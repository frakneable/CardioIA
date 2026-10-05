import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import * as authService from '../services/authService'
import { lerTexto, gravarTexto } from '../services/storage'

const AuthContext = createContext(null)

function tokenSalvoValido() {
  const token = lerTexto(authService.CHAVE_TOKEN)
  return authService.lerToken(token) ? token : null
}

export function AuthProvider({ children }) {
  // Inicialização preguiçosa: lê o localStorage uma única vez, na montagem.
  // Assim quem recarrega a página continua logado enquanto o token for válido.
  const [token, setToken] = useState(tokenSalvoValido)
  const usuario = useMemo(() => authService.lerToken(token), [token])

  // Sincroniza o token com o localStorage sempre que ele muda
  useEffect(() => {
    gravarTexto(authService.CHAVE_TOKEN, token)
  }, [token])

  // Encerra a sessão automaticamente quando o token expira
  useEffect(() => {
    if (!usuario) return
    const restante = usuario.exp * 1000 - Date.now()
    const timer = setTimeout(() => setToken(null), restante)
    return () => clearTimeout(timer)
  }, [usuario])

  const entrar = useCallback(async (email, senha) => {
    const novoToken = await authService.login(email, senha)
    setToken(novoToken)
  }, [])

  const sair = useCallback(() => setToken(null), [])

  const valor = useMemo(
    () => ({ usuario, token, autenticado: Boolean(usuario), entrar, sair }),
    [usuario, token, entrar, sair],
  )
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const contexto = useContext(AuthContext)
  if (!contexto) throw new Error('useAuth precisa estar dentro de <AuthProvider>')
  return contexto
}
