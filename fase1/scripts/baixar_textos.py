"""Baixa e limpa os três textos da Parte 2 (NLP).

Os três foram escolhidos para cobrir REGISTROS DE LINGUAGEM diferentes — é o
contraste que torna defensável a classificação de tópicos e a análise de
sentimento nas fases seguintes:
  1. artigo científico (linguagem acadêmica, dados epidemiológicos)
  2. diretriz clínica (terminologia densa, ideal para extração de entidades)
  3. material de divulgação (linguagem leiga, carga afetiva)

Licenças verificadas em 2026-08-31: os dois textos do SciELO são CC BY 4.0.
O material da OPAS/OMS é de divulgação pública, citado com atribuição.

RECORTE DO CONTEÚDO: baixar a página inteira e só tirar as tags deixava menu,
rodapé e widgets de métrica dentro do corpus ("navigate_before", "Baixar em
RIS", "SciELO Analytics", "PlumX"...). Cada fonte agora tem um extrator que
recorta o container do conteúdo antes de limpar:

  - SciELO: pega `div.articleTxt` e para no bloco de referências
    (`div.articleSection--referências`), depois anexa as tabelas, que o SciELO
    renderiza fora do corpo, em modais `div.modal.ModalTables`. A bibliografia
    fica de fora de propósito: são ~30 mil palavras de citação em inglês na
    diretriz da SBC, que inflavam a contagem e não são prosa clínica.
  - OPAS: pega `div.region-content`, o corpo do artigo no tema do Drupal.

O que cada arquivo contém está declarado no campo `Recorte:` do cabeçalho de
procedência, para que a contagem de palavras seja interpretável.
"""
from __future__ import annotations

import datetime as dt
import html
import re

import comum

# Ligaduras de ícone (Material Icons) viram texto ao remover as tags: era daí
# que vinham "home", "navigate_before" e "table_chart" no meio do texto.
RE_ICONES = r'(?is)<(span|i)[^>]*class="[^"]*material-icons[^"]*"[^>]*>.*?</\1>'
RE_BOTOES = r"(?is)<button[^>]*>.*?</button>"
RE_INVISIVEL = r"(?is)<(script|style|nav|footer|header|form|noscript)[^>]*>.*?</\1>"

SCIELO_CORPO = r'<div[^>]*class="articleTxt"[^>]*>'
SCIELO_REFERENCIAS = r'<div[^>]*class="articleSection articleSection--refer'
SCIELO_TABELAS = r'<div[^>]*class="modal fade ModalTables[^"]*"[^>]*>'
OPAS_CORPO = r'<div[^>]*class="region region-content"[^>]*>'

FONTES = [
    {
        "arquivo": "01_scielo_mortalidade_dcv.txt",
        "titulo": (
            "Taxas de Mortalidade por Doenças Cardiovasculares e Câncer na "
            "População Brasileira com Idade entre 35 e 74 Anos, 1996-2017"
        ),
        "fonte": "SciELO — Arquivos Brasileiros de Cardiologia (SBC)",
        "url": "https://www.scielo.br/j/abc/a/cJzNdtHVN7PxzTg9BhnqWXb/?lang=pt",
        "licenca": "CC BY 4.0",
        "registro": "artigo cientifico — linguagem academica, dados epidemiologicos",
        "extrator": "scielo",
        "recorte": "corpo do artigo e tabelas; sem a lista de referencias",
    },
    {
        "arquivo": "02_sbc_diretriz_hipertensao.txt",
        "titulo": "Diretrizes Brasileiras de Hipertensão Arterial – 2020",
        "fonte": "SciELO — Arquivos Brasileiros de Cardiologia (SBC/SBH/SBN)",
        "url": "https://www.scielo.br/j/abc/a/Z6m5gGNQCvrW3WLV7csqbqh/?lang=pt",
        "licenca": "CC BY 4.0",
        "registro": "diretriz clinica — terminologia densa, base para NER de sintomas",
        "extrator": "scielo",
        "recorte": "corpo da diretriz e quadros; sem a lista de referencias",
    },
    {
        "arquivo": "03_opas_dcv_divulgacao.txt",
        "titulo": "Doenças cardiovasculares — página temática",
        "fonte": "OPAS/OMS — Organização Pan-Americana da Saúde",
        "url": "https://www.paho.org/pt/topicos/doencas-cardiovasculares",
        "licenca": "conteúdo público OPAS/OMS, citado com atribuição",
        "registro": "divulgacao para leigos — linguagem acessivel, analise de sentimento",
        "extrator": "opas",
        "recorte": "corpo da pagina tematica; sem menu, rodape e lista de eventos",
    },
]


def blocos_div(bruto: str, abertura: str) -> list[str]:
    """Todos os `<div>` que casam com `abertura`, equilibrando o aninhamento.

    Regex sozinha não fecha `<div>` corretamente quando há divs aninhadas —
    daí a contagem de profundidade.
    """
    encontrados = []
    for inicio in re.finditer(abertura, bruto):
        posicao = inicio.end()
        profundidade = 1
        for tag in re.finditer(r"<div\b|</div>", bruto[posicao:]):
            profundidade += 1 if tag.group(0) == "<div" else -1
            if profundidade == 0:
                encontrados.append(bruto[inicio.start(): posicao + tag.end()])
                break
    return encontrados


