"""Ir Além 1: API REST, cliente, verificação de risco e e-mail de alerta."""

import email
import sys
import threading
from pathlib import Path

import pytest
import requests
from werkzeug.serving import make_server

DIR = Path(__file__).resolve().parents[1] / "ir_alem_1"
sys.path.insert(0, str(DIR))

import notificador  # noqa: E402
from api import create_app  # noqa: E402
from cliente import ClienteCardioIA, gerar_leituras  # noqa: E402
from risco import JANELA_IMOVEL, avaliar  # noqa: E402

CHAVE = "chave-teste"


def leitura(**campos):
    base = {"paciente": "p1", "seq": 1, "ts": 1_793_000_000, "temp": 36.6, "umid": 55.0, "bpm": 72, "acel": 1.05}
    return {**base, **campos}


# --- verificação de risco ----------------------------------------------------

@pytest.mark.parametrize(
    "campos, motivos",
    [
        ({}, []),
        ({"bpm": 135}, ["taquicardia"]),
        ({"bpm": 140, "acel": 1.6}, []),               # correndo: limite sobe para 150
        ({"bpm": 160, "acel": 1.6}, ["taquicardia"]),
        ({"bpm": 42}, ["bradicardia"]),
        ({"bpm": 0}, []),                              # sem leitura de pulso não é bradicardia
        ({"temp": 37.8}, ["febre"]),
        ({"temp": 35.0}, ["hipotermia"]),
        ({"acel": 3.0}, ["queda"]),
        ({"bpm": 130, "temp": 38.5}, ["taquicardia", "febre"]),
    ],
)
def test_regras_de_risco(campos, motivos):
    assert avaliar(leitura(**campos), []).motivos == motivos


def test_ausencia_de_movimento_precisa_da_janela_inteira():
    parado = [1.0] * (JANELA_IMOVEL - 1)
    assert avaliar(leitura(acel=1.0), parado).motivos == ["ausencia_movimento"]
    assert avaliar(leitura(acel=1.0), parado[:-1]).motivos == []           # histórico curto
    assert avaliar(leitura(acel=1.0), [1.1, *parado[1:]]).motivos == []    # houve movimento


def test_severidade():
    assert avaliar(leitura(), []).severidade == "normal"
    assert avaliar(leitura(temp=38.2), []).severidade == "atencao"
    assert avaliar(leitura(temp=38.2, acel=3.0), []).severidade == "critico"


# --- API REST ----------------------------------------------------------------

@pytest.fixture
def emails():
    return []


@pytest.fixture
def app(tmp_path, emails):
    def enviar_falso(msg):
        emails.append(msg)
        return "memoria"
    return create_app(tmp_path / "teste.db", chave=CHAVE, enviar_email=enviar_falso)


@pytest.fixture
def http(app):
    return app.test_client()


def post(http, dados, chave=CHAVE):
    return http.post("/api/v1/leituras", json=dados, headers={"X-API-Key": chave})


def test_saude_sem_chave_e_demais_rotas_com_chave(http):
    assert http.get("/api/v1/saude").status_code == 200
    assert http.get("/api/v1/leituras").status_code == 401
    assert post(http, leitura(), chave="errada").status_code == 401


def test_leitura_invalida_retorna_400(http):
    resposta = post(http, {"paciente": "p1", "bpm": "cento e vinte"})
    assert resposta.status_code == 400
    detalhes = " ".join(resposta.get_json()["detalhes"])
    assert "bpm: tipo inválido" in detalhes and "temp: obrigatório" in detalhes
    assert post(http, leitura(temp=60)).status_code == 400


def test_post_classifica_e_get_devolve(http):
    resposta = post(http, leitura(bpm=135))
    assert resposta.status_code == 201
    corpo = resposta.get_json()["leitura"]
    assert corpo["alerta"] and corpo["motivos"] == ["taquicardia"] and corpo["severidade"] == "atencao"

    lidas = http.get("/api/v1/leituras?paciente=p1", headers={"X-API-Key": CHAVE}).get_json()["leituras"]
    assert len(lidas) == 1 and lidas[0]["motivos"] == ["taquicardia"]


def test_reenvio_da_mesma_leitura_nao_duplica_nem_manda_email(http, emails):
    assert post(http, leitura(bpm=135)).status_code == 201
    repetida = post(http, leitura(bpm=135))
    assert repetida.status_code == 200 and repetida.get_json()["repetida"]
    assert len(emails) == 1


def test_email_so_quando_aparece_motivo_novo(http, emails):
    seq = iter(range(1, 100))

    def enviar(**campos):
        n = next(seq)
        return post(http, leitura(seq=n, ts=1_793_000_000 + 2 * n, **campos)).get_json()["email"]

    assert enviar() is None                                  # normal
    assert enviar(bpm=135)["status"] == "enviado"            # taquicardia começa
    assert enviar(bpm=138) is None                           # continua: sem e-mail repetido
    assert enviar(bpm=138, temp=38.4)["status"] == "enviado" # febre é motivo novo
    assert enviar() is None                                  # voltou ao normal
    assert enviar(bpm=133)["status"] == "enviado"            # novo episódio
    assert len(emails) == 3
    assert "febre" in emails[1]["Subject"] and "taquicardia" in emails[1]["Subject"]

    alertas = http.get("/api/v1/alertas", headers={"X-API-Key": CHAVE}).get_json()["alertas"]
    assert [a["novos"] for a in alertas] == [["taquicardia"], ["febre"], ["taquicardia"]]


