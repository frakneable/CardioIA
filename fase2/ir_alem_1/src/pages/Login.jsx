import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { CREDENCIAIS_DEMO } from '../services/authService'
import Marca from '../components/Marca'
import TracadoEcg from '../components/TracadoEcg'
import styles from './Login.module.css'

export default function Login() {
  const { autenticado, entrar } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const destino = location.state?.de ?? '/dashboard'

  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState(null)
  const [enviando, setEnviando] = useState(false)

  // Quem já está logado não precisa ver o login
  if (autenticado) return <Navigate to={destino} replace />

  async function aoEnviar(evento) {
    evento.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      await entrar(email, senha)
      navigate(destino, { replace: true })
    } catch (e) {
      setErro(e.message)
      setEnviando(false)
    }
  }

  function usarConta(conta) {
    setEmail(conta.email)
    setSenha(conta.senha)
    setErro(null)
  }

  return (
    <div className={styles.pagina}>
      <section className={styles.monitor} aria-hidden="true">
        <Marca />
        <div className={styles.papel}>
          <TracadoEcg batimentos={4} />
        </div>
        <p className={styles.legenda}>
          Pacientes, consultas e indicadores da cardiologia em um só lugar.
        </p>
      </section>

      <section className={styles.lado}>
        <form className={styles.form} onSubmit={aoEnviar} noValidate>
          <h1 className={styles.titulo}>Entrar no portal</h1>
          <p className={styles.sub}>Acesso da equipe de cardiologia.</p>

          <label className={styles.campo}>
            E-mail
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className={styles.campo}>
            Senha
            <input
              type="password"
              autoComplete="current-password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              required
            />
          </label>

          {erro && <p className={styles.erro} role="alert">{erro}</p>}

          <button type="submit" className={styles.entrar} disabled={enviando || !email || !senha}>
            {enviando ? 'Entrando…' : 'Entrar'}
          </button>

          <div className={styles.demo}>
            <p className={styles.demoTitulo}>Contas de demonstração</p>
            <p className={styles.demoTexto}>
              Não há servidor: o login gera um token JWT simulado no navegador.
            </p>
            <ul>
              {CREDENCIAIS_DEMO.map((conta) => (
                <li key={conta.email}>
                  <button type="button" className={styles.conta} onClick={() => usarConta(conta)}>
                    <span>{conta.papel}</span>
                    <span className={styles.email}>{conta.email} / {conta.senha}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </form>
      </section>
    </div>
  )
}
