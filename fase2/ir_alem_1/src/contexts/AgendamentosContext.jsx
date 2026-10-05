import { createContext, useContext, useEffect, useMemo, useReducer } from 'react'
import { agendamentosReducer } from '../reducers/agendamentosReducer'
import { lerJSON, gravarJSON } from '../services/storage'

const CHAVE = 'cardioia:agendamentos'
const AgendamentosContext = createContext(null)

export function AgendamentosProvider({ children }) {
  // O terceiro argumento do useReducer carrega o estado inicial do localStorage
  const [agendamentos, dispatch] = useReducer(agendamentosReducer, [], () => lerJSON(CHAVE, []))

  // Cada mudança é persistida: as consultas sobrevivem a um recarregamento
  useEffect(() => {
    gravarJSON(CHAVE, agendamentos)
  }, [agendamentos])

  const valor = useMemo(() => ({
    agendamentos,
    agendar: (dados) => dispatch({
      type: 'adicionar',
      agendamento: { ...dados, id: crypto.randomUUID(), criadoEm: new Date().toISOString() },
    }),
    cancelar: (id) => dispatch({ type: 'cancelar', id }),
  }), [agendamentos])

  return <AgendamentosContext.Provider value={valor}>{children}</AgendamentosContext.Provider>
}

export function useAgendamentos() {
  const contexto = useContext(AgendamentosContext)
  if (!contexto) throw new Error('useAgendamentos precisa estar dentro de <AgendamentosProvider>')
  return contexto
}
