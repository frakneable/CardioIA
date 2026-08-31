import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import pandas as pd
import pytest
from PIL import Image

import comum

DIR_IMG = comum.RAIZ / "assets" / "imagens"
MANIFEST = DIR_IMG / "MANIFEST.csv"
CLASSES = {"normal", "infarto", "historico_infarto", "arritmia"}


@pytest.fixture(scope="module")
def manifest():
    if not MANIFEST.exists():
        pytest.fail("rode antes: .venv/bin/python fase1/scripts/preparar_imagens.py")
    return pd.read_csv(MANIFEST)


def test_minimo_cem_imagens_do_enunciado(manifest):
    assert len(manifest) >= 100


def test_exatamente_cento_e_vinte(manifest):
    assert len(manifest) == 120


def test_amostra_balanceada_por_classe(manifest):
    contagem = manifest["classe"].value_counts().to_dict()
    assert set(contagem) == CLASSES
    assert set(contagem.values()) == {30}


def test_manifest_tem_as_colunas(manifest):
    assert list(manifest.columns) == [
        "arquivo", "classe", "arquivo_origem", "url_origem",
        "sha256", "largura", "altura", "bytes",
    ]


def test_todo_arquivo_do_manifest_existe_no_disco(manifest):
    for nome in manifest["arquivo"]:
        assert (DIR_IMG / nome).is_file(), nome


def test_nao_ha_imagem_fora_do_manifest(manifest):
    no_disco = {p.name for p in DIR_IMG.glob("*.jpg")}
    assert no_disco == set(manifest["arquivo"])


def test_hash_do_manifest_confere_com_o_disco(manifest):
    for linha in manifest.itertuples(index=False):
        assert comum.sha256_arquivo(DIR_IMG / linha.arquivo) == linha.sha256, linha.arquivo


def test_formato_e_normalizacao(manifest):
    for linha in manifest.itertuples(index=False):
        caminho = DIR_IMG / linha.arquivo
        assert caminho.suffix == ".jpg"
        with Image.open(caminho) as img:
            assert img.format == "JPEG"
            assert img.mode == "RGB"
            assert max(img.size) <= 1024
            assert img.size == (linha.largura, linha.altura)


def test_repositorio_leve(manifest):
    total_mb = manifest["bytes"].sum() / 1e6
    assert total_mb < 40, f"{total_mb:.1f} MB — imagens grandes demais para o repo"


def test_sem_imagem_duplicada(manifest):
    assert manifest["sha256"].is_unique
    assert manifest["arquivo_origem"].is_unique
