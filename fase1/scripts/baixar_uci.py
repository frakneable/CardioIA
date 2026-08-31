"""Baixa os quatro arquivos originais do UCI Heart Disease e os consolida
em um único CSV com nomes de coluna legíveis em português.

Fonte: UCI Machine Learning Repository — Heart Disease (Detrano et al., 1989).
https://archive.ics.uci.edu/dataset/45/heart+disease

Decisão de projeto: os arquivos originais são preservados em data/raw/ e a
consolidação é feita por este script, para que a procedência seja auditável.
Valores ausentes ('?' na origem) tornam-se vazios — exceto colesterol = 0,
que é preservado tal como está por ser um viés documentado em docs/VIESES.md.
"""
from __future__ import annotations

import pandas as pd

import comum

BASE_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/"
    "processed.{base}.data"
)
BASES = ("cleveland", "hungarian", "switzerland", "va")

# Ordem dos 14 atributos conforme heart-disease.names do UCI.
COLUNAS_ORIGEM = [
    "idade", "sexo", "tipo_dor_toracica", "pressao_repouso_mmhg",
    "colesterol_mgdl", "glicemia_jejum_alta", "ecg_repouso", "fc_maxima_bpm",
    "angina_exercicio", "depressao_st_oldpeak", "inclinacao_st",
    "n_vasos_obstruidos", "talassemia", "num_diagnostico",
]

COLUNAS_FINAIS = ["paciente_id", "origem_base"] + COLUNAS_ORIGEM + ["doenca_cardiaca"]

# Tudo que é contagem, medida inteira ou código categórico. `tipo_dor_toracica`
# entra aqui: é um código de 1 a 4, e sem isso saía como 1.0/2.0/3.0/4.0,
# contrariando o dicionário de dados. Só `depressao_st_oldpeak` fica de fora,
# por ser decimal de verdade (mm de depressão do segmento ST).
INTEIRAS = [
    "idade", "tipo_dor_toracica", "pressao_repouso_mmhg", "colesterol_mgdl",
    "glicemia_jejum_alta", "ecg_repouso", "fc_maxima_bpm", "angina_exercicio",
    "inclinacao_st", "n_vasos_obstruidos", "talassemia", "num_diagnostico",
]


def carregar_base(nome: str) -> pd.DataFrame:
    destino = comum.RAIZ / "data" / "raw" / f"processed.{nome}.data"
    comum.baixar(BASE_URL.format(base=nome), destino)
    df = pd.read_csv(destino, header=None, names=COLUNAS_ORIGEM, na_values=["?"])
    df.insert(0, "origem_base", nome)
    df.insert(0, "paciente_id", [f"{nome}-{i:03d}" for i in range(1, len(df) + 1)])
    return df


def consolidar() -> pd.DataFrame:
    df = pd.concat([carregar_base(n) for n in BASES], ignore_index=True)
    df["sexo"] = df["sexo"].map({1.0: "masculino", 0.0: "feminino"})
    df["doenca_cardiaca"] = (df["num_diagnostico"] > 0).astype(int)
    for coluna in INTEIRAS:
        df[coluna] = df[coluna].astype("Int64")
    return df[COLUNAS_FINAIS]


def main() -> None:
    df = consolidar()
    saida = comum.RAIZ / "data" / "numerico" / "heart_disease_clinico.csv"
    saida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(saida, index=False)
    print(f"{len(df)} linhas escritas em {saida}")
    print(df["origem_base"].value_counts().to_string())


if __name__ == "__main__":
    main()
