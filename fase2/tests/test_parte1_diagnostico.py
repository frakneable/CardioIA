import csv
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "parte1"))

import pytest

import diagnostico as dg

# Diagnóstico que cada uma das 10 frases foi escrita para representar.
ESPERADOS = [
    "Infarto Agudo do Miocárdio",
    "Angina",
    "Insuficiência Cardíaca",
    "Arritmia (Fibrilação Atrial)",
    "Hipertensão Arterial",
    "Pericardite",
    "Valvopatia",
    "TVP / Embolia Pulmonar",
    "Arritmia (Fibrilação Atrial)",
    "Insuficiência Cardíaca",
]


@pytest.fixture(scope="module")
def mapa():
    return dg.carregar_mapa()


@pytest.fixture(scope="module")
def frases():
    return dg.carregar_frases()


def test_dez_frases(frases):
    assert len(frases) == 10


def test_toda_frase_tem_tempo_de_inicio(frases):
    sem_tempo = [f for f in frases if not dg.extrair_inicio(f)]
    assert not sem_tempo


def test_mapa_tem_colunas_do_enunciado_mais_peso():
    with open(dg.ARQ_MAPA, encoding="utf-8", newline="") as f:
        assert csv.DictReader(f).fieldnames == ["sintoma_1", "sintoma_2", "doenca_associada", "peso"]


def test_pesos_validos(mapa):
    assert all(l.peso in (1, 2, 3) for l in mapa)


def test_oito_doencas(mapa):
    assert len({l.doenca for l in mapa}) == 8


@pytest.mark.parametrize("i, esperado", list(enumerate(ESPERADOS)))
def test_diagnostico_de_cada_frase(i, esperado, frases, mapa):
    assert dg.analisar(i + 1, frases[i], mapa).diagnostico == esperado


def test_normalizar_remove_acento_e_pontuacao():
    assert dg.normalizar("Coração DISPARADO!") == "coracao disparado"


def test_casamento_respeita_limite_de_palavra():
    assert dg.encontrar("ar", "vou parar agora".split()) == []
    assert dg.encontrar("falta de ar", "sinto falta de ar".split()) == [1]


def test_negacao_descarta_sintoma(mapa):
    r = dg.analisar(1, "Não sinto dor no peito.", mapa)
    assert "dor no peito" in r.negados
    assert r.ranking == []


def test_negacao_tem_alcance_limitado(mapa):
    # "não" está a mais de 3 palavras de "dor no peito": o sintoma conta.
    r = dg.analisar(1, "Não dormi bem esta noite e sinto dor no peito.", mapa)
    assert "dor no peito" in r.sintomas


def test_frase_sem_sintoma_conhecido(mapa):
    assert dg.analisar(1, "Estou ótimo hoje.", mapa).diagnostico == "sem sintomas reconhecidos"


def test_linha_soma_peso_uma_vez(mapa):
    # As duas formas do mesmo sintoma na frase não dobram o peso.
    uma = dg.analisar(1, "sinto aperto no peito", mapa)
    duas = dg.analisar(1, "sinto aperto no peito e peso no peito", mapa)
    assert dict(uma.ranking)["Infarto Agudo do Miocárdio"] == dict(duas.ranking)["Infarto Agudo do Miocárdio"]
