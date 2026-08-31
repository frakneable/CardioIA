# Análise de Viés — CardioIA Fase 1

Todo número deste documento foi medido nos dados por
`scripts/medir_vieses.py`. Nada aqui é suposição. A saída bruta é reproduzível
rodando `scripts/medir_vieses.py`.

## 1. Viés de sexo

78,9% dos 920 registros são de homens (726 contra 194 mulheres, 21,1%). A
desproporção piora por centro: 32,0%/68,0% (mulheres/homens) em Cleveland, mas
apenas 8,1%/91,9% em Switzerland e 3,0%/97,0% em VA.

**Risco:** um modelo de triagem treinado assim aprende o padrão de apresentação
masculino. O problema é clínico, não só estatístico: infarto em mulheres se
apresenta com mais frequência por sintomas atípicos (náusea, dor mandibular,
fadiga) em vez de dor torácica clássica — exatamente o caso que o modelo verá
menos. Erro de triagem aqui é falso negativo em quem já é subdiagnosticado.

**Mitigação para as fases seguintes:** avaliar métricas separadas por sexo, não
só a acurácia global; considerar reponderação de classe; nunca reportar um único
número de desempenho.

## 2. Colesterol ausente codificado como zero

172 registros (18,7%) têm `colesterol_mgdl = 0` — um valor fisiologicamente
impossível. É ausência de medição gravada como zero. Distribuição por base:
switzerland 123, va 49 (nenhum em cleveland ou hungarian).

**Risco:** tratado como número real, arrasta a média para baixo, inverte o sinal
do coeficiente e faz o modelo aprender "colesterol baixo prediz doença".

**Decisão de projeto:** o zero foi **preservado** no CSV. Corrigir na coleta
esconderia o problema; o dado bruto fiel mais esta documentação é o que permite
tratar o caso de forma consciente na fase de modelagem.

**Mitigação:** converter 0 para nulo antes de treinar e imputar de forma
explícita, ou usar modelo que lide com ausência nativamente.

## 3. Pressão de repouso ausente codificada como zero

O mesmo padrão de sentinela em zero aparece em `pressao_repouso_mmhg`: 1
registro (0,11% de 920), vindo exclusivamente da base `va`. Uma pressão
arterial sistólica de 0 mmHg é fisiologicamente impossível — é ausência de
medição, não um valor real, exatamente como o caso do colesterol acima. Este
achado não constava na lista original do plano da Fase 1 e foi identificado
apenas ao medir a coluna diretamente.

**Risco:** embora a contagem seja pequena (1 registro), o mecanismo é o mesmo
do colesterol: se não tratado, um zero de pressão arterial distorce qualquer
estatística descritiva (mínimo, média) e pode ser interpretado por um modelo
como um valor extremo real, em vez de ausência.

**Mitigação:** aplicar a mesma regra do colesterol — converter `0` para nulo em
`pressao_repouso_mmhg` antes de qualquer análise ou treinamento, e documentar a
regra de limpeza em conjunto com a de `colesterol_mgdl` (mesma causa raiz:
codificação de ausência do dataset original do UCI).

## 4. Viés de seleção e prevalência entre centros

Prevalência de doença por base: cleveland 45,9%, hungarian 36,1%, switzerland
93,5%, va 74,5%.

**Risco:** as quatro bases têm perfis muito diferentes de gravidade — de 36% a
93,5% de prevalência. Concatená-las sem controle faz o modelo aprender a
prevalência da mistura, que não corresponde a nenhuma população real.

**Mitigação:** a coluna `origem_base` foi mantida no CSV exatamente para isso —
permite estratificar a divisão treino/teste por centro e medir generalização
entre centros.

## 5. Faixa etária estreita

Idades de 28 a 77 anos (média 53,5). O plano original da Fase 1 citava 29–77;
a medição direta mostra que o mínimo real é 28, e é esse o valor que consta
aqui e no dicionário de dados.

**Risco:** nenhuma validade em população pediátrica ou muito idosa. Um modelo
aplicado fora dessa faixa extrapola sem base.

**Mitigação:** declarar a faixa de validade como restrição de uso do modelo.

## 6. Ausência de dados desigual entre colunas

Percentual de nulos por coluna: `n_vasos_obstruidos` 66,4%, `talassemia` 52,8%,
`inclinacao_st` 33,6%, `glicemia_jejum_alta` 9,8%, `depressao_st_oldpeak` 6,7%,
`pressao_repouso_mmhg` 6,4%, `fc_maxima_bpm` 6,0%, `angina_exercicio` 6,0%,
`colesterol_mgdl` 3,3%, `ecg_repouso` 0,2%; as demais colunas (`paciente_id`,
`origem_base`, `idade`, `sexo`, `tipo_dor_toracica`, `num_diagnostico`,
`doenca_cardiaca`) têm 0% de nulos.

