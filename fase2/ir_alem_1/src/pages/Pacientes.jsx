import { useDeferredValue, useMemo, useState } from 'react'
import { usePacientes } from '../contexts/PacientesContext'
import { Carregando, Erro, Vazio } from '../components/Estado'
import TabelaPacientes from '../components/TabelaPacientes'
import FichaPaciente from '../components/FichaPaciente'
import styles from './Pacientes.module.css'

function normalizar(texto) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

export default function Pacientes() {
  const { pacientes, porId, carregando, erro, recarregar } = usePacientes()
  const [busca, setBusca] = useState('')
  const [diagnostico, setDiagnostico] = useState('todos')
  const [sexo, setSexo] = useState('todos')
  const [selecionadoId, setSelecionadoId] = useState(null)

  // useDeferredValue mantém a digitação fluida: o filtro roda com prioridade menor
  const buscaAdiada = useDeferredValue(busca)

  const filtrados = useMemo(() => {
    const termo = normalizar(buscaAdiada.trim())
    return pacientes
      .filter((p) => !termo || normalizar(p.nome).includes(termo))
      .filter((p) => diagnostico === 'todos' || p.doencaCardiaca === (diagnostico === 'com'))
      .filter((p) => sexo === 'todos' || p.sexo === sexo)
      .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  }, [pacientes, buscaAdiada, diagnostico, sexo])

  const filtrosAtivos = busca || diagnostico !== 'todos' || sexo !== 'todos'

  function limparFiltros() {
    setBusca('')
    setDiagnostico('todos')
    setSexo('todos')
  }

  return (
    <div className={styles.pagina}>
      <header>
        <h1>Pacientes</h1>
        <p className={styles.sub}>
          Dados clínicos reais da base UCI Heart Disease (Fase 1). Nomes e telefones são fictícios.
        </p>
      </header>

      <div className={styles.filtros} role="search">
        <label className={styles.busca}>
          <span className="visually-hidden">Buscar por nome</span>
          <input
            type="search"
            placeholder="Buscar por nome"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </label>
        <label className={styles.filtro}>
          Diagnóstico
          <select value={diagnostico} onChange={(e) => setDiagnostico(e.target.value)}>
            <option value="todos">Todos</option>
            <option value="com">Com doença cardíaca</option>
            <option value="sem">Sem doença cardíaca</option>
          </select>
        </label>
        <label className={styles.filtro}>
          Sexo
          <select value={sexo} onChange={(e) => setSexo(e.target.value)}>
            <option value="todos">Todos</option>
            <option value="feminino">Feminino</option>
            <option value="masculino">Masculino</option>
          </select>
        </label>
      </div>

      {carregando && <Carregando texto="Carregando pacientes…" />}
      {erro && <Erro mensagem={erro} aoTentarDeNovo={recarregar} />}

      {!carregando && !erro && (
        <>
          <p className={styles.contagem} aria-live="polite">
            {filtrados.length === pacientes.length
              ? `${pacientes.length} pacientes`
              : `${filtrados.length} de ${pacientes.length} pacientes`}
          </p>
          {filtrados.length === 0 ? (
            <Vazio titulo="Nenhum paciente com esses filtros">
              <button type="button" className={styles.limpar} onClick={limparFiltros}>
                Limpar filtros
              </button>
            </Vazio>
          ) : (
            <TabelaPacientes pacientes={filtrados} aoAbrir={setSelecionadoId} />
          )}
          {filtrosAtivos && filtrados.length > 0 && (
            <button type="button" className={styles.limpar} onClick={limparFiltros}>
              Limpar filtros
            </button>
          )}
        </>
      )}

      <FichaPaciente paciente={porId.get(selecionadoId)} aoFechar={() => setSelecionadoId(null)} />
    </div>
  )
}
