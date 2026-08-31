# CardioIA — Fase 1: Batimentos de Dados

Projeto acadêmico FIAP. Esta fase levanta, organiza e documenta as três bases de
dados que alimentarão os módulos de Machine Learning, NLP, Visão Computacional e
IoT do CardioIA nas fases seguintes.

## 👨‍🎓 Integrantes
- Victor Copque dos Reis — RM566821
- Victor Hugo Ferreira Rolim — RM568006

## 📌 O que está entregue

| Parte | Conteúdo | Volume | Formato | Origem |
|---|---|---|---|---|
| 1 — Numérico (IoT) | Base clínica de pacientes cardíacos + telemetria de vestível | 920 pacientes · 6.440 registros de telemetria | `.csv` | **real** (UCI) + **simulado** |
| 2 — Textual (NLP) | Artigo científico, diretriz clínica e material de divulgação | 3 arquivos · ~77,7 mil palavras de prosa clínica | `.txt` | **real** (SciELO, OPAS/OMS) |
| 3 — Visual (VC) | ECGs de 12 derivações rotulados em 4 classes | 120 imagens | `.jpg` | **real** (Mendeley Data) |

## 🔗 Links públicos (Google Drive)

Os dados estão espelhados no Drive com acesso público de leitura. **O conteúdo é
idêntico ao do repositório**: a integridade das 120 imagens é verificável pela
coluna `sha256` de `fase1/assets/imagens/MANIFEST.csv`; os CSVs e os 3 `.txt`
são idênticos por construção, pois o espelho é montado por
`fase1/scripts/preparar_espelho_drive.py` a partir dos mesmos arquivos do
repositório.

| Conteúdo | Link |
|---|---|
| Pasta completa da Fase 1 | https://drive.google.com/drive/folders/1rYHNEZ5UQmAfHRl7dxJOLV8q1CFoH7F7 |
| Parte 1 — dados numéricos | https://drive.google.com/drive/folders/19ErNtim54QtI3zmjq-4Bns6Evz551a5s |
| Parte 2 — textos | https://drive.google.com/drive/folders/1DCXtCI0xRQ2LbPB44YpKi2El1lcuS5vG |
| Parte 3 — imagens | https://drive.google.com/drive/folders/1d2xbiJqanHfJ8kuXgbIHqgUa0Qsbx_Aa |

## 🗂️ Estrutura do repositório

```
fase1/
├── data/
│   ├── raw/                 # os 4 arquivos originais do UCI, intactos
│   └── numerico/            # CSVs consolidados + dicionário de dados
├── docs/
│   ├── textos/              # os 3 .txt + PROCEDENCIA.md
│   ├── GOVERNANCA.md        # procedência, licenças, LGPD, integridade
│   └── VIESES.md            # vieses medidos nos dados + mitigações
├── assets/imagens/          # 120 ECGs + MANIFEST.csv (classe, origem, hash)
├── notebooks/               # esqueleto de exploração para as fases seguintes
├── scripts/                 # scripts que geram tudo acima
└── tests/                   # validação automatizada dos artefatos
```

## Parte 1 — Dados Numéricos (IoT)

### Origem

**São dados reais.** `heart_disease_clinico.csv` vem do *Heart Disease Data Set*
do UCI Machine Learning Repository (Detrano et al., 1989), reconstruído a partir
dos **quatro arquivos originais** dos centros de Cleveland (303), Hungria (294),
Suíça (123) e Long Beach VA (200) — **920 registros**, bem acima do mínimo de
100. Optamos por baixar e consolidar os arquivos primários em vez de usar um CSV
já pronto de terceiros, para que a procedência fosse auditável.

`iot_wearable_telemetria.csv` **é simulado** e está rotulado como tal em todo
lugar onde aparece. O enunciado pede a pegada IoT, mas nenhuma base pública de
doença cardíaca traz série temporal de vestível. Geramos 7 dias por paciente
(6.440 registros) com séries **condicionadas aos dados reais** do paciente —
idade, FC máxima e desfecho. Sortear valores independentes produziria ruído sem
correlação com o desfecho e inútil nas fases de modelagem.

### Variáveis mais relevantes do ponto de vista clínico

| Variável | Por que importa |
|---|---|
| `depressao_st_oldpeak` | Depressão do segmento ST induzida por esforço, em mm. Marcador direto de isquemia miocárdica sob demanda e a variável de maior poder discriminativo nesta base. |
| `inclinacao_st` | A **forma** do segmento ST no pico do esforço. Infradesnivelamento descendente é bem mais preocupante que ascendente com a mesma amplitude — informação que o valor numérico sozinho não carrega. |
| `angina_exercicio` | Sintoma provocado sob condição controlada: separa dor torácica de origem isquêmica de dor inespecífica. |
| `fc_maxima_bpm` | FC máxima atingida no esforço. Baixa capacidade cronotrópica é preditor independente de desfecho cardiovascular. |
| `tipo_dor_toracica` | Inclui a categoria **assintomático** — justamente onde a triagem humana falha e um modelo agrega mais valor. |
| `idade` e `sexo` | Fatores de risco não modificáveis e, ao mesmo tempo, os principais eixos de viés desta base (ver `VIESES.md`). |
| `hrv_ms` (IoT) | Variabilidade da FC, proxy contínuo de tônus autonômico — o tipo de sinal que só o monitoramento vestível oferece, entre consultas. |