**Risco:** as colunas mais ausentes são justamente as de exame invasivo
(`n_vasos_obstruidos`, `talassemia`), que só são realizadas em quem já tem
suspeita alta. A ausência não é aleatória — ela própria carrega informação
sobre a suspeita clínica, e imputar como se fosse aleatória vaza rótulo.

**Mitigação:** tratar a ausência como categoria própria e nunca imputar essas
colunas com a média.

## 7. Viés de domínio nas imagens

As 928 imagens de origem (233 arritmia/HB, 239 infarto/MI, 284 normal, 172
histórico de infarto/PMI) vêm de **um único centro** (Ch. Pervaiz Elahi
Institute of Cardiology, Multan, Paquistão) e de **um único aparelho** (EDAN
SERIES-3).

**Risco:** a CNN aprende a assinatura do papel, da grade e do aparelho, não a
morfologia do traçado. Desempenho alto no teste interno e colapso em ECG de
outro equipamento.

**Mitigação:** aumento de dados que ataque a assinatura do aparelho (variação de
contraste, ruído, leve rotação); validação externa em ECG de outra fonte antes
de qualquer conclusão.

## 8. Duplicação de imagens no dataset de origem (mitigado na coleta)

O dataset Mendeley de origem contém **imagens byte-idênticas sob nomes de
arquivo diferentes**. Medido via hash SHA-256 do conteúdo
(`content_details.sha256_hash` da própria API do Mendeley), a contagem de
conteúdo **único** por classe no dataset de origem é: arritmia/HB 233 de 233
(sem duplicatas), infarto/MI **30 de 239**, normal/Normal 142 de 284,
histórico de infarto/PMI 86 de 172. Ou seja, a classe `infarto` tem apenas 30
imagens de conteúdo distinto em todo o dataset de origem — as outras 209 são
cópias byte-a-byte sob outro nome.

**Por que isso importa:** duas imagens byte-idênticas em um mesmo conjunto (ou
pior, uma em treino e outra em teste) não são duas observações independentes.
Se caem em lados opostos de uma divisão treino/teste, a imagem "vaza" do treino
para o teste e infla artificialmente toda métrica de desempenho — o modelo não
está generalizando, está memorizando.

**Decisão de projeto:** `preparar_imagens.py` deduplica pelo hash de conteúdo
da fonte **antes** de amostrar, então as 120 imagens finais têm 120 hashes
SHA-256 distintos (verificado e registrado em `MANIFEST.csv`).

**Efeito colateral a declarar:** como a classe `infarto` tem exatamente 30
imagens únicas no dataset de origem inteiro, a amostra de 30 dessa classe não é
uma amostra aleatória de uma população maior — é **o total disponível**. Não há
folga de diversidade nessa classe: qualquer viés de captura (mesmo paciente,
mesmo dia, mesmo ângulo) presente nessas 30 imagens está necessariamente
presente na amostra também, e não pode ser diluído amostrando mais.

**Mitigação:** relatar o desempenho da classe `infarto` com a ressalva de
amostra forçada e não aleatória; para uma fase futura, buscar uma fonte
adicional independente especificamente para ampliar essa classe.

## 9. Desbalanceamento de classe nas imagens (mitigado na coleta)

A origem é desbalanceada: normal 284, infarto 239, arritmia 233, histórico de
infarto 172 (928 no total, antes da deduplicação).

**Decisão de projeto:** a amostra de 120 foi montada **balanceada**, 30 por
classe, em vez de proporcional. É uma mitigação aplicada já na coleta —
combinada com a deduplicação por conteúdo do item 8 acima.

**Efeito colateral a declarar:** a amostra balanceada **não** reflete a
prevalência real das condições. Probabilidade prevista por um modelo treinado
nela precisa de recalibração antes de ser lida como risco clínico.

## 10. Viés linguístico nos textos

Os três textos são em português do Brasil, dois deles produzidos pela mesma
sociedade médica (SBC).

**Risco:** um modelo de NLP treinado só nisso não transfere para outro idioma, e
herda a terminologia e as convenções de uma única escola clínica.

**Mitigação:** ampliar as fontes nas fases de NLP; o terceiro texto (OPAS,
linguagem leiga) já foi incluído para quebrar a uniformidade de registro.

## 11. Viés do dado sintético

A telemetria IoT (6.440 registros, 920 pacientes × 7 dias) foi gerada por
regras que **nós** escrevemos: FC de repouso mais alta, HRV mais baixa e mais
alertas de arritmia em quem tem `doenca_cardiaca = 1`. **Estes dados são
inteiramente simulados, não medições reais de nenhum paciente ou dispositivo.**

**Risco — o mais importante da lista:** qualquer modelo treinado nessa
telemetria vai "descobrir" precisamente a relação que o gerador impôs. Isso
**não valida hipótese clínica nenhuma** e não é evidência de nada. A base serve
para exercitar pipeline, engenharia de atributos e visualização — nunca para
sustentar conclusão sobre o mundo real.

**Mitigação:** rotular a base como sintética em todo lugar onde ela aparece
(feito), e nunca reportar métrica dela ao lado de métrica de dado real sem essa
ressalva.
