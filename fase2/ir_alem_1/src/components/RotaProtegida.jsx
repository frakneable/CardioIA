import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

// Sem usuário logado, redireciona para o login guardando a página pedida,
// para voltar a ela depois de entrar.
export default function RotaProtegida({ children }) {
  const { autenticado } = useAuth()
  const location = useLocation()

  if (!autenticado) {
    return <Navigate to="/login" replace state={{ de: location.pathname + location.search }} />
  }
  return children
}