O detalhe de cada coluna, com unidade, domínio e contagem de nulos, está em
[`fase1/data/numerico/dicionario_de_dados.md`](fase1/data/numerico/dicionario_de_dados.md).

## Parte 2 — Dados Textuais (NLP)

Três textos, escolhidos para cobrir **registros de linguagem diferentes** — o
contraste é o que torna as análises abaixo defensáveis:

| Arquivo | Conteúdo | Registro | Licença |
|---|---|---|---|
| `01_scielo_mortalidade_dcv.txt` | Taxas de mortalidade por DCV e câncer no Brasil, 1996-2017 (Arq. Bras. Cardiologia) | científico | CC BY 4.0 |
| `02_sbc_diretriz_hipertensao.txt` | Diretrizes Brasileiras de Hipertensão Arterial – 2020 (SBC/SBH/SBN) | clínico normativo | CC BY 4.0 |
| `03_opas_dcv_divulgacao.txt` | Página temática de doenças cardiovasculares da OPAS/OMS | divulgação leiga | conteúdo público |

**O que foi recortado de cada página.** Baixar a página inteira e remover as
tags deixa menu, rodapé e widgets de métrica dentro do corpus — `Baixar em
RIS`, `SciELO Analytics`, `PlumX` viram texto solto e contaminam qualquer
tokenização. Por isso `baixar_textos.py` recorta o container do conteúdo antes
de limpar: `div.articleTxt` mais as tabelas no SciELO, `div.region-content` na
OPAS. **A lista de referências dos dois artigos do SciELO também ficou de
fora** — na diretriz da SBC eram cerca de 30 mil palavras de citação
bibliográfica, majoritariamente em inglês, que inflavam o volume sem
acrescentar prosa clínica em português. As 77,7 mil palavras contadas acima
são, portanto, texto corrido de conteúdo: 5.786 no artigo, 70.213 na diretriz
e 1.704 na página da OPAS. O recorte aplicado está declarado no cabeçalho de
cada `.txt` e na coluna `Recorte` de `PROCEDENCIA.md`, e
`test_sem_boilerplate_de_navegacao` falha se algum desses termos voltar.

### Como esses textos podem ser explorados por algoritmos de NLP

**Extração de sintomas e entidades clínicas (NER).** A diretriz da SBC traz
terminologia clínica densa e padronizada — nomes de fármacos, classes de risco,
limiares pressóricos, comorbidades. É a base para treinar ou avaliar um
extrator que leia texto livre de anamnese e devolva campos estruturados. *Por
que importa:* a triagem do CardioIA vai receber queixa em texto livre, e sem
essa etapa não existe entrada para o modelo de risco.

**Classificação de tópicos.** Os três documentos cobrem eixos distintos —
epidemiologia, diagnóstico/tratamento e prevenção. Servem como conjunto rotulado
inicial para um classificador que roteie conteúdo ao módulo certo da
plataforma. *Por que importa:* é o que permite ao agente inteligente escolher a
fonte adequada antes de responder, em vez de misturar diretriz clínica com
material de campanha.

**Análise de sentimento e legibilidade.** O material da OPAS é escrito para o
público; a diretriz, para o especialista. Comparar os dois calibra o tom da
comunicação com o paciente e permite medir se uma resposta gerada está no nível
de linguagem adequado ao destinatário. *Por que importa:* na fase de assistência
remota, uma orientação tecnicamente correta e incompreensível é uma orientação
que não é seguida.

Procedência completa em
[`fase1/docs/textos/PROCEDENCIA.md`](fase1/docs/textos/PROCEDENCIA.md).

## Parte 3 — Dados Visuais (VC)

