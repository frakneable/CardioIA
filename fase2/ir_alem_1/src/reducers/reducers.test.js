import { describe, expect, it } from 'vitest'
import { agendamentosReducer, horarioOcupado, proximasConsultas } from './agendamentosReducer'
import { formularioReducer, formularioVazio, iniciarFormulario, validar } from './formularioReducer'

const consulta = (id, data, horario, status = 'agendada') => ({ id, pacienteId: 1, data, horario, tipo: 'Retorno', status })

describe('agendamentosReducer', () => {
  it('adiciona com status "agendada" sem alterar o estado anterior', () => {
    const antes = []
    const depois = agendamentosReducer(antes, { type: 'adicionar', agendamento: { id: 'a', data: '2030-01-07' } })
    expect(depois).toEqual([{ id: 'a', data: '2030-01-07', status: 'agendada' }])
    expect(antes).toEqual([])
  })

  it('cancela só a consulta indicada', () => {
    const estado = [consulta('a', '2030-01-07', '09:00'), consulta('b', '2030-01-07', '10:00')]
    const depois = agendamentosReducer(estado, { type: 'cancelar', id: 'a' })
    expect(depois.map((c) => c.status)).toEqual(['cancelada', 'agendada'])
  })

  it('rejeita ação desconhecida', () => {
    expect(() => agendamentosReducer([], { type: 'apagar-tudo' })).toThrow()
  })

  it('horário cancelado volta a ficar livre', () => {
    const estado = [consulta('a', '2030-01-07', '09:00', 'cancelada')]
    expect(horarioOcupado(estado, '2030-01-07', '09:00')).toBe(false)
  })

  it('próximas consultas ignoram passadas e canceladas e vêm em ordem', () => {
    const estado = [
      consulta('futura2', '2030-01-08', '08:00'),
      consulta('passada', '2030-01-07', '08:00'),
      consulta('futura1', '2030-01-07', '15:00'),
      consulta('cancelada', '2030-01-07', '16:00', 'cancelada'),
    ]
    expect(proximasConsultas(estado, '2030-01-07', '12:00').map((c) => c.id)).toEqual(['futura1', 'futura2'])
  })
})

describe('formularioReducer', () => {
  it('pré-seleciona o paciente vindo da ficha', () => {
    expect(iniciarFormulario(7).valores.pacienteId).toBe(7)
  })

  it('alterar um campo apaga só o erro dele', () => {
    const estado = { ...formularioVazio, erros: { tipo: 'x', data: 'y' } }
    const depois = formularioReducer(estado, { type: 'alterar', campo: 'tipo', valor: 'Retorno' })
    expect(depois.erros).toEqual({ data: 'y' })
    expect(depois.valores.tipo).toBe('Retorno')
  })

  it('trocar a data apaga também o erro de horário', () => {
    const estado = { ...formularioVazio, erros: { horario: 'ocupado' } }
    expect(formularioReducer(estado, { type: 'alterar', campo: 'data', valor: '2030-01-08' }).erros).toEqual({})
  })
})

describe('validar', () => {
  const valido = { pacienteId: 1, data: '2030-01-07', horario: '09:00', tipo: 'Retorno', observacoes: '' } // segunda-feira

  it('aceita um agendamento válido', () => {
    expect(validar(valido, [], '2030-01-07', '08:00')).toEqual({})
  })

  it('exige os campos obrigatórios', () => {
    expect(Object.keys(validar(formularioVazio.valores, [], '2030-01-07', '08:00')).sort())
      .toEqual(['data', 'horario', 'pacienteId', 'tipo'])
  })

  it('recusa data passada, fim de semana e horário já passado hoje', () => {
    expect(validar({ ...valido, data: '2030-01-04' }, [], '2030-01-07', '08:00').data).toMatch(/passou/)
    expect(validar({ ...valido, data: '2030-01-12' }, [], '2030-01-07', '08:00').data).toMatch(/sábados/)
    expect(validar(valido, [], '2030-01-07', '10:00').horario).toMatch(/já passou/)
  })

  it('recusa horário ocupado', () => {
    const existentes = [consulta('a', '2030-01-07', '09:00')]
    expect(validar(valido, existentes, '2030-01-07', '08:00').horario).toMatch(/Já existe/)
  })
})
