import pathlib

import nbformat

DIR = pathlib.Path(__file__).resolve().parents[1] / "ir_alem_2"


def test_notebook_executado_sem_erros():
    nb = nbformat.read(DIR / "ecg_mlp.ipynb", as_version=4)
    codigo = [c for c in nb.cells if c.cell_type == "code"]
    assert all(c.get("execution_count") for c in codigo), "rode o notebook antes de entregar"
    assert not [o for c in codigo for o in c.get("outputs", []) if o.get("output_type") == "error"]


def test_notebook_usa_keras_e_mlp():
    fonte = "\n".join(c.source for c in nbformat.read(DIR / "ecg_mlp.ipynb", as_version=4).cells)
    assert "keras.Sequential" in fonte and "keras.layers.Dense" in fonte
    assert "Conv2D" not in fonte  # o enunciado pede MLP, não CNN


def test_exemplos_de_imagens_das_cinco_classes():
    for c, sigla in enumerate("NSVFQ"):
        for tipo in ("bruta", "preprocessada"):
            assert (DIR / "exemplos" / f"classe{c}_{sigla}_{tipo}.png").exists()
