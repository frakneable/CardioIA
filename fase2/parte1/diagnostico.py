"""CardioIA — Fase 2, Parte 1: extração de sintomas e sugestão de diagnóstico.

Lê os relatos de `frases_sintomas.txt`, procura neles as expressões do mapa de
conhecimento (`mapa_conhecimento.csv`) e sugere um diagnóstico por frase.

Como funciona, em quatro passos:
  1. Normalização: frase e expressões viram minúsculas, sem acento e sem
     pontuação. Assim "Coração disparado!" e "coracao disparado" são iguais.
  2. Casamento por substring: uma expressão é encontrada quando aparece inteira
     na frase normalizada, respeitando limites de palavra ("ar" não casa dentro
     de "parar"). Não há casamento aproximado: as variações de escrita ficam
     no CSV, onde qualquer pessoa consegue auditá-las.
  3. Negação: se "não", "nunca", "nem" ou "sem" aparece até JANELA_NEGACAO
     palavras antes da expressão, o sintoma é descartado ("não sinto dor no
     peito" não conta como dor no peito).
  4. Ranking: cada linha do CSV que casou soma o seu `peso` à doença associada.
     A doença com maior pontuação é a sugestão.

Uso:
    python fase2/parte1/diagnostico.py
Gera `resultados.csv` ao lado deste script e imprime o relatório no console.
"""
from __future__ import annotations

import csv
import pathlib
import re
import unicodedata
from dataclasses import dataclass, field

DIR = pathlib.Path(__file__).resolve().parent
ARQ_FRASES = DIR / "frases_sintomas.txt"
ARQ_MAPA = DIR / "mapa_conhecimento.csv"
ARQ_RESULTADOS = DIR / "resultados.csv"

PALAVRAS_NEGACAO = {"nao", "nunca", "nem", "sem"}
JANELA_NEGACAO = 3

# Expressões de tempo de início, buscadas na frase original em minúsculas.
# Cobrem "há duas horas", "há alguns meses", "faz 3 dias", "desde ontem" e
# "hoje de manhã".
_UNIDADES = r"(?:minutos?|horas?|dias?|semanas?|m[eê]s|meses|anos?)"
PADROES_TEMPO = [
    re.compile(rf"\b(?:h[aá]|faz)\s+(?:mais de\s+|uns\s+|umas\s+)?\S+\s+{_UNIDADES}\b"),
    re.compile(r"\bdesde\s+(?:ontem|anteontem|hoje|a semana passada|o m[eê]s passado|\S+)"),
    re.compile(r"\bhoje de manh[aã]\b"),
]


@dataclass
class LinhaMapa:
    """Uma linha do mapa de conhecimento.

    `sintoma_1` e `sintoma_2` são duas formas de relatar o MESMO sintoma (como
    no exemplo do enunciado, "dor no peito" e "aperto no tórax"). Basta uma
    delas aparecer para a linha casar.

    `peso` é a nossa adição ao formato `Sintoma 1 | Sintoma 2 | Doença
    Associada` do enunciado. Ele indica o quanto o sintoma aponta para aquela
    doença:
        3 = característico (ex.: dor que irradia para o braço → infarto)
        2 = frequente, sugestivo
        1 = inespecífico, só compatível (ex.: tontura)
    Sem o peso, uma frase com "dor no peito" empataria entre infarto, angina e
    pericardite, e o diagnóstico sairia pela ordem das linhas do arquivo.
    """
    sintoma_1: str
    sintoma_2: str
    doenca: str
    peso: int

    @property
    def expressoes(self) -> list[str]:
        return [e for e in (self.sintoma_1, self.sintoma_2) if e]


@dataclass
class Resultado:
    frase_id: int
    frase: str
    inicio: str | None
    sintomas: list[str] = field(default_factory=list)
    negados: list[str] = field(default_factory=list)
    ranking: list[tuple[str, int]] = field(default_factory=list)

    @property
    def diagnostico(self) -> str:
        return self.ranking[0][0] if self.ranking else "sem sintomas reconhecidos"


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos e sem pontuação, com espaços simples."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sem_acento).split())


