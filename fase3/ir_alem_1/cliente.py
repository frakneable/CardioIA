"""Cliente REST do CardioIA (requests).

Faz o papel do vestível e do posto de enfermagem: envia leituras para a API
(POST) e consulta leituras, alertas e o status do paciente (GET).

    python cliente.py simular            roda o roteiro de situações clínicas
    python cliente.py leituras [-n 10]   últimas leituras
    python cliente.py alertas            alertas gerados e e-mails disparados
    python cliente.py status             situação atual do paciente

Se a API estiver fora do ar, as leituras ficam numa fila local e são
reenviadas na próxima tentativa (a mesma ideia de resiliência da Parte 1).
"""

import argparse
import os
import random
import sys
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL_PADRAO = os.getenv("CARDIOIA_API_URL", "http://127.0.0.1:5050")
CHAVE_PADRAO = os.getenv("CARDIOIA_API_KEY", "cardioia-demo")


class ErroApi(Exception):
    pass


class ClienteCardioIA:
    def __init__(self, url: str = URL_PADRAO, chave: str = CHAVE_PADRAO, timeout: float = 5):
        self.url = url.rstrip("/") + "/api/v1"
        self.timeout = timeout
        self.fila: list[dict] = []
        self.sessao = requests.Session()
        self.sessao.headers.update({"X-API-Key": chave, "Accept": "application/json"})
        # Tenta de novo em erro 5xx passageiro, com espera crescente.
        tentativas = Retry(total=3, backoff_factor=0.3, status_forcelist=(502, 503, 504),
                           allowed_methods=None)
        self.sessao.mount("http://", HTTPAdapter(max_retries=tentativas))
        self.sessao.mount("https://", HTTPAdapter(max_retries=tentativas))

    def _requisitar(self, metodo: str, caminho: str, **kwargs) -> requests.Response:
        resposta = self.sessao.request(metodo, self.url + caminho, timeout=self.timeout, **kwargs)
        if resposta.status_code >= 400:
            try:
                corpo = resposta.json()
            except ValueError:
                corpo = resposta.text
            raise ErroApi(f"{metodo} {caminho} → HTTP {resposta.status_code}: {corpo}")
        return resposta

    # --- envio ---------------------------------------------------------------

    def enviar_leitura(self, leitura: dict) -> list[dict]:
        """Põe a leitura na fila e tenta descarregar a fila inteira, em ordem.

        Devolve as respostas da API para o que foi entregue agora. Sem conexão,
        devolve lista vazia e a leitura espera a próxima chamada.
        """
        self.fila.append(leitura)
        entregues = []
        while self.fila:
            try:
                resposta = self._requisitar("POST", "/leituras", json=self.fila[0])
            except requests.ConnectionError:
                break
            entregues.append(resposta.json())
            self.fila.pop(0)
        return entregues

    # --- consulta ------------------------------------------------------------

    def saude(self) -> bool:
        try:
            return self._requisitar("GET", "/saude").json().get("status") == "ok"
        except (requests.ConnectionError, ErroApi):
            return False

    def leituras(self, paciente: str | None = None, limite: int = 20) -> list[dict]:
        return self._requisitar("GET", "/leituras", params={"paciente": paciente, "limite": limite}).json()["leituras"]

    def alertas(self, paciente: str | None = None, limite: int = 20) -> list[dict]:
        return self._requisitar("GET", "/alertas", params={"paciente": paciente, "limite": limite}).json()["alertas"]

    def status(self, paciente: str) -> dict:
        return self._requisitar("GET", f"/pacientes/{paciente}/status").json()


# --- roteiro de simulação ----------------------------------------------------

# (situação, quantidade de leituras, bpm, temperatura, aceleração em g)
# Aceleração None = paciente parado de verdade (sensor cravado em 1,00 g).
ROTEIRO = [
    ("normal", 5, 72, 36.6, 1.0),
    ("taquicardia em repouso", 4, 135, 36.7, 1.0),
    ("normal", 3, 75, 36.6, 1.0),
    ("correndo (FC alta, mas esperada)", 4, 140, 36.9, 1.6),
    ("febre", 4, 88, 38.4, 1.0),
    ("normal", 3, 74, 36.8, 1.0),
    ("queda", 1, 96, 36.7, 3.2),
    ("caído, sem se mexer", 10, 58, 36.4, None),
    ("bradicardia", 3, 42, 36.3, 1.0),
    ("normal", 3, 70, 36.6, 1.0),
]


