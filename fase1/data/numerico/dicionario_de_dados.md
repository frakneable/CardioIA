# Dicionário de Dados — Parte 1 (Dados Numéricos)

## `heart_disease_clinico.csv` — dados REAIS

Fonte: UCI Machine Learning Repository, Heart Disease (Detrano et al., 1989).
920 registros, 17 colunas. Consolidado de quatro centros por
`scripts/baixar_uci.py`.

| Coluna | Tipo | Unidade / Domínio | Descrição | Nulos |
|---|---|---|---|---|
| `paciente_id` | texto | `<base>-<n>` | Identificador sintético criado por nós na consolidação; a base do UCI não traz identificador algum | 0 |
| `origem_base` | categórico | cleveland, hungarian, switzerland, va | Centro de coleta — necessário para controlar viés de prevalência | 0 |
| `idade` | inteiro | anos (28–77) | Idade do paciente | 0 |
| `sexo` | categórico | masculino, feminino | Sexo biológico registrado | 0 |
| `tipo_dor_toracica` | inteiro | 1 angina típica, 2 angina atípica, 3 dor não anginosa, 4 assintomático | Apresentação clínica da dor torácica | 0 |
| `pressao_repouso_mmhg` | inteiro | mmHg | Pressão arterial sistólica em repouso na admissão. **Atenção: 1 registro com valor `0`** (base `va`), mesma codificação de ausência do UCI — ver observação abaixo | 59 |
| `colesterol_mgdl` | inteiro | mg/dL | Colesterol sérico. **Atenção: 0 significa ausente, não zero real** (172 registros com valor 0, além de nulos declarados) | 30 |
| `glicemia_jejum_alta` | inteiro | 0 não, 1 sim (>120 mg/dL) | Glicemia de jejum elevada | 90 |
| `ecg_repouso` | inteiro | 0 normal, 1 anormalidade ST-T, 2 hipertrofia ventricular esquerda | ECG em repouso | 2 |
| `fc_maxima_bpm` | inteiro | bpm | Frequência cardíaca máxima atingida no teste de esforço | 55 |
| `angina_exercicio` | inteiro | 0 não, 1 sim | Angina induzida por exercício | 55 |
| `depressao_st_oldpeak` | decimal | mm | Depressão do segmento ST induzida por exercício em relação ao repouso | 62 |
| `inclinacao_st` | inteiro | 1 ascendente, 2 plana, 3 descendente | Inclinação do segmento ST no pico do exercício | 309 |
| `n_vasos_obstruidos` | inteiro | 0–3 | Vasos principais com obstrução vistos na angiografia | 611 |
| `talassemia` | inteiro | 3 normal, 6 defeito fixo, 7 defeito reversível | Resultado da cintilografia | 486 |
| `num_diagnostico` | inteiro | 0–4 | Gravidade original do diagnóstico angiográfico | 0 |
| `doenca_cardiaca` | inteiro | 0 ausente, 1 presente | **Variável alvo**, derivada de `num_diagnostico > 0` | 0 |

**Observação sobre `colesterol_mgdl`:** além dos 30 registros marcados como
nulos (`NaN`), há 172 registros com o valor literal `0`, que na base original
do UCI significa "não medido", não um colesterol zero real. Qualquer análise
estatística ou de viés sobre esta coluna deve tratar `0` como dado ausente e
excluí-lo (ou os 202 registros combinados — 30 nulos + 172 zeros — devem ser
computados separadamente das demais medições).

**Observação sobre `pressao_repouso_mmhg`:** há 1 registro (base `va`) com o
valor literal `0`, fisiologicamente impossível para pressão sistólica — mesma
codificação de ausência do dataset original do UCI, mas aqui pontual (1
registro), não um padrão sistêmico como em `colesterol_mgdl`. Ver detalhamento
em `fase1/docs/VIESES.md`, seção 3.

## `iot_wearable_telemetria.csv` — dados SIMULADOS

Gerado por `scripts/gerar_telemetria_iot.py` (seed 42). 6.440 registros
(920 pacientes × 7 dias, 2026-08-01 a 2026-08-07). **Não são dados de pessoas
reais.** Cada série é condicionada a `idade`, `fc_maxima_bpm` e
`doenca_cardiaca` do paciente real correspondente.

| Coluna | Tipo | Unidade / Faixa | Descrição |
|---|---|---|---|
| `paciente_id` | texto | — | Chave estrangeira para `heart_disease_clinico.csv` |
| `data` | data | ISO-8601 | Dia da medição |
| `fc_repouso_bpm` | decimal | bpm (40–120) | FC de repouso do dia |
| `fc_media_bpm` | decimal | bpm (45–160) | FC média nas 24h |
| `hrv_ms` | decimal | ms (5–120) | Variabilidade da FC — cai na presença de doença |
| `spo2_pct` | decimal | % (85–100) | Saturação periférica de oxigênio |
| `pas_mmhg` | decimal | mmHg (80–220) | Pressão sistólica ambulatorial |
| `pad_mmhg` | decimal | mmHg (50–130) | Pressão diastólica ambulatorial |
| `passos` | inteiro | 0–25000 | Passos no dia |
| `minutos_atividade` | inteiro | 0–300 | Minutos de atividade física |
| `alerta_arritmia` | inteiro | 0, 1 | Alerta de ritmo irregular emitido pelo dispositivo |

Nenhuma coluna de `iot_wearable_telemetria.csv` apresenta valores nulos
(verificado via `df.isna().sum()` sobre os 6.440 registros).

**Sobre a coluna "Unidade / Faixa" da tabela acima:** os intervalos indicados
são o **domínio permitido pelo gerador** (os limites do `np.clip` em
`scripts/gerar_telemetria_iot.py`), não a faixa observada nos dados. Os dois
não coincidem: `minutos_atividade`, por exemplo, admite 0–300 por construção,
mas o máximo efetivamente gerado nos 6.440 registros é 122, porque o valor
deriva da contagem de passos e nunca se aproxima do teto. Para a faixa
observada de qualquer coluna, use `df.describe()`.