def carregar_mapa(caminho: pathlib.Path = ARQ_MAPA) -> list[LinhaMapa]:
    with open(caminho, encoding="utf-8", newline="") as f:
        return [
            LinhaMapa(
                sintoma_1=linha["sintoma_1"].strip(),
                sintoma_2=linha["sintoma_2"].strip(),
                doenca=linha["doenca_associada"].strip(),
                peso=int(linha["peso"]),
            )
            for linha in csv.DictReader(f)
        ]


def carregar_frases(caminho: pathlib.Path = ARQ_FRASES) -> list[str]:
    return [l.strip() for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]


def encontrar(expressao: str, tokens: list[str]) -> list[int]:
    """Posições (índice de token) onde `expressao` aparece inteira em `tokens`.

    Comparar listas de tokens é o mesmo que buscar substring com limite de
    palavra: "ar" não casa dentro de "parar"."""
    alvo = expressao.split()
    n = len(alvo)
    return [i for i in range(len(tokens) - n + 1) if tokens[i:i + n] == alvo]


def negado(tokens: list[str], inicio: int) -> bool:
    """True se há palavra de negação nas JANELA_NEGACAO palavras anteriores."""
    return any(t in PALAVRAS_NEGACAO for t in tokens[max(0, inicio - JANELA_NEGACAO):inicio])


def extrair_inicio(frase: str) -> str | None:
    """Todas as menções de tempo de início, na ordem em que aparecem."""
    texto = frase.lower()
    achados = sorted(
        (m.start(), m.group(0)) for p in PADROES_TEMPO for m in p.finditer(texto)
    )
    return "; ".join(t for _, t in achados) or None


def analisar(frase_id: int, frase: str, mapa: list[LinhaMapa]) -> Resultado:
    tokens = normalizar(frase).split()
    res = Resultado(frase_id=frase_id, frase=frase, inicio=extrair_inicio(frase))
    pontos: dict[str, int] = {}

    for linha in mapa:
        casou = False
        for expr in linha.expressoes:
            # Casa na forma normalizada, mas registra a forma escrita no CSV.
            for pos in encontrar(normalizar(expr), tokens):
                if negado(tokens, pos):
                    if expr not in res.negados:
                        res.negados.append(expr)
                else:
                    casou = True
                    if expr not in res.sintomas:
                        res.sintomas.append(expr)
        # A linha soma o peso uma única vez, mesmo que as duas formas do
        # sintoma apareçam na frase.
        if casou:
            pontos[linha.doenca] = pontos.get(linha.doenca, 0) + linha.peso

    # Maior pontuação primeiro; empate desempatado pelo nome, para a saída ser
    # determinística.
    res.ranking = sorted(pontos.items(), key=lambda kv: (-kv[1], kv[0]))
    return res


def salvar(resultados: list[Resultado], caminho: pathlib.Path = ARQ_RESULTADOS) -> None:
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frase_id", "frase", "inicio", "sintomas_encontrados",
                    "sintomas_negados", "ranking", "diagnostico_sugerido"])
        for r in resultados:
            w.writerow([
                r.frase_id, r.frase, r.inicio or "",
                "; ".join(r.sintomas), "; ".join(r.negados),
                "; ".join(f"{d} ({p})" for d, p in r.ranking),
                r.diagnostico,
            ])


def imprimir(r: Resultado) -> None:
    print(f"\n[{r.frase_id:02d}] {r.frase}")
    print(f"     Início:    {r.inicio or '—'}")
    print(f"     Sintomas:  {', '.join(r.sintomas) or '—'}")
    if r.negados:
        print(f"     Negados:   {', '.join(r.negados)}")
    for i, (doenca, pts) in enumerate(r.ranking[:3], 1):
        print(f"     {i}º {doenca} ({pts} pts)")
    print(f"  => Diagnóstico sugerido: {r.diagnostico}")


def main() -> list[Resultado]:
    mapa = carregar_mapa()
    frases = carregar_frases()
    resultados = [analisar(i, f, mapa) for i, f in enumerate(frases, 1)]

    print(f"Mapa de conhecimento: {len(mapa)} associações, "
          f"{len({l.doenca for l in mapa})} doenças. Frases: {len(frases)}.")
    for r in resultados:
        imprimir(r)

    salvar(resultados)
    print(f"\nResultados salvos em {ARQ_RESULTADOS.relative_to(DIR.parents[1]).as_posix()}")
    print("Aviso: apoio à decisão para fins acadêmicos — não substitui avaliação médica.")
    return resultados


if __name__ == "__main__":
    main()
