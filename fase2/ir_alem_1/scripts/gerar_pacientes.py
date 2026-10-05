"""Gera public/data/pacientes.json para o portal a partir da base clínica da Fase 1.

Os dados clínicos (idade, sexo, pressão, colesterol, FC máxima, tipo de dor,
diagnóstico) são REAIS, do UCI Heart Disease consolidado na Fase 1. Os nomes
e contatos são FICTÍCIOS: a base original não identifica ninguém, e o portal
precisa de nomes para ser utilizável.

Uso: python fase2/ir_alem_1/scripts/gerar_pacientes.py
"""
from __future__ import annotations

import json
import pathlib
import random

import pandas as pd

SEED = 42
N_PACIENTES = 120

RAIZ = pathlib.Path(__file__).resolve().parents[3]
ORIGEM = RAIZ / "fase1" / "data" / "numerico" / "heart_disease_clinico.csv"
DESTINO = pathlib.Path(__file__).resolve().parents[1] / "public" / "data" / "pacientes.json"

NOMES = {
    "masculino": ["Antônio", "Carlos", "Eduardo", "Fernando", "Gilberto", "Hélio", "Joaquim",
                  "José", "Luiz", "Marcos", "Nelson", "Osvaldo", "Paulo", "Raimundo",
                  "Roberto", "Sérgio", "Valter", "Wagner", "Benedito", "Domingos"],
    "feminino": ["Ana", "Benedita", "Cecília", "Dalva", "Elza", "Francisca", "Glória",
                 "Helena", "Irene", "Joana", "Lúcia", "Marta", "Neusa", "Odete",
                 "Rosa", "Sônia", "Tereza", "Vera", "Zilda", "Aparecida"],
}
SOBRENOMES = ["Almeida", "Barbosa", "Cardoso", "Carvalho", "Costa", "Dias", "Fernandes",
              "Ferreira", "Gomes", "Lima", "Machado", "Martins", "Melo", "Moreira",
              "Nascimento", "Oliveira", "Pereira", "Ribeiro", "Rocha", "Santos",
              "Silva", "Souza", "Teixeira", "Vieira"]

CENTROS = {
    "cleveland": "Cleveland (EUA)",
    "hungarian": "Budapeste (Hungria)",
    "switzerland": "Zurique (Suíça)",
    "va": "Long Beach (EUA)",
}
TIPO_DOR = {1: "Angina típica", 2: "Angina atípica", 3: "Dor não anginosa", 4: "Assintomático"}


def inteiro_ou_nulo(valor) -> int | None:
    """NaN e o código 0 do UCI ("não medido") viram null. Ver fase1/docs/VIESES.md."""
    if pd.isna(valor) or valor == 0:
        return None
    return int(valor)


def main() -> None:
    base = pd.read_csv(ORIGEM)
    amostra = base.sample(N_PACIENTES, random_state=SEED).reset_index(drop=True)
    rng = random.Random(SEED)

    pacientes = []
    usados: set[str] = set()
    for i, linha in amostra.iterrows():
        while True:
            nome = f"{rng.choice(NOMES[linha.sexo])} {rng.choice(SOBRENOMES)} {rng.choice(SOBRENOMES)}"
            if nome not in usados:
                usados.add(nome)
                break
        pacientes.append({
            "id": i + 1,
            "registroOrigem": linha.paciente_id,
            "nome": nome,
            "idade": int(linha.idade),
            "sexo": linha.sexo,
            "centro": CENTROS[linha.origem_base],
            "pressaoSistolica": inteiro_ou_nulo(linha.pressao_repouso_mmhg),
            "colesterol": inteiro_ou_nulo(linha.colesterol_mgdl),
            "fcMaxima": inteiro_ou_nulo(linha.fc_maxima_bpm),
            "tipoDor": TIPO_DOR[int(linha.tipo_dor_toracica)],
            "anginaExercicio": None if pd.isna(linha.angina_exercicio) else bool(linha.angina_exercicio),
            "doencaCardiaca": bool(linha.doenca_cardiaca),
            "telefone": f"(11) 9{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}",
        })

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(pacientes, ensure_ascii=False, indent=2), encoding="utf-8")
    com_doenca = sum(p["doencaCardiaca"] for p in pacientes)
    print(f"{len(pacientes)} pacientes ({com_doenca} com doença cardíaca) → {DESTINO.relative_to(RAIZ).as_posix()}")


if __name__ == "__main__":
    main()
