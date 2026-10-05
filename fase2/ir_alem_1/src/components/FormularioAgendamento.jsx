import { useMemo, useReducer, useRef, useState } from 'react'
import { useAgendamentos } from '../contexts/AgendamentosContext'
import { usePacientes } from '../contexts/PacientesContext'
import { TIPOS_CONSULTA, horarioOcupado } from '../reducers/agendamentosReducer'
import { formularioReducer, iniciarFormulario, validar } from '../reducers/formularioReducer'
import { HORARIOS, formatarData, hojeISO, horaAtual } from '../utils/datas'
import { esperar } from '../services/api'
import styles from './FormularioAgendamento.module.css'

const ORDEM_CAMPOS = ['pacienteId', 'data', 'horario', 'tipo', 'observacoes']

export default function FormularioAgendamento({ pacienteInicial = '' }) {
  const { pacientes, porId } = usePacientes()
  const { agendamentos, agendar } = useAgendamentos()

  // useReducer: valores e erros do formulário mudam juntos, por ações nomeadas
  const [form, dispatch] = useReducer(formularioReducer, pacienteInicial, iniciarFormulario)
  // useState: estados simples e independentes da tela
  const [enviando, setEnviando] = useState(false)
  const [confirmacao, setConfirmacao] = useState(null)
  const refs = useRef({})

  const { valores, erros } = form
  const hoje = hojeISO()

  const pacientesOrdenados = useMemo(
    () => [...pacientes].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')),
    [pacientes],
  )

  function alterar(campo) {
    return (e) => {
      setConfirmacao(null)
      const valor = campo === 'pacienteId' ? Number(e.target.value) || '' : e.target.value
      dispatch({ type: 'alterar', campo, valor })
    }
  }

  async function aoEnviar(evento) {
    evento.preventDefault()
    const novosErros = validar(valores, agendamentos, hoje, horaAtual())
    if (Object.keys(novosErros).length) {
      dispatch({ type: 'erros', erros: novosErros })
      // Leva o foco ao primeiro campo com problema
      refs.current[ORDEM_CAMPOS.find((c) => novosErros[c])]?.focus()
      return
    }
    setEnviando(true)
    await esperar(400) // simula a gravação no servidor
    agendar(valores)
    setConfirmacao(
      `Consulta agendada: ${porId.get(valores.pacienteId).nome}, ${formatarData(valores.data)} às ${valores.horario}.`,
    )
    dispatch({ type: 'limpar' })
    setEnviando(false)
  }

  const props = (campo) => ({
    id: `campo-${campo}`,
    ref: (el) => { refs.current[campo] = el },
    value: valores[campo],
    onChange: alterar(campo),
    'aria-invalid': Boolean(erros[campo]),
    'aria-describedby': erros[campo] ? `erro-${campo}` : undefined,
  })

  const mensagemErro = (campo) =>
    erros[campo] && <p id={`erro-${campo}`} className={styles.erro}>{erros[campo]}</p>

  return (
    <form className={styles.form} onSubmit={aoEnviar} noValidate>
      <h2 className={styles.titulo}>Agendar consulta</h2>

      <div className={styles.campo}>
        <label htmlFor="campo-pacienteId">Paciente</label>
        <select {...props('pacienteId')}>
          <option value="">Escolha o paciente</option>
          {pacientesOrdenados.map((p) => (
            <option key={p.id} value={p.id}>{p.nome}, {p.idade} anos</option>
          ))}
        </select>
        {mensagemErro('pacienteId')}
      </div>

      <div className={styles.linha}>
        <div className={styles.campo}>
          <label htmlFor="campo-data">Data</label>
          <input type="date" min={hoje} {...props('data')} />
          {mensagemErro('data')}
        </div>
        <div className={styles.campo}>
          <label htmlFor="campo-horario">Horário</label>
          <select {...props('horario')}>
            <option value="">Escolha</option>
            {HORARIOS.map((h) => {
              const ocupado = valores.data && horarioOcupado(agendamentos, valores.data, h)
              return (
                <option key={h} value={h} disabled={ocupado}>
                  {h}{ocupado ? ' (ocupado)' : ''}
                </option>
              )
            })}
          </select>
          {mensagemErro('horario')}
        </div>
      </div>

      <div className={styles.campo}>
        <label htmlFor="campo-tipo">Tipo de consulta</label>
        <select {...props('tipo')}>
          <option value="">Escolha o tipo</option>
          {TIPOS_CONSULTA.map((t) => <option key={t}>{t}</option>)}
        </select>
        {mensagemErro('tipo')}
      </div>

      <div className={styles.campo}>
        <label htmlFor="campo-observacoes">
          Observações <span className={styles.opcional}>(opcional)</span>
        </label>
        <textarea rows={3} maxLength={300} {...props('observacoes')} />
        <p className={styles.contador}>{valores.observacoes.length}/300</p>
        {mensagemErro('observacoes')}
      </div>

      <button type="submit" className={styles.agendar} disabled={enviando}>
        {enviando ? 'Agendando…' : 'Agendar consulta'}
      </button>

      <p className={styles.confirmacao} role="status">{confirmacao}</p>
    </form>
  )
}
