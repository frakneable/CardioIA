import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { usePacientes } from '../contexts/PacientesContext'
import { useAgendamentos } from '../contexts/AgendamentosContext'
import { proximasConsultas } from '../reducers/agendamentosReducer'
import { formatarData, hojeISO, horaAtual } from '../utils/datas'
import TracadoEcg from '../components/TracadoEcg'
import { Carregando, Erro, Vazio } from '../components/Estado'
import styles from './Dashboard.module.css'

function saudacao(hora) {
  if (hora < 12) return 'Bom dia'
  if (hora < 18) return 'Boa tarde'
  return 'Boa noite'
}

const numero = new Intl.NumberFormat('pt-BR')

export default function Dashboard() {
  const { usuario } = useAuth()
  const { pacientes, porId, carregando, erro, recarregar } = usePacientes()
  const { agendamentos } = useAgendamentos()

  const agora = new Date()
  const hoje = hojeISO(agora)

  // useMemo: os indicadores só são recalculados quando os dados mudam
  const indicadores = useMemo(() => {
    const comDoenca = pacientes.filter((p) => p.doencaCardiaca).length
    const proximas = proximasConsultas(agendamentos, hoje, horaAtual())
    const centros = Object.entries(
      pacientes.reduce((acc, p) => {
        acc[p.centro] ??= { total: 0, comDoenca: 0 }
        acc[p.centro].total += 1
        acc[p.centro].comDoenca += p.doencaCardiaca ? 1 : 0
        return acc
      }, {}),
    ).sort((a, b) => b[1].total - a[1].total)
    return {
      total: pacientes.length,
      comDoenca,
      percentual: pacientes.length ? Math.round((comDoenca / pacientes.length) * 100) : 0,
      proximas,
      hojeQtd: proximas.filter((a) => a.data === hoje).length,
      centros,
    }
  }, [pacientes, agendamentos, hoje])

  return (
    <div className={styles.pagina}>
      <header className={styles.cabecalho}>
        <h1>{saudacao(agora.getHours())}, {usuario.nome.split(' ').slice(0, 2).join(' ')}</h1>
        <p className={styles.data}>
          {new Intl.DateTimeFormat('pt-BR', { dateStyle: 'full' }).format(agora)}
        </p>
      </header>

      {carregando && <Carregando texto="Carregando pacientes…" />}
      {erro && <Erro mensagem={erro} aoTentarDeNovo={recarregar} />}

      {!carregando && !erro && (
        <>
          <section className={styles.monitor} aria-label="Indicadores">
            <div className={styles.tracado}>
              <TracadoEcg batimentos={6} rotulo="Traçado de ECG decorativo" />
            </div>
            <dl className={styles.leituras}>
              <div className={styles.leitura}>
                <dt>Pacientes cadastrados</dt>
                <dd>{numero.format(indicadores.total)}</dd>
              </div>
              <div className={styles.leitura}>
                <dt>Com doença cardíaca</dt>
                <dd>
                  {numero.format(indicadores.comDoenca)}
                  <span className={styles.unidade}>{indicadores.percentual}%</span>
                </dd>
              </div>
              <div className={styles.leitura}>
                <dt>Consultas agendadas</dt>
                <dd>
                  {numero.format(indicadores.proximas.length)}
                  <span className={styles.unidade}>{indicadores.hojeQtd} hoje</span>
                </dd>
              </div>
            </dl>
          </section>

          <div className={styles.colunas}>
            <section className={styles.bloco}>
              <div className={styles.blocoTopo}>
                <h2>Próximas consultas</h2>
                <Link to="/agendamentos">Agendar consulta</Link>
              </div>
              {indicadores.proximas.length === 0 ? (
                <Vazio titulo="Nenhuma consulta agendada">
                  <p>As consultas que você agendar aparecem aqui, da mais próxima para a mais distante.</p>
                </Vazio>
              ) : (
                <ol className={styles.agenda}>
                  {indicadores.proximas.slice(0, 5).map((a) => (
                    <li key={a.id}>
                      <span className={styles.quando}>
                        <span className={styles.hora}>{a.horario}</span>
                        {a.data === hoje ? 'Hoje' : formatarData(a.data)}
                      </span>
                      <span>
                        <span className={styles.paciente}>{porId.get(a.pacienteId)?.nome ?? 'Paciente removido'}</span>
                        <span className={styles.tipo}>{a.tipo}</span>
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </section>

            <section className={styles.bloco}>
              <div className={styles.blocoTopo}>
                <h2>Pacientes por centro de origem</h2>
              </div>
              <ul className={styles.centros}>
                {indicadores.centros.map(([centro, { total, comDoenca }]) => (
                  <li key={centro}>
                    <div className={styles.centroLinha}>
                      <span>{centro}</span>
                      <span className={styles.centroNum}>{total}</span>
                    </div>
                    <div
                      className={styles.barra}
                      role="img"
                      aria-label={`${comDoenca} de ${total} com doença cardíaca`}
                    >
                      <span className={styles.barraDoenca} style={{ width: `${(comDoenca / indicadores.total) * 100}%` }} />
                      <span className={styles.barraSem} style={{ width: `${((total - comDoenca) / indicadores.total) * 100}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
              <p className={styles.legenda}>
                <span className={styles.item}><span className={styles.chaveDoenca} /> com doença cardíaca</span>
                <span className={styles.item}><span className={styles.chaveSem} /> sem doença cardíaca</span>
              </p>
            </section>
          </div>
        </>
      )}
    </div>
  )
}
