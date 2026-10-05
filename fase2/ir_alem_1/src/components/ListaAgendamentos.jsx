import { useMemo, useState } from 'react'
import { useAgendamentos } from '../contexts/AgendamentosContext'
import { usePacientes } from '../contexts/PacientesContext'
import { formatarData, hojeISO, horaAtual } from '../utils/datas'
import { Vazio } from './Estado'
import styles from './ListaAgendamentos.module.css'

const ABAS = [
  { id: 'proximas', rotulo: 'Próximas' },
  { id: 'anteriores', rotulo: 'Anteriores' },
  { id: 'canceladas', rotulo: 'Canceladas' },
]

export default function ListaAgendamentos() {
  const { agendamentos, cancelar } = useAgendamentos()
  const { porId } = usePacientes()
  const [aba, setAba] = useState('proximas')
  const [confirmandoId, setConfirmandoId] = useState(null)

  const grupos = useMemo(() => {
    const agora = `${hojeISO()} ${horaAtual()}`
    const quando = (a) => `${a.data} ${a.horario}`
    const ativas = agendamentos.filter((a) => a.status === 'agendada')
    return {
      proximas: ativas.filter((a) => quando(a) >= agora).sort((a, b) => quando(a).localeCompare(quando(b))),
      anteriores: ativas.filter((a) => quando(a) < agora).sort((a, b) => quando(b).localeCompare(quando(a))),
      canceladas: agendamentos.filter((a) => a.status === 'cancelada'),
    }
  }, [agendamentos])

  const lista = grupos[aba]

  return (
    <section className={styles.lista} aria-labelledby="lista-titulo">
      <h2 id="lista-titulo" className={styles.titulo}>Agenda</h2>

      <div className={styles.abas} role="tablist">
        {ABAS.map(({ id, rotulo }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={aba === id}
            className={styles.aba}
            onClick={() => setAba(id)}
          >
            {rotulo} <span className={styles.qtd}>{grupos[id].length}</span>
          </button>
        ))}
      </div>

      {lista.length === 0 ? (
        <Vazio titulo={aba === 'proximas' ? 'Nenhuma consulta agendada' : 'Nada por aqui'}>
          {aba === 'proximas' && <p>Use o formulário para agendar a primeira consulta.</p>}
        </Vazio>
      ) : (
        <ul className={styles.itens}>
          {lista.map((a) => (
            <li key={a.id} className={styles.item}>
              <div className={styles.quando}>
                <span className={styles.hora}>{a.horario}</span>
                <span>{formatarData(a.data)}</span>
              </div>
              <div className={styles.info}>
                <p className={styles.paciente}>{porId.get(a.pacienteId)?.nome ?? 'Paciente removido'}</p>
                <p className={styles.tipo}>{a.tipo}</p>
                {a.observacoes && <p className={styles.obs}>{a.observacoes}</p>}
              </div>
              {aba === 'proximas' && (
                <div className={styles.acoes}>
                  {confirmandoId === a.id ? (
                    <>
                      <button type="button" className={styles.confirmar} onClick={() => cancelar(a.id)}>
                        Confirmar cancelamento
                      </button>
                      <button type="button" className={styles.manter} onClick={() => setConfirmandoId(null)}>
                        Manter
                      </button>
                    </>
                  ) : (
                    <button type="button" className={styles.cancelar} onClick={() => setConfirmandoId(a.id)}>
                      Cancelar consulta
                    </button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
