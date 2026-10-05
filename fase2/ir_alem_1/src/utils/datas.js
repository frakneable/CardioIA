// Datas no formato AAAA-MM-DD sempre no fuso LOCAL. toISOString() usa UTC e,
// no Brasil, depois das 21h já devolveria o dia seguinte.
export function hojeISO(agora = new Date()) {
  const a = agora.getFullYear()
  const m = String(agora.getMonth() + 1).padStart(2, '0')
  const d = String(agora.getDate()).padStart(2, '0')
  return `${a}-${m}-${d}`
}

export function horaAtual(agora = new Date()) {
  return `${String(agora.getHours()).padStart(2, '0')}:${String(agora.getMinutes()).padStart(2, '0')}`
}

const formatoData = new Intl.DateTimeFormat('pt-BR', { weekday: 'short', day: '2-digit', month: 'short' })

export function formatarData(iso) {
  const [a, m, d] = iso.split('-').map(Number)
  return formatoData.format(new Date(a, m - 1, d)).replace('.', '')
}

export function ehFimDeSemana(iso) {
  const [a, m, d] = iso.split('-').map(Number)
  const dia = new Date(a, m - 1, d).getDay()
  return dia === 0 || dia === 6
}

// Horários de atendimento: 08:00 às 17:30, a cada 30 minutos
export const HORARIOS = Array.from({ length: 20 }, (_, i) => {
  const minutos = 8 * 60 + i * 30
  return `${String(Math.floor(minutos / 60)).padStart(2, '0')}:${String(minutos % 60).padStart(2, '0')}`
})
