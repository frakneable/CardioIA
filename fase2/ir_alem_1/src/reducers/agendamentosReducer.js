// Estado global das consultas, usado pelo AgendamentosContext via useReducer.
// Funções puras: recebem o estado e uma ação, devolvem um estado novo.

export const TIPOS_CONSULTA = [
  'Primeira consulta',
  'Retorno',
  'Eletrocardiograma',
  'Ecocardiograma',
  'Teste ergométrico',
]

export function agendamentosReducer(estado, acao) {
  switch (acao.type) {
    case 'adicionar':
      return [...estado, { ...acao.agendamento, status: 'agendada' }]
    case 'cancelar':
      return estado.map((a) => (a.id === acao.id ? { ...a, status: 'cancelada' } : a))
    default:
      throw new Error(`Ação desconhecida: ${acao.type}`)
  }
}

export function horarioOcupado(agendamentos, data, horario) {
  return agendamentos.some((a) => a.status === 'agendada' && a.data === data && a.horario === horario)
}

// Consultas ativas a partir de agora, da mais próxima para a mais distante
export function proximasConsultas(agendamentos, hoje, agoraHora) {
  return agendamentos
    .filter((a) => a.status === 'agendada')
    .filter((a) => a.data > hoje || (a.data === hoje && a.horario >= agoraHora))
    .sort((a, b) => `${a.data} ${a.horario}`.localeCompare(`${b.data} ${b.horario}`))
}
