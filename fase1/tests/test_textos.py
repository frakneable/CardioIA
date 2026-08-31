import re
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import pytest

import comum

DIR_TEXTOS = comum.RAIZ / "docs" / "textos"
ESPERADOS = {
    "01_scielo_mortalidade_dcv.txt": 3000,
    "02_sbc_diretriz_hipertensao.txt": 20000,
    "03_opas_dcv_divulgacao.txt": 800,
}
CHAVES = ("Titulo:", "Fonte:", "URL:", "Licenca:", "Acesso:", "Registro:", "Recorte:")

# Menu, rodapé e widgets de métrica das páginas de origem. Não são tags HTML —
# sobrevivem a qualquer limpeza que só remova marcação, então precisam de um
# teste próprio. Ver o recorte por container em scripts/baixar_textos.py.
BOILERPLATE = (
    "navigate_before", "navigate_next", "vertical_align_top", "table_chart",
    "Baixar em RIS", "Baixar em BIBTEX", "SciELO Analytics", "PlumX",
    "Altmetric", "Scite_", "Reportar erro", "Report error",
    "Ir para o topo", "Go to top", "Download PDF",
)


@pytest.fixture(scope="module")
def textos():
    faltando = [n for n in ESPERADOS if not (DIR_TEXTOS / n).exists()]
    if faltando:
        pytest.fail(f"rode antes: .venv/bin/python fase1/scripts/baixar_textos.py ({faltando})")
    return {n: (DIR_TEXTOS / n).read_text(encoding="utf-8") for n in ESPERADOS}


def test_minimo_dois_textos_do_enunciado(textos):
    assert len(textos) >= 2


def test_todos_tem_bloco_de_procedencia(textos):
    for nome, conteudo in textos.items():
        assert conteudo.startswith("=== PROCEDENCIA ==="), nome
        cabecalho = conteudo.split("=== FIM PROCEDENCIA ===")[0]
        for chave in CHAVES:
            assert chave in cabecalho, f"{nome} sem {chave}"


def test_volume_minimo_de_palavras(textos):
    for nome, minimo in ESPERADOS.items():
        corpo = textos[nome].split("=== FIM PROCEDENCIA ===")[1]
        assert len(corpo.split()) >= minimo, f"{nome} curto demais"


def test_conteudo_e_cardiologico_em_portugues(textos):
    for nome, conteudo in textos.items():
        baixo = conteudo.lower()
        assert any(t in baixo for t in ("cardiovascular", "cardíac", "hipertens", "coração")), nome


def test_sem_residuo_de_html(textos):
    for nome, conteudo in textos.items():
        for residuo in ("<div", "<span", "<script", "&nbsp;", "&lt;"):
            assert residuo not in conteudo, f"{nome} contém {residuo}"


def test_sem_boilerplate_de_navegacao(textos):
    """Tirar as tags não basta: menu e widgets viram texto solto no corpus."""
    for nome, conteudo in textos.items():
        corpo = conteudo.split("=== FIM PROCEDENCIA ===")[1]
        for termo in BOILERPLATE:
            assert termo not in corpo, f"{nome} contém boilerplate {termo!r}"


def test_sem_lista_de_referencias_bibliograficas(textos):
    """A bibliografia da diretriz eram ~30 mil palavras de citação em inglês.
    Fica fora do corpus de propósito — ver o recorte em baixar_textos.py."""
    corpo = textos["02_sbc_diretriz_hipertensao.txt"].split("=== FIM PROCEDENCIA ===")[1]
    citacoes = re.findall(r"\b(?:19|20)\d\d;\s*\d+", corpo)
    assert len(citacoes) < 100, f"{len(citacoes)} citações — a bibliografia voltou?"


def test_procedencia_consolidada_existe():
    proc = DIR_TEXTOS / "PROCEDENCIA.md"
    assert proc.exists()
    texto = proc.read_text(encoding="utf-8")
    for nome in ESPERADOS:
        assert nome in texto