def gerar_leituras(paciente: str, inicio: int | None = None, intervalo_s: int = 2, semente: int = 7):
    """Gera as leituras do roteiro com um pouco de ruído, como um sensor real."""
    aleatorio = random.Random(semente)
    ts = inicio or int(time.time())
    seq = 0
    for situacao, quantidade, bpm, temp, acel in ROTEIRO:
        for _ in range(quantidade):
            seq += 1
            yield situacao, {
                "paciente": paciente,
                "seq": seq,
                "ts": ts,
                "temp": round(temp + aleatorio.uniform(-0.1, 0.1), 1),
                "umid": round(aleatorio.uniform(50, 60), 1),
                "bpm": bpm + aleatorio.randint(-3, 3),
                "acel": 1.0 if acel is None else round(acel + aleatorio.uniform(-0.08, 0.08), 2),
            }
            ts += intervalo_s


def simular(cliente: ClienteCardioIA, paciente: str, pausa: float) -> None:
    if not cliente.saude():
        sys.exit(f"API fora do ar em {cliente.url}. Suba antes com: python api.py")

    situacao_atual = None
    for situacao, leitura in gerar_leituras(paciente):
        if situacao != situacao_atual:
            print(f"\n── {situacao} ──")
            situacao_atual = situacao
        for r in cliente.enviar_leitura(leitura):
            l = r["leitura"]
            estado = "ALERTA " + ", ".join(l["motivos"]) if l["alerta"] else "normal"
            print(f"  #{l['seq']:>2}  {l['bpm']:>3} BPM  {l['temp']:.1f} °C  {l['acel']:.2f} g "
                  f"{l['movimento']:<9} → {estado}")
            if r["email"]:
                print(f"       ✉ e-mail {r['email']['status']}: {r['email']['destino']}")
        time.sleep(pausa)

    print("\n── consulta à API (GET) ──")
    st = cliente.status(paciente)
    print(f"  Status de {paciente}: {st['ultima_leitura']['severidade']}, "
          f"{st['alertas_enviados']} alertas com e-mail")
    for a in reversed(cliente.alertas(paciente)):
        print(f"  {time.strftime('%H:%M:%S', time.localtime(a['ts']))}  {a['severidade']:<8} "
              f"{', '.join(a['novos']):<30} e-mail {a['email_status']}")


def main():
    parser = argparse.ArgumentParser(description="Cliente REST do CardioIA")
    parser.add_argument("comando", choices=["simular", "leituras", "alertas", "status"])
    parser.add_argument("--paciente", default="paciente01")
    parser.add_argument("-n", "--limite", type=int, default=10)
    parser.add_argument("--pausa", type=float, default=0.3, help="segundos entre envios na simulação")
    args = parser.parse_args()

    cliente = ClienteCardioIA()
    try:
        if args.comando == "simular":
            simular(cliente, args.paciente, args.pausa)
        elif args.comando == "leituras":
            for l in cliente.leituras(args.paciente, args.limite):
                print(f"#{l['seq']:>3}  {l['bpm']:>3} BPM  {l['temp']:.1f} °C  {l['movimento']:<9} "
                      f"{', '.join(l['motivos']) or 'normal'}")
        elif args.comando == "alertas":
            for a in cliente.alertas(args.paciente, args.limite):
                print(f"leitura {a['leitura_id']:>3}  {a['severidade']:<8} {', '.join(a['motivos']):<35} "
                      f"e-mail {a['email_status']} → {a['email_destino']}")
        else:
            print(cliente.status(args.paciente))
    except requests.ConnectionError:
        sys.exit(f"API fora do ar em {cliente.url}. Suba antes com: python api.py")
    except ErroApi as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
