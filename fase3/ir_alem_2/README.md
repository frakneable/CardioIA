# CardioIA — Fase 3, Ir Além 2: IA em séries temporais de batimentos

> [← Fase 3](../README.md) · Relatório: [`RELATORIO.pdf`](RELATORIO.pdf) ([`.md`](RELATORIO.md))

Cada batimento do coração é **normal** ou **anormal**? Comparamos um
classificador tradicional, a **regressão logística**, com uma **rede
neuromórfica de neurônios LIF** (*Leaky Integrate-and-Fire*), os dois com
exatamente a mesma entrada: a onda do batimento e a série temporal dos
intervalos entre batimentos (RR).

## 👨‍🎓 Integrantes
- Victor Copque dos Reis — RM566821
- Victor Hugo Ferreira Rolim — RM568006

## 🎬 Vídeo

**YouTube (não listado):** _link a adicionar_

## 📌 Arquivos

| Arquivo | Conteúdo |
|---|---|
| [`series_temporais_lif.ipynb`](series_temporais_lif.ipynb) | Notebook completo, comentado e já executado |
| [`RELATORIO.pdf`](RELATORIO.pdf) · [`RELATORIO.md`](RELATORIO.md) | Relatório comparativo (2 páginas) |
| [`figuras/`](figuras/) | Gráficos do notebook usados no relatório |
| [`../tests/test_ir_alem2_series.py`](../tests/test_ir_alem2_series.py) | Testes: notebook executado sem erro, divisão por paciente, entregáveis |

## Dados

**MIT-BIH Arrhythmia Database** (PhysioNet): 48 gravações de ECG de 30 min,
com cada batimento anotado por cardiologistas. O notebook baixa direto do
PhysioNet com a biblioteca `wfdb` (≈ 80 MB, para `dados/`, fora do git).

- Classes da norma **AAMI EC57**: normal (N) × anormal (S supraventricular,
  V ventricular, F fusão).
- **Divisão por paciente** (de Chazal et al., 2004): 22 gravações para treino
  e 22 de **outros pacientes** para teste, ~50 mil batimentos de cada lado.
  Sortear batimentos misturaria a mesma pessoa no treino e no teste e inflaria
  o resultado.
- Entrada: janela de 0,65 s ao redor do pico R (117 amostras) + 5 atributos
  de ritmo (RR anterior, seguinte, médio e duas razões).

## Os modelos

| | Regressão logística | Rede LIF |
|---|---|---|
| Ideia | soma ponderada → sigmoide | 300 neurônios que integram, vazam e disparam spikes |
| Como a entrada chega | os 122 números de uma vez | a onda amostra por amostra (canais ON/OFF); o ritmo como corrente constante |
| O que é treinado | os 123 pesos | só a leitura (1.201 pesos); os 11 mil pesos da rede são fixos e aleatórios |
| Hiperparâmetros | `C`, por validação cruzada por paciente | escala da corrente, idem |

O neurônio LIF, discretizado: `v ← β·v + (1−β)·R·I`, com `β = e^(−Δt/τ)`,
`τ = 20 ms`; ao passar do limiar 1, dispara e volta a 0.

## Resultados (teste: 22 pacientes nunca vistos)

| Métrica | Regressão logística | Rede LIF |
|---|---|---|
| Acurácia balanceada | **0,898** | 0,828 |
| Sensibilidade (arritmias detectadas) | **0,908** | 0,781 |
| Especificidade | **0,889** | 0,875 |
| AUC | **0,960** | 0,897 |
| Acurácia balanceada com ruído forte (σ = 1) | 0,589 | **0,867** |
| Operações por batimento | **122** | ~73 mil MAC + ~200 mil somas |
| Inferência por batimento (CPU) | **0,1 µs** | ~120 µs |

- **Sinal limpo:** a regressão logística vence, principalmente nas arritmias
  supraventriculares, que se denunciam pelo ritmo ("chegou cedo").
- **Sinal ruidoso:** a rede LIF quase não perde desempenho, enquanto a
  regressão logística cai para perto do chute.
- **Custo:** numa CPU, a LIF é ~1.000× mais cara. A vantagem de energia só
  aparece em hardware neuromórfico, que trabalha por eventos.

Análise completa, gráficos e limitações no notebook e no relatório.

## Como rodar

```bash
pip install -r requirements.txt     # na raiz do repositório
cd fase3/ir_alem_2
jupyter notebook series_temporais_lif.ipynb
```

A execução completa leva ~3 min num notebook comum (a maior parte é a simulação
dos neurônios LIF sobre 100 mil batimentos).
