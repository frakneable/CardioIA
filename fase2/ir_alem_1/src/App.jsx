import { Navigate, Route, Routes } from 'react-router-dom'
import RotaProtegida from './components/RotaProtegida'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Pacientes from './pages/Pacientes'
import Agendamentos from './pages/Agendamentos'
import NaoEncontrada from './pages/NaoEncontrada'
import { PacientesProvider } from './contexts/PacientesContext'
import { AgendamentosProvider } from './contexts/AgendamentosContext'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Tudo abaixo exige login. Os dados só são buscados depois da autenticação. */}
      <Route
        element={
          <RotaProtegida>
            <PacientesProvider>
              <AgendamentosProvider>
                <Layout />
              </AgendamentosProvider>
            </PacientesProvider>
          </RotaProtegida>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/pacientes" element={<Pacientes />} />
        <Route path="/agendamentos" element={<Agendamentos />} />
        <Route path="*" element={<NaoEncontrada />} />
      </Route>
    </Routes>
  )
}
