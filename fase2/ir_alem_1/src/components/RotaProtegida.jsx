import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { podeAcessar } from '../services/authService'

// `papeis` é opcional: sem ele, basta estar logado. Com ele, quem está logado
// com outro perfil volta para o painel.
export default function RotaProtegida({ papeis, children }) {
  const { autenticado, usuario } = useAuth()
  const location = useLocation()

  if (!autenticado) {
    return <Navigate to="/login" replace state={{ de: location.pathname + location.search }} />
  }
  if (!podeAcessar(usuario, papeis)) {
    return <Navigate to="/dashboard" replace />
  }
  return children
}