def test_falha_no_email_nao_perde_a_leitura(tmp_path):
    def quebrado(_msg):
        raise ConnectionRefusedError("servidor SMTP fora do ar")

    http = create_app(tmp_path / "t.db", chave=CHAVE, enviar_email=quebrado).test_client()
    resposta = post(http, leitura(acel=3.0))
    assert resposta.status_code == 201 and resposta.get_json()["email"]["status"] == "falhou"
    alerta = http.get("/api/v1/alertas", headers={"X-API-Key": CHAVE}).get_json()["alertas"][0]
    assert alerta["email_status"] == "falhou"


def test_status_do_paciente(http):
    assert http.get("/api/v1/pacientes/p1/status", headers={"X-API-Key": CHAVE}).status_code == 404
    post(http, leitura(temp=38.0))
    st = http.get("/api/v1/pacientes/p1/status", headers={"X-API-Key": CHAVE}).get_json()
    assert st["ultima_leitura"]["severidade"] == "atencao" and st["alertas_enviados"] == 1


# --- e-mail ------------------------------------------------------------------

def test_email_tem_texto_e_html_e_modo_arquivo_grava_eml(tmp_path, monkeypatch):
    dados = leitura(bpm=135, temp=38.4)
    msg = notificador.montar_email(dados, avaliar(dados, []), ["febre"])
    assert msg["Subject"].startswith("[CardioIA][ATENÇÃO] p1")
    assert {p.get_content_type() for p in msg.iter_parts()} == {"text/plain", "text/html"}

    monkeypatch.setenv("EMAIL_MODO", "arquivo")
    monkeypatch.setattr(notificador, "PASTA_SAIDA", tmp_path)
    caminho = tmp_path.parent / notificador.enviar(msg)
    relido = email.message_from_bytes(caminho.read_bytes())
    assert caminho.suffix == ".eml" and "taquicardia" in str(email.header.make_header(email.header.decode_header(relido["Subject"])))


def test_modo_smtp_usa_smtplib(monkeypatch):
    enviados = []

    class SmtpFalso:
        def __init__(self, host, porta, timeout):
            self.destino = (host, porta)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def send_message(self, msg):
            enviados.append((self.destino, msg["Subject"]))

    monkeypatch.setenv("EMAIL_MODO", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.exemplo")
    monkeypatch.setattr(notificador.smtplib, "SMTP", SmtpFalso)
    dados = leitura(acel=3.0)
    assert notificador.enviar(notificador.montar_email(dados, avaliar(dados, []), ["queda"])) == "smtp://smtp.exemplo:1025"
    assert enviados[0][0] == ("smtp.exemplo", 1025) and "CRÍTICO" in enviados[0][1]


# --- cliente REST contra a API rodando de verdade ----------------------------

@pytest.fixture
def servidor(app):
    srv = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_cliente_roda_o_roteiro_inteiro(servidor, emails):
    cliente = ClienteCardioIA(servidor, chave=CHAVE)
    assert cliente.saude()
    for _, dados in gerar_leituras("p1", inicio=1_793_000_000):
        cliente.enviar_leitura(dados)

    novos = [a["novos"] for a in reversed(cliente.alertas("p1"))]
    assert novos == [["taquicardia"], ["febre"], ["queda"], ["ausencia_movimento"], ["bradicardia"]]
    assert len(emails) == 5
    assert cliente.status("p1")["ultima_leitura"]["severidade"] == "normal"


def test_cliente_guarda_na_fila_sem_conexao_e_reenvia(app, emails):
    cliente = ClienteCardioIA("http://127.0.0.1:9", chave=CHAVE, timeout=0.5)   # porta fechada
    cliente.sessao.mount("http://", requests.adapters.HTTPAdapter(max_retries=0))
    assert cliente.enviar_leitura(leitura(seq=1, bpm=135)) == []
    assert cliente.enviar_leitura(leitura(seq=2, ts=1_793_000_002, bpm=136)) == []
    assert len(cliente.fila) == 2

    srv = make_server("127.0.0.1", 0, app)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        cliente.url = f"http://127.0.0.1:{srv.server_port}/api/v1"
        entregues = cliente.enviar_leitura(leitura(seq=3, ts=1_793_000_004, bpm=74))
        assert [r["leitura"]["seq"] for r in entregues] == [1, 2, 3] and cliente.fila == []
    finally:
        srv.shutdown()
    assert len(emails) == 1


def test_arquivos_da_entrega():
    for arquivo in ("api.py", "cliente.py", "risco.py", "notificador.py", "requirements.txt",
                    "README.md", "RELATORIO.md", "RELATORIO.pdf"):
        assert (DIR / arquivo).is_file(), arquivo
    ignorados = (DIR.parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "fase3/ir_alem_1/cardioia.db" in ignorados and "fase3/ir_alem_1/caixa_saida/" in ignorados