def limpar_html(bruto: str) -> str:
    """Remove marcação e normaliza espaços, preservando quebras de parágrafo."""
    sem_ruido = re.sub(RE_ICONES, " ", bruto)
    sem_ruido = re.sub(RE_BOTOES, " ", sem_ruido)
    sem_ruido = re.sub(RE_INVISIVEL, " ", sem_ruido)
    com_paragrafos = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|section)>", "\n\n", sem_ruido)
    texto = html.unescape(re.sub(r"(?s)<[^>]+>", " ", com_paragrafos))
    texto = texto.replace("\xa0", " ")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n\s*\n\s*(\n\s*)+", "\n\n", texto)
    return "\n".join(linha.strip() for linha in texto.splitlines()).strip()


def extrair_scielo(bruto: str) -> str:
    """Corpo do artigo até as referências, mais as tabelas dos modais."""
    corpo_inicio = re.search(SCIELO_CORPO, bruto)
    if not corpo_inicio:
        raise SystemExit("SciELO: container 'articleTxt' não encontrado — layout mudou?")
    referencias = re.search(SCIELO_REFERENCIAS, bruto)
    fim = referencias.start() if referencias else len(bruto)
    partes = [limpar_html(bruto[corpo_inicio.start():fim])]
    # As tabelas ficam depois das referências; só interessam as de lá, para não
    # duplicar as que já aparecem embutidas no corpo.
    partes += [
        limpar_html(tabela)
        for tabela in blocos_div(bruto, SCIELO_TABELAS)
        if bruto.index(tabela) >= fim
    ]
    return "\n\n".join(parte for parte in partes if parte)


def extrair_opas(bruto: str) -> str:
    """Região de conteúdo da página temática, sem menu, rodapé nem eventos."""
    regiao = blocos_div(bruto, OPAS_CORPO)
    if not regiao:
        raise SystemExit("OPAS: container 'region-content' não encontrado — layout mudou?")
    return limpar_html(regiao[0])


EXTRATORES = {"scielo": extrair_scielo, "opas": extrair_opas}


def cabecalho(fonte: dict, acesso: str) -> str:
    return (
        "=== PROCEDENCIA ===\n"
        f"Titulo: {fonte['titulo']}\n"
        f"Fonte: {fonte['fonte']}\n"
        f"URL: {fonte['url']}\n"
        f"Licenca: {fonte['licenca']}\n"
        f"Acesso: {acesso}\n"
        f"Registro: {fonte['registro']}\n"
        f"Recorte: {fonte['recorte']}\n"
        "Uso: exclusivamente academico — FIAP, projeto CardioIA Fase 1\n"
        "=== FIM PROCEDENCIA ===\n\n"
    )


def main() -> None:
    acesso = dt.date.today().isoformat()
    dir_textos = comum.RAIZ / "docs" / "textos"
    dir_textos.mkdir(parents=True, exist_ok=True)
    linhas_proc = []

    for fonte in FONTES:
        bruto_path = comum.RAIZ / "data" / "tmp" / (fonte["arquivo"] + ".html")
        comum.baixar(fonte["url"], bruto_path)
        bruto = bruto_path.read_text(encoding="utf-8", errors="ignore")
        corpo = EXTRATORES[fonte["extrator"]](bruto)
        saida = dir_textos / fonte["arquivo"]
        saida.write_text(cabecalho(fonte, acesso) + corpo + "\n", encoding="utf-8")
        n = len(corpo.split())
        print(f"{fonte['arquivo']}: {n} palavras")
        linhas_proc.append(
            f"| `{fonte['arquivo']}` | {fonte['titulo']} | {fonte['fonte']} | "
            f"{fonte['licenca']} | {n} | {fonte['recorte']} | [link]({fonte['url']}) |"
        )

    (dir_textos / "PROCEDENCIA.md").write_text(
        "# Procedência dos Textos — Parte 2 (NLP)\n\n"
        f"Coleta realizada em {acesso}. Todos em português do Brasil.\n\n"
        "A contagem de palavras é do texto **já recortado**: de cada página foi\n"
        "extraído só o corpo do conteúdo, sem menu, rodapé nem widgets de\n"
        "métrica. Nos dois artigos do SciELO a lista de referências também ficou\n"
        "de fora — na diretriz da SBC eram cerca de 30 mil palavras de citação\n"
        "bibliográfica, majoritariamente em inglês, que inflavam o volume sem\n"
        "acrescentar prosa clínica. A coluna `Recorte` diz o que entrou em cada\n"
        "arquivo, e o mesmo texto está no cabeçalho de cada `.txt`.\n\n"
        "| Arquivo | Título | Fonte | Licença | Palavras | Recorte | URL |\n"
        "|---|---|---|---|---|---|---|\n" + "\n".join(linhas_proc) + "\n",
        encoding="utf-8",
    )
    print("PROCEDENCIA.md escrito")


if __name__ == "__main__":
    main()
