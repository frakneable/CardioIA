import styles from './Marca.module.css'

export default function Marca({ escura = false }) {
  return (
    <span className={`${styles.marca} ${escura ? styles.escura : ''}`}>
      <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
        <path
          d="M2 18h7l2-5 3 11 3-16 3 10h10"
          fill="none"
          stroke="#e5484d"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      CardioIA
    </span>
  )
}
