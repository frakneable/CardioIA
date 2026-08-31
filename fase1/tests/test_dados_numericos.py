import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import pandas as pd
import pytest

import comum

CSV_CLINICO = comum.RAIZ / "data" / "numerico" / "heart_disease_clinico.csv"

COLUNAS_ESPERADAS = [
    "paciente_id", "origem_base", "idade", "sexo", "tipo_dor_toracica",
    "pressao_repouso_mmhg", "colesterol_mgdl", "glicemia_jejum_alta",
    "ecg_repouso", "fc_maxima_bpm", "angina_exercicio",
    "depressao_st_oldpeak", "inclinacao_st", "n_vasos_obstruidos",
    "talassemia", "num_diagnostico", "doenca_cardiaca",
]


@pytest.fixture(scope="module")
def clinico():
    if not CSV_CLINICO.exists():
        pytest.fail("rode antes: .venv/bin/python fase1/scripts/baixar_uci.py")
    return pd.read_csv(CSV_CLINICO)


def test_colunas_e_ordem(clinico):
    assert list(clinico.columns) == COLUNAS_ESPERADAS


def test_total_de_linhas_das_quatro_bases(clinico):
    assert len(clinico) == 920


def test_contagem_por_base(clinico):
    assert clinico["origem_base"].value_counts().to_dict() == {
        "cleveland": 303, "hungarian": 294, "va": 200, "switzerland": 123,
    }


def test_acima_do_minimo_do_enunciado(clinico):
    assert len(clinico) >= 100


def test_paciente_id_unico(clinico):
    assert clinico["paciente_id"].is_unique


def test_alvo_binario_derivado_de_num(clinico):
    assert set(clinico["doenca_cardiaca"].unique()) <= {0, 1}
    esperado = (clinico["num_diagnostico"] > 0).astype(int)
    assert (clinico["doenca_cardiaca"] == esperado).all()


def test_missing_virou_vazio_e_nao_interrogacao(clinico):
    for coluna in clinico.columns:
        assert not clinico[coluna].astype(str).str.contains(r"\?").any()


def test_sexo_legivel(clinico):
    assert set(clinico["sexo"].unique()) <= {"masculino", "feminino"}


def test_colesterol_zero_preservado_como_zero(clinico):
    # Achado do spike: a base suíça registra colesterol ausente como 0.
    # O script NÃO deve "consertar" isso — é matéria-prima da análise de viés.
    zeros = (clinico["colesterol_mgdl"] == 0).sum()
    assert zeros > 100


# === Testes da telemetria IoT simulada ===

CSV_IOT = comum.RAIZ / "data" / "numerico" / "iot_wearable_telemetria.csv"

COLUNAS_IOT = [
    "paciente_id", "data", "fc_repouso_bpm", "fc_media_bpm", "hrv_ms",
    "spo2_pct", "pas_mmhg", "pad_mmhg", "passos", "minutos_atividade",
    "alerta_arritmia",
]


@pytest.fixture(scope="module")
def iot():
    if not CSV_IOT.exists():
        pytest.fail("rode antes: .venv/bin/python fase1/scripts/gerar_telemetria_iot.py")
    return pd.read_csv(CSV_IOT)


def test_iot_colunas(iot):
    assert list(iot.columns) == COLUNAS_IOT


def test_iot_sete_dias_por_paciente(iot, clinico):
    contagem = iot.groupby("paciente_id").size()
    assert set(contagem.unique()) == {7}
    assert len(contagem) == len(clinico)
    assert len(iot) == len(clinico) * 7


def test_iot_pacientes_batem_com_a_base_clinica(iot, clinico):
    assert set(iot["paciente_id"]) == set(clinico["paciente_id"])


def test_iot_faixas_fisiologicamente_plausiveis(iot):
    assert iot["fc_repouso_bpm"].between(40, 120).all()
    assert iot["fc_media_bpm"].between(45, 160).all()
    assert iot["hrv_ms"].between(5, 120).all()
    assert iot["spo2_pct"].between(85, 100).all()
    assert iot["pas_mmhg"].between(80, 220).all()
    assert iot["pad_mmhg"].between(50, 130).all()
    assert (iot["pas_mmhg"] > iot["pad_mmhg"]).all()
    assert iot["passos"].between(0, 25000).all()
    assert set(iot["alerta_arritmia"].unique()) <= {0, 1}


def test_iot_correlaciona_com_o_desfecho_real(iot, clinico):
    """A telemetria é condicionada ao dado real: doentes têm HRV mais baixa e
    mais alertas de arritmia. Sem isso a simulação seria ruído inútil."""
    juncao = iot.merge(clinico[["paciente_id", "doenca_cardiaca"]], on="paciente_id")
    hrv = juncao.groupby("doenca_cardiaca")["hrv_ms"].mean()
    assert hrv[1] < hrv[0]
    alertas = juncao.groupby("doenca_cardiaca")["alerta_arritmia"].mean()
    assert alertas[1] > alertas[0]


def test_iot_deterministica(iot):
    """Regerar com a mesma seed produz exatamente o mesmo arquivo."""
    import subprocess, sys
    antes = comum.sha256_arquivo(CSV_IOT)
    subprocess.run(
        [sys.executable, str(comum.RAIZ / "scripts" / "gerar_telemetria_iot.py")],
        check=True, capture_output=True,
    )
    assert comum.sha256_arquivo(CSV_IOT) == antes
