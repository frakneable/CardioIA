# Governança de Dados — CardioIA Fase 1

Documento que responde, para cada base: de onde veio, sob qual licença, para
que serve, o que foi feito com ela e como verificar que não foi alterada.

## 1. Procedência e licença

| Parte | Base | Fonte | Licença | Acesso | Atribuição obrigatória |
|---|---|---|---|---|---|
| 1 | `heart_disease_clinico.csv` | UCI ML Repository — Heart Disease | Uso acadêmico livre | anônimo, HTTP | Detrano, R. et al. (1989); Janosi, Steinbrunn, Pfisterer, Detrano — UCI ML Repository |
| 1 | `iot_wearable_telemetria.csv` | **gerado por nós** | — (dado sintético) | `scripts/gerar_telemetria_iot.py` | — |
| 2 | `01_scielo_mortalidade_dcv.txt` | SciELO — Arq. Bras. Cardiologia | **CC BY 4.0** | anônimo, HTTP | conforme cabeçalho do arquivo |
| 2 | `02_sbc_diretriz_hipertensao.txt` | SciELO — Arq. Bras. Cardiologia (SBC/SBH/SBN) | **CC BY 4.0** | anônimo, HTTP | Barroso, W.K.S. et al., Diretrizes Brasileiras de Hipertensão Arterial – 2020 |
| 2 | `03_opas_dcv_divulgacao.txt` | OPAS/OMS | conteúdo público, citado com atribuição | anônimo, HTTP | Organização Pan-Americana da Saúde |
| 3 | 120 imagens de ECG | Mendeley Data, DOI 10.17632/gwbz3fsgp8.2 | **CC BY 4.0** | anônimo, HTTP | Khan, A.H.; Hussain, M. — ECG Images dataset of Cardiac Patients |

Todas as licenças permitem a redistribuição feita aqui (repositório + espelho no
Drive), desde que a atribuição acima seja preservada.

## 2. Finalidade

Uso **exclusivamente acadêmico**, no âmbito da disciplina de IA da FIAP. Nenhum
dado, modelo ou saída deste projeto se destina a decisão clínica real, e nada
aqui constitui orientação médica.

## 3. Dados pessoais e LGPD

- As três bases públicas chegam **pseudonimizadas na origem** — não
  anonimizadas, e a diferença importa. Em nenhuma delas há nome, documento
  civil, endereço ou contato. Mas **as imagens de ECG preservam, impresso no
  próprio traçado, o número de prontuário da instituição de origem, o sexo e a
  data e hora do exame** (por exemplo, `ID: 177232` e `2020-10-20 05:49:00 PM`
  em `normal_001.jpg`). É assim que o dataset foi publicado pelos autores, sob
  CC BY 4.0, e não há chave pública que ligue esses números a uma pessoa: a
  reidentificação dependeria do prontuário do Ch. Pervaiz Elahi Institute of
  Cardiology, ao qual não temos nem buscamos acesso. Ainda assim, o dado é
  pseudônimo, não anônimo, e tratá-lo como anônimo seria um erro de
  classificação — por isso o registro explícito aqui.
- As bases numéricas (UCI), essas sim, chegam sem qualquer identificador de
  origem: cada centro publicou apenas os 14 atributos clínicos.
- O `paciente_id` (`cleveland-001`) é um identificador **criado por nós** na
  consolidação, sequencial e sem vínculo com identidade real. Não é
  reidentificável.
- A telemetria IoT é **sintética**. Está rotulada como tal no dicionário de
  dados, no cabeçalho do script e neste documento, para que não seja confundida
  com medição real de paciente.
- Nenhum dado pessoal do grupo ou de terceiros é coletado pelo projeto.
- **LGPD:** nenhuma pessoa é identificável a partir do que está publicado aqui,
  e o projeto não detém meio de reidentificação. Como as imagens são
  pseudonimizadas e não anônimas (art. 12), não afirmamos que a LGPD é
  simplesmente inaplicável: a postura adotada é a de tratar as imagens como se
  fossem dado pessoal sensível de saúde (art. 5º, II) — uso restrito à
  finalidade acadêmica declarada, sem cruzamento com outras bases e sem
  tentativa de reidentificação. É a hipótese mais conservadora, e nada no
  projeto depende de ela ser afastada.

## 4. Integridade e verificação

- Os quatro arquivos originais do UCI ficam intactos em `data/raw/`; o CSV
  consolidado é derivado, nunca editado à mão.
- `assets/imagens/MANIFEST.csv` registra o **SHA-256** de cada imagem, com o
  nome do arquivo de origem e a URL. Os testes em `tests/test_imagens.py`
  recalculam e comparam os hashes.
- O espelho no Google Drive é verificável contra o repositório pelos mesmos
  hashes para as 120 imagens; os CSVs e os 3 `.txt` são idênticos por
  construção, pois o espelho é montado por `scripts/preparar_espelho_drive.py`
  a partir dos mesmos arquivos do repositório.

## 5. Reprodutibilidade

Todo artefato derivado é regenerável do zero:

```bash
.venv/bin/python fase1/scripts/baixar_uci.py
.venv/bin/python fase1/scripts/gerar_telemetria_iot.py
.venv/bin/python fase1/scripts/baixar_textos.py
.venv/bin/python fase1/scripts/preparar_imagens.py
.venv/bin/pytest
```

A semente aleatória é fixa (`SEED = 42` em `scripts/comum.py`), então a
telemetria e a amostra de imagens são idênticas a cada execução — o que
`test_iot_deterministica` verifica. Essa garantia para a amostra de imagens
depende também de o Mendeley continuar servindo a mesma listagem de arquivos:
uma nova versão do dataset de origem produziria uma amostra de 120 diferente
mesmo com a mesma semente.

## 6. Acesso

- Repositório GitHub **privado durante o desenvolvimento**; para a entrega e
  correção, ele é aberto à equipe docente — seja tornado público, seja
  compartilhado diretamente com o corpo docente.
- Espelho no Google Drive com **link público de leitura**, contendo **apenas os
  dados** (CSVs, textos e imagens).

## 7. Ciclo de vida

Os dados são retidos enquanto o projeto acadêmico durar. Como toda base é
pública e reprodutível pelos scripts, não há necessidade de arquivamento
especial ao final.
