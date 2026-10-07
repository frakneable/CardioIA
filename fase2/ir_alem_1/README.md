# CardioIA Portal — Ir Além 1

Interface web do CardioIA em **React + Vite**. Ela simula a rotina de um portal
de cardiologia: login da equipe, lista de pacientes, agendamento de consultas e
um painel com indicadores. Não há back-end: os dados vêm de um JSON local e o
login gera um JWT simulado no navegador.

## 👨‍🎓 Integrantes
- Victor Copque dos Reis — RM566821
- Victor Hugo Ferreira Rolim — RM568006

## 🎬 Vídeo de demonstração

**YouTube (não listado):** https://www.youtube.com/watch?v=QpTnxGWJkwE

## ⚙️ Instalação e execução

Requer **Node.js 20 ou superior**.

```bash
cd fase2/ir_alem_1
npm install
npm run dev        # abre em http://localhost:5173
```

| Comando | O que faz |
|---|---|
| `npm run dev` | Servidor de desenvolvimento com recarga automática |
| `npm run build` | Gera a versão de produção em `dist/` |
| `npm run preview` | Serve a versão de produção localmente |
| `npm test` | Roda os testes (Vitest) |

**Contas de demonstração** (também listadas na tela de login, com botão para
preencher):

| Perfil | E-mail | Senha |
|---|---|---|
| Cardiologista | `medico@cardioia.com` | `cardio123` |
| Recepção | `recepcao@cardioia.com` | `cardio123` |

## 🗂️ Estrutura

```
src/
├── contexts/      # AuthContext, PacientesContext, AgendamentosContext
├── components/    # Layout, RotaProtegida, TabelaPacientes, FichaPaciente,
│                  # FormularioAgendamento, ListaAgendamentos, TracadoEcg, Estado
├── services/      # authService (JWT simulado), api (busca de pacientes), storage
├── pages/         # Login, Dashboard, Pacientes, Agendamentos, NaoEncontrada
├── reducers/      # agendamentosReducer e formularioReducer (funções puras, testadas)
├── utils/         # datas no fuso local e horários de atendimento
└── styles/        # tokens globais (cores, tipografia)
public/data/       # pacientes.json, a "API" simulada
scripts/           # gerar_pacientes.py: cria o JSON a partir da base da Fase 1
```

## ✅ Como cada requisito foi atendido

### Autenticação simulada com Context API e JWT fake no localStorage
- `services/authService.js` confere as credenciais de demonstração e monta um
  token no formato JWT real (`cabeçalho.payload.assinatura`, em base64url),
  com nome, perfil e **expiração de 8 horas**. A assinatura é um texto fixo, e
  o código deixa claro que isso não oferece segurança.
- `contexts/AuthContext.jsx` guarda o token com `useState` e o sincroniza com o
  `localStorage` via `useEffect`. Quem recarrega a página continua logado
  enquanto o token for válido. Um segundo `useEffect` encerra a sessão
  sozinho quando o token expira.

### Proteção de rotas com AuthContext
- `components/RotaProtegida.jsx` lê `useAuth()`. Sem usuário, redireciona para
  `/login` **guardando a página pedida**: depois do login, o usuário volta
  para onde queria ir.
- **Controle por perfil:** a tabela de pacientes, com dados clínicos, é só do
  **Cardiologista**. Para a **Recepção** o link some do menu, e quem digita
  `/pacientes` volta para o painel. A recepção continua agendando consultas,
  escolhendo o paciente só pelo nome. A regra está em `PAPEIS_DADOS_CLINICOS`
  (`services/authService.js`), e a `RotaProtegida` aceita a lista de perfis.
- Os dados de pacientes e consultas só são carregados **depois** da
  autenticação, porque os providers ficam dentro da rota protegida
  (`App.jsx`).

### Listagem de pacientes com base simulada
- `public/data/pacientes.json` tem **120 pacientes** com dados clínicos
  **reais** da base UCI Heart Disease usada na Fase 1 (idade, sexo, pressão,
  colesterol, FC máxima, tipo de dor, diagnóstico). **Nomes e telefones são
  fictícios**, gerados por `scripts/gerar_pacientes.py`. Medidas que a base
  original marca como "não medido" aparecem assim na tela, e não como zero.
- `services/api.js` busca o JSON com `fetch`, como faria com um endpoint real,
  com latência simulada. `contexts/PacientesContext.jsx` faz a busca uma única
  vez em um `useEffect`, com `AbortController` e estados de **carregando**,
  **erro (com "Tentar de novo")** e **vazio**.
