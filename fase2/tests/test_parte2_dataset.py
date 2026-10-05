import pathlib

import pandas as pd
import pytest

DIR = pathlib.Path(__file__).resolve().parents[1] / "parte2"
ROTULOS = {"alto risco", "baixo risco"}


@pytest.fixture(scope="module")
def base():
    return pd.read_csv(DIR / "frases_risco.csv")


@pytest.fixture(scope="module")
def adversariais():
    return pd.read_csv(DIR / "frases_adversariais.csv")


def test_formato_do_enunciado(base):
    assert list(base.columns) == ["frase", "situacao"]


def test_rotulos_validos(base, adversariais):
    assert set(base["situacao"]) == ROTULOS
    assert set(adversariais["situacao_esperada"]) == ROTULOS


def test_base_balanceada_com_200_frases(base):
    assert len(base) == 200
    assert base["situacao"].value_counts().to_dict() == {"alto risco": 100, "baixo risco": 100}


def test_sem_frases_duplicadas(base):
    assert not base["frase"].str.lower().str.strip().duplicated().any()


def test_adversariais_fora_da_base(base, adversariais):
    # O teste de distorções só vale se as frases não foram vistas no treino.
    vistas = set(base["frase"].str.lower().str.strip())
    assert not (set(adversariais["frase"].str.lower().str.strip()) & vistas)


def test_notebook_executado():
    import nbformat
    nb = nbformat.read(DIR / "classificador_risco.ipynb", as_version=4)
    codigo = [c for c in nb.cells if c.cell_type == "code"]
    assert all(c.get("execution_count") for c in codigo), "rode o notebook antes de entregar"
    erros = [o for c in codigo for o in c.get("outputs", []) if o.get("output_type") == "error"]
    assert not erros
