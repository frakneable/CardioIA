"""Ir Além 2: notebook executado, comparação LR × LIF, relatório e README."""

from pathlib import Path

import nbformat

DIR = Path(__file__).resolve().parents[1] / "ir_alem_2"
NOTEBOOK = DIR / "series_temporais_lif.ipynb"


def codigo_e_saidas():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    return [c for c in nb.cells if c.cell_type == "code"], nb


def test_notebook_executado_sem_erros():
    celulas, _ = codigo_e_saidas()
    assert all(c.execution_count for c in celulas), "notebook precisa estar executado"
    erros = [o for c in celulas for o in c.outputs if o.output_type == "error"]
    assert not erros, erros[0].evalue if erros else ""


def test_notebook_comentado_e_com_os_dois_modelos():
    celulas, nb = codigo_e_saidas()
    fonte = "\n".join(c.source for c in celulas)
    markdown = [c for c in nb.cells if c.cell_type == "markdown"]
    assert len(markdown) >= 15
    assert "LogisticRegression" in fonte and "class RedeLIF" in fonte
    assert "GroupKFold" in fonte                       # hiperparâmetros só com validação por paciente
    assert "beta * v" in fonte and "v >= 1.0" in fonte # integra, vaza e dispara


def test_divisao_por_paciente_sem_sobreposicao():
    celulas, _ = codigo_e_saidas()
    fonte = "\n".join(c.source for c in celulas)
    ns = {}
    exec(fonte[fonte.index("DS1 = ["):fonte.index("if not all")], ns)
    assert len(ns["DS1"]) == len(ns["DS2"]) == 22
    assert not set(ns["DS1"]) & set(ns["DS2"])
    assert not {102, 104, 107, 217} & (set(ns["DS1"]) | set(ns["DS2"]))   # marca-passo fora


def test_entregaveis():
    for arquivo in ("README.md", "RELATORIO.md", "RELATORIO.pdf"):
        assert (DIR / arquivo).is_file(), arquivo
    readme = (DIR / "README.md").read_text(encoding="utf-8")
    assert "series_temporais_lif.ipynb" in readme and "Vídeo" in readme
    ignorados = (DIR.parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "fase3/ir_alem_2/dados/" in ignorados
