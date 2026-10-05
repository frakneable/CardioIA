import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useAgendamentos } from '../contexts/AgendamentosContext'
import { formatarData } from '../utils/datas'
import styles from './FichaPaciente.module.css'

function valor(v, unidade) {
  return v === null || v === undefined ? 'Não medido' : `${v} ${unidade}`.trim()
}

// Ficha em <dialog> nativo: o navegador cuida do foco, da tecla Esc e do fundo inerte.
export default function FichaPaciente({ paciente, aoFechar }) {
  const dialogo = useRef(null)
  const { agendamentos } = useAgendamentos()

  useEffect(() => {
    const el = dialogo.current
    if (paciente && !el.open) el.showModal()
    if (!paciente && el.open) el.close()
  }, [paciente])

  const consultas = paciente
    ? agendamentos
        .filter((a) => a.pacienteId === paciente.id)
        .sort((a, b) => `${b.data}${b.horario}`.localeCompare(`${a.data}${a.horario}`))
    : []

  return (
    <dialog
      ref={dialogo}
      className={styles.dialogo}
      onClose={aoFechar}
      onClick={(e) => e.target === dialogo.current && dialogo.current.close()}
      aria-labelledby="ficha-titulo"
    >
      {paciente && (
        <div className={styles.corpo}>
          <header className={styles.topo}>
            <div>
              <h2 id="ficha-titulo">{paciente.nome}</h2>
              <p className={styles.meta}>
                {paciente.idade} anos, {paciente.sexo}, {paciente.centro}
              </p>
            </div>
            <button type="button" className={styles.fechar} onClick={() => dialogo.current.close()}>
              Fechar
            </button>
          </header>

          <p className={paciente.doencaCardiaca ? styles.com : styles.sem}>
            {paciente.doencaCardiaca
              ? 'Doença cardíaca confirmada por angiografia'
              : 'Sem doença cardíaca na angiografia'}
          </p>

          <dl className={styles.dados}>
            <div><dt>Pressão sistólica em repouso</dt><dd>{valor(paciente.pressaoSistolica, 'mmHg')}</dd></div>
            <div><dt>Colesterol</dt><dd>{valor(paciente.colesterol, 'mg/dL')}</dd></div>
            <div><dt>FC máxima no esforço</dt><dd>{valor(paciente.fcMaxima, 'bpm')}</dd></div>
            <div><dt>Dor torácica</dt><dd>{paciente.tipoDor}</dd></div>
            <div>
              <dt>Angina no exercício</dt>
              <dd>{paciente.anginaExercicio === null ? 'Não avaliada' : paciente.anginaExercicio ? 'Sim' : 'Não'}</dd>
            </div>
            <div><dt>Telefone</dt><dd>{paciente.telefone}</dd></div>
          </dl>

          <section>
            <h3 className={styles.subtitulo}>Consultas</h3>
            {consultas.length === 0 ? (
              <p className={styles.nenhuma}>Nenhuma consulta registrada.</p>
            ) : (
              <ul className={styles.consultas}>
                {consultas.map((c) => (
                  <li key={c.id} className={c.status === 'cancelada' ? styles.cancelada : undefined}>
                    {formatarData(c.data)}, {c.horario}: {c.tipo}
                    {c.status === 'cancelada' && ' (cancelada)'}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <footer className={styles.rodape}>
            <span className={styles.origem}>Registro de origem: {paciente.registroOrigem}</span>
            <Link to={`/agendamentos?paciente=${paciente.id}`} className={styles.agendar}>
              Agendar consulta
            </Link>
          </footer>
        </div>
      )}
    </dialog>
  )
}