**120 imagens** de ECG de 12 derivações, amostradas do *ECG Images dataset of
Cardiac Patients* (Khan & Hussain, Mendeley Data,
[DOI 10.17632/gwbz3fsgp8.2](https://doi.org/10.17632/gwbz3fsgp8.2), **CC BY
4.0**), que reúne 928 imagens coletadas no Ch. Pervaiz Elahi Institute of
Cardiology com aparelho EDAN SERIES-3.

| Classe | Imagens |
|---|---|
| `normal` | 30 |
| `infarto` (MI) | 30 |
| `historico_infarto` (PMI) | 30 |
| `arritmia` (batimento anormal) | 30 |

A amostra é **balanceada** e não proporcional: a origem é desbalanceada e
equilibrar as classes já na coleta mitiga viés de classe no treino. O efeito
colateral — a amostra não reflete prevalência real — está declarado em
`VIESES.md`. As imagens foram normalizadas para JPEG de lado máximo 1024px, o
que preserva a legibilidade do traçado e mantém o repositório clonável.

**Deduplicação por hash de conteúdo.** Durante a preparação descobrimos que o
dataset Mendeley de origem contém imagens **byte-idênticas sob nomes de
arquivo diferentes** — a classe `infarto`/MI, por exemplo, tem apenas 30
imagens de conteúdo distinto entre 239 arquivos. Por isso `preparar_imagens.py`
deduplica pelo hash SHA-256 do conteúdo **antes** de amostrar, e as 120 imagens
finais têm 120 hashes distintos (registrados em `MANIFEST.csv`). A análise
completa, incluindo o efeito colateral de a classe `infarto` esgotar todo o
conteúdo único disponível na origem, está em `VIESES.md`.

### Como essas imagens podem ser analisadas por Visão Computacional

**Detecção de bordas e extração do traçado.** O ECG em papel é uma curva escura
sobre grade milimetrada. Operadores de borda (Canny, Sobel) somados a
limiarização adaptativa separam curva de grade e permitem **digitalizar o sinal**
a partir da imagem. *Por que importa:* recupera o sinal 1D a partir de exame
arquivado em papel — o formato em que está a maior parte do histórico clínico
brasileiro.

**Segmentação e medição de intervalos.** Localizado o traçado, dá para segmentar
o complexo QRS e medir intervalos PR, QT e o segmento ST em pixels, convertidos
para milissegundos pela escala da grade. *Por que importa:* são exatamente as
medidas que o cardiologista usa, então o modelo produz uma saída auditável por
humano, em vez de um escore opaco.

**Classificação por CNN com transfer learning.** Com 4 classes rotuladas e
poucas imagens por classe, o caminho é ajustar uma rede pré-treinada em vez de
treinar do zero. *Por que importa:* é o módulo de triagem — priorizar quem
precisa de laudo humano primeiro.

**Detecção de anomalia não supervisionada.** Um autoencoder treinado só nos
ECGs normais sinaliza desvio pelo erro de reconstrução. *Por que importa:*
achados raros nunca terão exemplos rotulados suficientes; detectar "isto não é
normal" é viável mesmo sem saber nomear a condição.

Cada imagem está registrada em `MANIFEST.csv` com classe, arquivo de origem, URL
e hash SHA-256.

## 🛡️ Governança de dados e viés

Dois documentos, e eles não são acessórios da entrega:

- [`fase1/docs/GOVERNANCA.md`](fase1/docs/GOVERNANCA.md) — procedência e licença
  de cada base, finalidade, situação de LGPD, verificação de integridade por
  hash e instruções de reprodução.
- [`fase1/docs/VIESES.md`](fase1/docs/VIESES.md) — onze vieses **medidos nos
  dados**, não genéricos, cada um com risco clínico e mitigação. Entre eles: o
  desequilíbrio de sexo, o colesterol ausente gravado como `0` em mais de 170
  registros, a prevalência muito diferente entre os quatro centros, a
  duplicação de imagens na fonte e o viés de aparelho único nas imagens.

**Uso exclusivamente acadêmico.** Nada aqui se destina a decisão clínica real.
As bases chegam pseudonimizadas na origem — as imagens de ECG ainda trazem o
número de prontuário e a data do exame impressos no traçado, como publicados
pelos autores, e por isso são tratadas como dado sensível de saúde
(ver `GOVERNANCA.md` §3) — e a telemetria IoT é sintética.

## ⚙️ Como reproduzir

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python fase1/scripts/baixar_uci.py            # Parte 1 — base real
.venv/bin/python fase1/scripts/gerar_telemetria_iot.py   # Parte 1 — telemetria
.venv/bin/python fase1/scripts/baixar_textos.py          # Parte 2
.venv/bin/python fase1/scripts/preparar_imagens.py       # Parte 3

.venv/bin/pytest                                         # valida os artefatos
```

Semente fixa (`SEED = 42`): a telemetria e a amostra de imagens saem idênticas a
cada execução.

## 📚 Referências

- Detrano, R.; Janosi, A.; Steinbrunn, W.; Pfisterer, M. *Heart Disease Data
  Set*. UCI Machine Learning Repository, 1989.
- Barroso, W.K.S. et al. *Diretrizes Brasileiras de Hipertensão Arterial – 2020*.
  Arq. Bras. Cardiol., 2021;116(3):516-658. CC BY 4.0.
- Khan, A.H.; Hussain, M. *ECG Images dataset of Cardiac Patients*. Mendeley
  Data, v2, 2021. DOI 10.17632/gwbz3fsgp8.2. CC BY 4.0.
- Organização Pan-Americana da Saúde. *Doenças cardiovasculares*.
