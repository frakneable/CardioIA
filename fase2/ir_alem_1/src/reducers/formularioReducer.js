// Estado do formulário de agendamento: valores dos campos e erros de validação.
// Com useReducer, cada mudança vira uma ação nomeada ("alterar", "erros",
// "limpar"), em vez de vários useState espalhados que precisam mudar juntos.

import { ehFimDeSemana, HORARIOS } from '../utils/datas'
import { horarioOcupado } from './agendamentosReducer'

export const formularioVazio = {
  valores: { pacienteId: '', data: '', horario: '', tipo: '', observacoes: '' },
  erros: {},
}

export function iniciarFormulario(pacienteId = '') {
  return { ...formularioVazio, valores: { ...formularioVazio.valores, pacienteId } }
}

export function formularioReducer(estado, acao) {
  switch (acao.type) {
    case 'alterar': {
      // Ao editar um campo, o erro dele some; trocar a data revalida o horário
      const { [acao.campo]: _removido, ...erros } = estado.erros
      if (acao.campo === 'data') delete erros.horario
      return { valores: { ...estado.valores, [acao.campo]: acao.valor }, erros }
    }
    case 'erros':
      return { ...estado, erros: acao.erros }
    case 'limpar':
      return formularioVazio
    default:
      throw new Error(`Ação desconhecida: ${acao.type}`)
  }
}

export function validar(valores, agendamentos, hoje, agoraHora) {
  const erros = {}
  if (!valores.pacienteId) erros.pacienteId = 'Escolha o paciente.'
  if (!valores.tipo) erros.tipo = 'Escolha o tipo de consulta.'

  if (!valores.data) erros.data = 'Escolha a data.'
  else if (valores.data < hoje) erros.data = 'A data já passou. Escolha hoje ou um dia futuro.'
  else if (ehFimDeSemana(valores.data)) erros.data = 'A clínica não atende aos sábados e domingos.'

  if (!valores.horario) erros.horario = 'Escolha o horário.'
  else if (!HORARIOS.includes(valores.horario)) erros.horario = 'Horário fora do expediente.'
  else if (valores.data === hoje && valores.horario < agoraHora) erros.horario = 'Esse horário de hoje já passou.'
  else if (valores.data && horarioOcupado(agendamentos, valores.data, valores.horario)) {
    erros.horario = 'Já existe uma consulta neste horário. Escolha outro.'
  }

  if (valores.observacoes.length > 300) erros.observacoes = 'Use no máximo 300 caracteres.'
  return erros
}
