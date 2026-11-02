"""Lógica de verificação de risco do CardioIA.

Mesmos limiares do ESP32 (fase3/parte2/sketch.ino), mais uma regra que o
dispositivo não consegue aplicar sozinho porque depende do histórico:
**ausência de movimento** prolongada (paciente imóvel demais por tempo demais,
sinal de desmaio ou de queda sem recuperação).
"""

from dataclasses import dataclass, field

# Limiares clínicos (iguais aos do Edge)
BPM_MIN = 50
BPM_MAX_REPOUSO = 120
BPM_MAX_ATIVIDADE = 150
TEMP_FEBRE = 37.8
TEMP_HIPOTERMIA = 35.0
ACEL_DESVIO_ATIVO_G = 0.3
ACEL_QUEDA_G = 2.5

# Ausência de movimento: N leituras seguidas com a aceleração colada em 1 g.
# Na demonstração (uma leitura a cada 2 s) são 20 s; em produção a janela
# seria de minutos e combinada com o horário de sono do paciente.
ACEL_IMOVEL_G = 0.02
JANELA_IMOVEL = 10

SEVERIDADE = {
    "taquicardia": "atencao",
    "febre": "atencao",
    "bradicardia": "critico",
    "hipotermia": "critico",
    "queda": "critico",
    "ausencia_movimento": "critico",
}

DESCRICAO = {
    "taquicardia": "frequência cardíaca acima do limite",
    "bradicardia": "frequência cardíaca abaixo de 50 BPM",
    "febre": "temperatura a partir de 37,8 °C",
    "hipotermia": "temperatura até 35 °C",
    "queda": "aceleração acima de 2,5 g (possível queda)",
    "ausencia_movimento": "paciente sem nenhum movimento por tempo prolongado",
}


@dataclass
class Risco:
    movimento: str
    motivos: list[str] = field(default_factory=list)

    @property
    def alerta(self) -> bool:
        return bool(self.motivos)

    @property
    def severidade(self) -> str:
        if not self.motivos:
            return "normal"
        return "critico" if any(SEVERIDADE[m] == "critico" for m in self.motivos) else "atencao"


def classificar_movimento(acel: float) -> str:
    if acel >= ACEL_QUEDA_G:
        return "queda"
    if abs(acel - 1.0) > ACEL_DESVIO_ATIVO_G:
        return "atividade"
    return "repouso"


def imovel(acel: float) -> bool:
    return abs(acel - 1.0) < ACEL_IMOVEL_G


def avaliar(leitura: dict, acel_anteriores: list[float]) -> Risco:
    """Avalia uma leitura.

    `acel_anteriores` são as acelerações das leituras anteriores do mesmo
    paciente, da mais recente para a mais antiga.
    """
    risco = Risco(movimento=classificar_movimento(leitura["acel"]))
    bpm, temp = leitura["bpm"], leitura["temp"]

    # bpm = 0 é "sem leitura de pulso": falta de dado não é bradicardia.
    bpm_max = BPM_MAX_ATIVIDADE if risco.movimento == "atividade" else BPM_MAX_REPOUSO
    if 0 < bpm < BPM_MIN:
        risco.motivos.append("bradicardia")
    if bpm > bpm_max:
        risco.motivos.append("taquicardia")

    if temp >= TEMP_FEBRE:
        risco.motivos.append("febre")
    elif temp <= TEMP_HIPOTERMIA:
        risco.motivos.append("hipotermia")

    if risco.movimento == "queda":
        risco.motivos.append("queda")

    janela = [leitura["acel"], *acel_anteriores[: JANELA_IMOVEL - 1]]
    if len(janela) == JANELA_IMOVEL and all(imovel(a) for a in janela):
        risco.motivos.append("ausencia_movimento")

    return risco
