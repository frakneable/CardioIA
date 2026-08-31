import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import comum


def test_seed_fixa():
    assert comum.SEED == 42


def test_raiz_aponta_para_fase1():
    assert comum.RAIZ.name == "fase1"
    assert (comum.RAIZ / "scripts").is_dir()


def test_sha256_de_conteudo_conhecido(tmp_path):
    arq = tmp_path / "a.txt"
    arq.write_bytes(b"cardioia")
    assert comum.sha256_arquivo(arq) == (
        "f3ab2e2bea55aca0022344be4f26edfe0c509777655e8cfcdf91b24c3c5d0d13"
    )
    assert len(comum.sha256_arquivo(arq)) == 64
