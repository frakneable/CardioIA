# fase1/scripts/medir_vieses.py
"""Mede nos dados os vieses documentados em docs/VIESES.md.

Rodar antes de editar VIESES.md: os números do documento devem vir daqui, não
de suposição. É o que separa uma análise de viés de um texto genérico.
"""
from __future__ import annotations

import pandas as pd

import comum


def main() -> None:
    numerico = comum.RAIZ / "data" / "numerico"
    clinico = pd.read_csv(numerico / "heart_disease_clinico.csv")

    print("== distribuição de sexo (global) ==")
    print((clinico["sexo"].value_counts(normalize=True) * 100).round(1).to_string())
    print(clinico["sexo"].value_counts().to_string())

    print("\n== distribuição de sexo por base ==")
    print(
        pd.crosstab(clinico["origem_base"], clinico["sexo"], normalize="index")
        .mul(100).round(1).to_string()
    )

    print("\n== prevalência de doença por base (%) ==")
    print((clinico.groupby("origem_base")["doenca_cardiaca"].mean() * 100).round(1).to_string())

    print("\n== colesterol == 0 (missing codificado como zero) ==")
    zeros = clinico["colesterol_mgdl"] == 0
    print(f"total: {zeros.sum()} de {len(clinico)} ({zeros.mean()*100:.1f}%)")
    print(clinico.loc[zeros, "origem_base"].value_counts().to_string())

    print("\n== pressão de repouso == 0 (missing codificado como zero) ==")
    zeros_pressao = clinico["pressao_repouso_mmhg"] == 0
    print(f"total: {zeros_pressao.sum()} de {len(clinico)} ({zeros_pressao.mean()*100:.2f}%)")
    print(clinico.loc[zeros_pressao, "origem_base"].value_counts().to_string())

    print("\n== faixa etária ==")
    print(clinico["idade"].describe()[["min", "max", "mean"]].round(1).to_string())

    print("\n== nulos por coluna (%) ==")
    print((clinico.isna().mean() * 100).round(1).sort_values(ascending=False).to_string())

    print("\n== classes de imagem ==")
    manifest = pd.read_csv(comum.RAIZ / "assets" / "imagens" / "MANIFEST.csv")
    print(manifest["classe"].value_counts().to_string())


if __name__ == "__main__":
    main()
