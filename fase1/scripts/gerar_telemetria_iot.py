"""Gera telemetria simulada de dispositivo vestível (IoT) para cada paciente
da base clínica real.

POR QUE SIMULAR: o enunciado pede dados numéricos com pegada IoT, mas nenhuma
base pública de doença cardíaca traz série temporal de vestível. Em vez de
sortear números independentes — que não teriam relação com o desfecho e seriam
inúteis nas fases de ML — cada série é CONDICIONADA aos dados reais do paciente
(idade, fc_maxima_bpm, doenca_cardiaca).

ESTE DADO NÃO É REAL e não corresponde a pessoa alguma. Ver docs/VIESES.md.

Determinístico: seed fixa em comum.SEED. Rodar duas vezes gera bytes idênticos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import comum

DIAS = pd.date_range("2026-08-01", periods=7, freq="D")


def gerar(clinico: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(comum.SEED)
    linhas = []

    for registro in clinico.itertuples(index=False):
        doente = int(registro.doenca_cardiaca) == 1
        idade = float(registro.idade) if pd.notna(registro.idade) else 55.0
        fc_max = float(registro.fc_maxima_bpm) if pd.notna(registro.fc_maxima_bpm) else 150.0

        # Bases por paciente: doença cardíaca eleva FC de repouso e derruba HRV.
        fc_rep_base = 62 + (10 if doente else 0) + (idade - 55) * 0.15
        hrv_base = 55 - (18 if doente else 0) - (idade - 55) * 0.35
        spo2_base = 97.5 - (1.5 if doente else 0)
        pas_base = 124 + (14 if doente else 0) + (idade - 55) * 0.25
        passos_base = 7200 - (2200 if doente else 0) - (idade - 55) * 45
        prob_arritmia = 0.18 if doente else 0.03

        for dia in DIAS:
            fc_rep = np.clip(rng.normal(fc_rep_base, 4), 40, 120)
            hrv = np.clip(rng.normal(hrv_base, 8), 5, 120)
            spo2 = np.clip(rng.normal(spo2_base, 1.0), 85, 100)
            pas = np.clip(rng.normal(pas_base, 9), 80, 220)
            pad = np.clip(pas * rng.uniform(0.60, 0.68), 50, 130)
            passos = int(np.clip(rng.normal(passos_base, 1800), 0, 25000))
            minutos = int(np.clip(passos / 110 + rng.normal(0, 5), 0, 300))
            # FC média sobe com atividade, sem passar do máximo tolerado do paciente.
            fc_media = np.clip(fc_rep + minutos * 0.20 + rng.normal(0, 3), 45, max(45, min(160, fc_max)))

            linhas.append({
                "paciente_id": registro.paciente_id,
                "data": dia.date().isoformat(),
                "fc_repouso_bpm": round(fc_rep, 1),
                "fc_media_bpm": round(fc_media, 1),
                "hrv_ms": round(hrv, 1),
                "spo2_pct": round(spo2, 1),
                "pas_mmhg": round(pas, 1),
                "pad_mmhg": round(pad, 1),
                "passos": passos,
                "minutos_atividade": minutos,
                "alerta_arritmia": int(rng.random() < prob_arritmia),
            })

    return pd.DataFrame(linhas)


def main() -> None:
    clinico = pd.read_csv(comum.RAIZ / "data" / "numerico" / "heart_disease_clinico.csv")
    df = gerar(clinico)
    saida = comum.RAIZ / "data" / "numerico" / "iot_wearable_telemetria.csv"
    df.to_csv(saida, index=False)
    print(f"{len(df)} linhas ({len(clinico)} pacientes x {len(DIAS)} dias) em {saida}")


if __name__ == "__main__":
    main()
