# CardioIA — Fase 2: Diagnóstico Automatizado

Projeto acadêmico FIAP. Nesta fase o CardioIA ganha um primeiro "estetoscópio
digital": um módulo que lê relatos de pacientes, reconhece sintomas, sugere
diagnósticos e classifica o risco para priorizar a triagem.

## 👨‍🎓 Integrantes
- Victor Copque dos Reis — RM566821
- Victor Hugo Ferreira Rolim — RM568006

## 🎬 Vídeo de demonstração

**YouTube (não listado):** _link a incluir após a gravação_

## 📌 O que está entregue

| Parte | Entregável | Arquivo |
|---|---|---|
| 1 | 10 frases de sintomas relatados por pacientes | [`parte1/frases_sintomas.txt`](parte1/frases_sintomas.txt) |
| 1 | Mapa de conhecimento sintoma → doença (64 associações, 8 doenças) | [`parte1/mapa_conhecimento.csv`](parte1/mapa_conhecimento.csv) |
| 1 | Código que lê as frases, extrai sintomas e sugere diagnóstico | [`parte1/diagnostico.py`](parte1/diagnostico.py) |
| 1 | Saída gerada pelo código | [`parte1/resultados.csv`](parte1/resultados.csv) |
| 2 | Base de 200 frases rotuladas (alto/baixo risco) | [`parte2/frases_risco.csv`](parte2/frases_risco.csv) |
| 2 | Frases adversariais para testar distorções | [`parte2/frases_adversariais.csv`](parte2/frases_adversariais.csv) |
| 2 | Notebook com TF-IDF, classificação e avaliação | [`parte2/classificador_risco.ipynb`](parte2/classificador_risco.ipynb) |
| Ir Além 2 | Rede neural MLP (Keras) que classifica imagens de ECG em normal/anormal | [`ir_alem_2/`](ir_alem_2/README.md) |

## 🗂️ Estrutura

```
fase2/
├── parte1/      # frases, mapa de conhecimento, extrator e resultados
├── parte2/      # base rotulada, frases adversariais e notebook do classificador
├── ir_alem_2/   # MLP para imagens de ECG: notebook, exemplos de imagens e README próprio
└── tests/       # validação automatizada dos artefatos
```

---

## Parte 1 — Frases de sintomas e extração de informações

### As frases

Dez relatos em primeira pessoa, cada um com **o que o paciente sente**,
**quando começou** e **como afeta a rotina**. Cada frase foi escrita para
representar uma condição diferente. Duas delas exercitam casos difíceis:

- a frase 9 começa com **"Não sinto dor no peito, mas…"**, para testar a
  negação;
- a frase 10 é de um paciente de 78 anos, cujo quadro de insuficiência
  cardíaca aparece como falta de ar ao deitar e tosse noturna, sem dor.

### O mapa de conhecimento

`mapa_conhecimento.csv` segue o formato sugerido no enunciado
(`Sintoma 1 | Sintoma 2 | Doença Associada`), **com uma coluna a mais: `peso`**.

```
sintoma_1,sintoma_2,doenca_associada,peso
dor no peito,aperto no tórax,Infarto Agudo do Miocárdio,2
irradia para o braço esquerdo,dor no braço esquerdo,Infarto Agudo do Miocárdio,3
dor no peito,aperto no tórax,Pericardite,1
```

- **`sintoma_1` e `sintoma_2`** são duas formas de relatar **o mesmo
  sintoma**, como no exemplo do enunciado ("dor no peito", "aperto no tórax").
  Basta uma delas aparecer na frase.
- **`peso` (nossa adição)** indica o quanto o sintoma aponta para aquela
  doença: **3** = característico, **2** = sugestivo, **1** = inespecífico.

