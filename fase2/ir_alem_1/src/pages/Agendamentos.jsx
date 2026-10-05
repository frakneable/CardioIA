import { useSearchParams } from 'react-router-dom'
import { usePacientes } from '../contexts/PacientesContext'
import FormularioAgendamento from '../components/FormularioAgendamento'
import ListaAgendamentos from '../components/ListaAgendamentos'
import { Carregando, Erro } from '../components/Estado'
import styles from './Agendamentos.module.css'

export default function Agendamentos() {
  const { carregando, erro, recarregar, porId } = usePacientes()
  // Vindo da ficha do paciente, o formulário já abre com ele selecionado
  const [params] = useSearchParams()
  const pacienteInicial = porId.has(Number(params.get('paciente'))) ? Number(params.get('paciente')) : ''

  return (
    <div className={styles.pagina}>
      <header>
        <h1>Consultas</h1>
        <p className={styles.sub}>Atendimento de segunda a sexta, das 8h às 18h, em horários de 30 minutos.</p>
      </header>

      {carregando && <Carregando texto="Carregando pacientes…" />}
      {erro && <Erro mensagem={erro} aoTentarDeNovo={recarregar} />}

      {!carregando && !erro && (
        <div className={styles.colunas}>
          {/* key: trocar de paciente pela URL recria o formulário com o novo valor inicial */}
          <FormularioAgendamento key={pacienteInicial} pacienteInicial={pacienteInicial} />
          <ListaAgendamentos />
        </div>
      )}
    </div>
  )
}
