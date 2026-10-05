import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { buscarPacientes } from '../services/api'

const PacientesContext = createContext(null)

// Busca a lista uma única vez para todo o portal: dashboard, listagem e
// formulário de agendamento leem do mesmo lugar, sem repetir a requisição.
export function PacientesProvider({ children }) {
  const [pacientes, setPacientes] = useState([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState(null)
  const [tentativa, setTentativa] = useState(0)

  useEffect(() => {
    // AbortController cancela a requisição se o componente desmontar no meio
    const controle = new AbortController()
    setCarregando(true)
    setErro(null)
    buscarPacientes({ signal: controle.signal })
      .then((dados) => setPacientes(dados))
      .catch((e) => {
        if (e.name !== 'AbortError') setErro(e.message)
      })
      .finally(() => {
        if (!controle.signal.aborted) setCarregando(false)
      })
    return () => controle.abort()
  }, [tentativa])

  const recarregar = useCallback(() => setTentativa((t) => t + 1), [])
  const porId = useMemo(() => new Map(pacientes.map((p) => [p.id, p])), [pacientes])

  const valor = useMemo(
    () => ({ pacientes, porId, carregando, erro, recarregar }),
    [pacientes, porId, carregando, erro, recarregar],
  )
  return <PacientesContext.Provider value={valor}>{children}</PacientesContext.Provider>
}

export function usePacientes() {
  const contexto = useContext(PacientesContext)
  if (!contexto) throw new Error('usePacientes precisa estar dentro de <PacientesProvider>')
  return contexto
}