**Por que adicionamos o peso.** Um mesmo sintoma aponta para várias doenças.
"Dor no peito" está ligada a infarto, angina e pericardite. Sem peso, uma frase
com "dor no peito" empataria entre as três, e a sugestão seria decidida pela
ordem das linhas no arquivo. Com o peso, sintomas característicos ("dor que
irradia para o braço esquerdo", "sopro no coração") desempatam o diagnóstico de
forma explícita e auditável.

O mapa cobre 8 doenças cardiológicas: infarto agudo do miocárdio, angina,
insuficiência cardíaca, arritmia (fibrilação atrial), hipertensão arterial,
pericardite, valvopatia e TVP/embolia pulmonar.

### Como o código funciona

`diagnostico.py` usa só a biblioteca padrão do Python:

1. **Normalização**: frase e expressões viram minúsculas, sem acento e sem
   pontuação, então "Coração disparado!" e "coracao disparado" se tornam iguais.
2. **Casamento por substring**: a expressão precisa aparecer **inteira** na
   frase, respeitando limites de palavra ("ar" não casa dentro de "parar").
   Não há casamento aproximado. As variações de escrita ficam no CSV, onde
   qualquer pessoa pode auditá-las.
3. **Negação**: se "não", "nunca", "nem" ou "sem" aparece até 3 palavras antes
   do sintoma, ele é descartado.
4. **Ranking**: cada linha que casou soma seu peso à doença. A maior pontuação
   é a sugestão, e as seguintes aparecem como diagnósticos diferenciais.

O código também extrai o **tempo de início** ("há duas horas", "desde ontem",
"hoje de manhã").

### Resultado

As 10 frases recebem o diagnóstico para o qual foram escritas. Exemplo de saída:

```
[09] Não sinto dor no peito, mas há uma semana tenho palpitações e cansaço constante...
     Início:    há uma semana
     Sintomas:  cansaço constante, palpitações
     Negados:   dor no peito
     1º Arritmia (Fibrilação Atrial) (4 pts)
     2º Insuficiência Cardíaca (2 pts)
  => Diagnóstico sugerido: Arritmia (Fibrilação Atrial)
```

Sem a regra de negação, "dor no peito" somaria pontos para infarto e angina
nessa frase.

**Limitações conhecidas:** o casamento exato não reconhece sinônimos que não
estão no CSV nem erros de digitação. A janela de negação é uma heurística e
erra em construções como "não é que eu não sinta dor no peito".

---

## Parte 2 — Classificador de risco

### A base

`frases_risco.csv`, no formato pedido (`frase,situacao`), tem **200 frases
escritas à mão**: 100 de alto risco e 100 de baixo risco. O rótulo segue os
sinais de alarme usados em triagem (dor torácica típica, falta de ar súbita ou
em repouso, desmaio, sinais neurológicos, entre outros). A base inclui casos
propositalmente difíceis: frases leves que mencionam o peito ("peito dolorido
depois do supino") e frases graves que não mencionam ("desmaiei duas vezes
hoje").

### Modelo e resultados

TF-IDF (unigramas e bigramas, **sem remover stopwords**, porque as listas
padrão de português removem "não" e "sem"), comparando **Logistic Regression**
e **Decision Tree**:

| Modelo | Acurácia (teste) | Recall alto risco (teste) | Acurácia (CV 5-fold) | Recall alto risco (CV) |
|---|---|---|---|---|
| **Logistic Regression** | **0,84** | **0,84** | **0,870 ± 0,053** | **0,86** |
| Decision Tree | 0,74 | 0,76 | 0,755 ± 0,043 | 0,65 |

A **Logistic Regression** foi escolhida. A métrica decisiva é o **recall de
alto risco**, porque em triagem deixar passar um paciente grave é muito pior do
que um falso alarme.

### Padrões e distorções: o achado principal

Os coeficientes mostram que o modelo aprendeu **o estilo de escrita do grupo**
além dos sintomas:

- **"não" tem peso positivo**, porque na base aparece em "não passa" e "não
  consigo respirar". Por isso, "**não** sinto dor no peito, só uma coceira" é
  classificada como **alto risco**.
- **"tenho" empurra para baixo risco**: 3 dos 4 falsos negativos do teste
  começam com "tenho…", incluindo "tenho histórico de infarto e a dor voltou".
- **"está" e "meu/minha" empurram para alto risco**: "meu bebê está com
  assadura" vira alto risco.

Em 20 frases adversariais (negação, termos técnicos, linguagem coloquial,
contexto familiar, apresentações atípicas), a acurácia cai para **60%**. O
modelo não conhece "dispneia" nem "síncope". Ele também sub-tria a idosa que
relata infarto como "só cansaço e enjoo", o mesmo viés de sexo e idade medido
na base clínica da Fase 1 ([`fase1/docs/VIESES.md`](../fase1/docs/VIESES.md)).

A seção 8 do notebook detalha cada distorção e propõe mitigações: marcação de
negação, normalização de sinônimos com o mapa da Parte 1, regras de bandeira
vermelha acima do modelo, ajuste de limiar, dados mais diversos e humano no
circuito.

---

## Ir Além 2 — Diagnóstico visual de ECG com MLP

Cada batimento do dataset MIT-BIH (Kaggle) é desenhado como imagem,
pré-processado (tons de cinza, 32×32, normalização) e classificado por uma MLP
em Keras. No teste, com a proporção real de 83% de normais, a rede chega a
**95,9% de acurácia e 94,9% de recall de anormal**, contra 82,8% de acurácia e
0% de recall de um modelo que responde sempre "normal". Detalhes, resultados e
vídeo próprio estão em [`ir_alem_2/README.md`](ir_alem_2/README.md).

---

## ⚙️ Como executar

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # Windows: .venv\Scripts\pip

# Parte 1 — imprime o relatório e gera parte1/resultados.csv
.venv/bin/python fase2/parte1/diagnostico.py

# Parte 2 — abra o notebook no VS Code ou no Jupyter e execute todas as células
# (ele lê os CSVs da própria pasta fase2/parte2)

# Testes das duas fases
.venv/bin/pytest
```

Semente fixa (`SEED = 42`): a divisão treino/teste e os resultados são
idênticos a cada execução.

## 🛡️ Uso responsável

Todas as frases desta fase são **fictícias**, escritas pelo grupo. Nenhum dado
de paciente real foi usado. Os dois módulos são **apoio à decisão** para fins
acadêmicos: sugerem e priorizam, mas não diagnosticam. As distorções
documentadas na Parte 2 mostram por que a decisão final precisa ser de um
profissional de saúde.
