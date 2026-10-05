import styles from './Estado.module.css'

export function Carregando({ texto = 'Carregando…' }) {
  return (
    <div className={styles.caixa} role="status">
      <span className={styles.pulso} aria-hidden="true" />
      {texto}
    </div>
  )
}

export function Erro({ mensagem, aoTentarDeNovo }) {
  return (
    <div className={`${styles.caixa} ${styles.erro}`} role="alert">
      <p>{mensagem}</p>
      {aoTentarDeNovo && (
        <button type="button" className={styles.botao} onClick={aoTentarDeNovo}>
          Tentar de novo
        </button>
      )}
    </div>
  )
}

export function Vazio({ titulo, children }) {
  return (
    <div className={`${styles.caixa} ${styles.vazio}`}>
      <p className={styles.titulo}>{titulo}</p>
      {children}
    </div>
  )
}
