import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { PAPEIS_DADOS_CLINICOS, podeAcessar } from '../services/authService'
import Marca from './Marca'
import styles from './Layout.module.css'

const LINKS = [
  { para: '/dashboard', rotulo: 'Painel' },
  { para: '/pacientes', rotulo: 'Pacientes', papeis: PAPEIS_DADOS_CLINICOS },
  { para: '/agendamentos', rotulo: 'Consultas' },
]

export default function Layout() {
  const { usuario, sair } = useAuth()
  const [menuAberto, setMenuAberto] = useState(false)
  const location = useLocation()

  // No celular, o menu fecha sozinho ao trocar de página
  useEffect(() => {
    setMenuAberto(false)
  }, [location.pathname])

  return (
    <div className={styles.app}>
      <header className={styles.lateral}>
        <div className={styles.topo}>
          <Link to="/dashboard" className={styles.marcaLink} aria-label="CardioIA: ir para o painel">
            <Marca />
          </Link>
          <button
            type="button"
            className={styles.botaoMenu}
            aria-expanded={menuAberto}
            aria-controls="navegacao"
            onClick={() => setMenuAberto((aberto) => !aberto)}
          >
            {menuAberto ? 'Fechar' : 'Menu'}
          </button>
        </div>

        <div id="navegacao" className={`${styles.gaveta} ${menuAberto ? styles.aberta : ''}`}>
          <nav aria-label="Principal">
            <ul className={styles.links}>
              {LINKS.filter(({ papeis }) => podeAcessar(usuario, papeis)).map(({ para, rotulo }) => (
                <li key={para}>
                  <NavLink
                    to={para}
                    className={({ isActive }) => `${styles.link} ${isActive ? styles.ativo : ''}`}
                  >
                    {rotulo}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <div className={styles.usuario}>
            <p className={styles.nome}>{usuario.nome}</p>
            <p className={styles.papel}>{usuario.papel}</p>
            <button type="button" className={styles.sair} onClick={sair}>
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className={styles.conteudo}>
        <Outlet />
      </main>
    </div>
  )
}