- Na página de pacientes há busca por nome (ignora acentos), filtros por
  diagnóstico e sexo, e uma ficha detalhada em `<dialog>` com as consultas do
  paciente e um atalho para agendar.

### Formulário de agendamento com useState e useReducer
- **`useReducer`** (`reducers/formularioReducer.js`): valores dos campos e
  erros de validação mudam juntos por ações nomeadas (`alterar`, `erros`,
  `limpar`). Editar um campo apaga só o erro dele.
- **`useState`**: estado de envio e mensagem de confirmação.
- Validações: campos obrigatórios, data passada, fim de semana, horário que
  já passou hoje e **horário já ocupado**. Horários ocupados aparecem
  desabilitados na lista. Ao errar, o foco vai para o primeiro campo com
  problema.
- As consultas ficam em `contexts/AgendamentosContext.jsx`, outro
  `useReducer` (`adicionar`, `cancelar`), persistido no `localStorage`.

### Dashboard com contagem de pacientes e consultas
- Painel no estilo monitor cardíaco, sobre papel milimetrado de ECG:
  pacientes cadastrados, quantos têm doença cardíaca (e o percentual) e
  consultas agendadas (e quantas são hoje).
- Próximas cinco consultas e distribuição dos pacientes por centro de origem.
- Os indicadores são calculados com `useMemo` a partir dos mesmos contextos
  usados nas outras páginas, então agendar ou cancelar reflete no painel na hora.

### Estilização com CSS Modules e responsividade
- Cada componente e página tem seu `.module.css`. Os tokens de cor e tipografia
  ficam em `styles/global.css`.
- **Responsivo**: no celular, o menu lateral vira barra superior com gaveta, a
  tabela de pacientes vira lista com rótulos e as colunas empilham. Testado em
  1366 px e 390 px de largura, sem rolagem horizontal.
- **Acessibilidade**: foco visível no teclado, rótulos em todos os campos,
  mensagens de erro ligadas aos campos (`aria-describedby`), `role="status"`
  e `role="alert"` para os avisos e respeito a `prefers-reduced-motion`.

### Hooks utilizados

| Hook | Onde |
|---|---|
| `useState` | Login, filtros, formulário, abas, menu mobile, sessão |
| `useEffect` | Busca de pacientes, persistência no localStorage, expiração da sessão, fechar menu ao navegar, abrir/fechar a ficha |
| `useContext` | `useAuth`, `usePacientes`, `useAgendamentos` |
| `useReducer` | Formulário de agendamento e lista de consultas |
| `useMemo` / `useCallback` | Indicadores, filtros, valores dos contextos |
| `useRef` | Foco no primeiro campo com erro e controle do `<dialog>` |
| `useDeferredValue` | Busca de pacientes sem travar a digitação |

## 🎨 Decisões de design

- **Tema:** o papel milimetrado do eletrocardiograma e o monitor de beira de
  leito. O traçado vermelho é o **único** elemento vermelho da interface. Ao
  carregar, ele é "escrito" da esquerda para a direita. Depois, uma faixa vazia
  varre a tela sem parar, como num monitor real, e cada passada traz
  batimentos novos: o ritmo continua sinusal normal, com pequenas variações no
  intervalo entre batimentos (±7%), na altura das ondas e uma oscilação lenta
  da linha de base, como a da respiração. Quem ativa "reduzir movimento" no
  sistema vê o traçado parado.
- **Tipografia:** *Atkinson Hyperlegible*, criada pelo Braille Institute para
  máxima legibilidade. O zero cortado evita confundir 0 com O, o que importa
  em dados de saúde. Os números do painel usam *Barlow Condensed*, que lembra
  os dígitos de um monitor.
- **Cores:** azul-ardósia para texto e navegação e verde-azulado de jaleco
  para ações.

## 🧪 Testes

```bash
npm test
```

16 testes com Vitest cobrem os reducers (adicionar, cancelar, próximas
consultas, validações de data, horário e conflito) e o JWT simulado (formato,
acentos, expiração de 8 horas, tokens malformados, login).

## Observação sobre o repositório

O enunciado pede um repositório próprio chamado
`nome-do-grupo-cardioia-portal`. Por ora o portal está em
`fase2/ir_alem_1/` do repositório do projeto. A aplicação é autocontida e pode
ser movida para um repositório separado sem alterações. Só o script
`scripts/gerar_pacientes.py` depende da base da Fase 1, e o JSON que ele gera
já está em `public/data/`.
