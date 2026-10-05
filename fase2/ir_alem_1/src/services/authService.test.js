import { describe, expect, it } from 'vitest'
import { criarTokenFalso, lerToken, login } from './authService'

const usuario = { email: 'medico@cardioia.com', nome: 'Dra. Marina Albuquerque', papel: 'Cardiologista' }

describe('JWT simulado', () => {
  it('tem as três partes de um JWT e preserva acentos no payload', () => {
    const token = criarTokenFalso({ ...usuario, papel: 'Recepção' })
    expect(token.split('.')).toHaveLength(3)
    expect(lerToken(token).papel).toBe('Recepção')
  })

  it('expira depois de 8 horas', () => {
    const agora = Date.UTC(2030, 0, 7, 8)
    const token = criarTokenFalso(usuario, agora)
    expect(lerToken(token, agora + 7.9 * 3600e3)).not.toBeNull()
    expect(lerToken(token, agora + 8 * 3600e3)).toBeNull()
  })

  it('recusa tokens malformados', () => {
    expect(lerToken(null)).toBeNull()
    expect(lerToken('abc')).toBeNull()
    expect(lerToken('a.b.c')).toBeNull()
  })

  it('login aceita a conta de demonstração e recusa senha errada', async () => {
    expect(lerToken(await login(' Medico@CardioIA.com ', 'cardio123')).nome).toBe(usuario.nome)
    await expect(login('medico@cardioia.com', 'errada')).rejects.toThrow(/incorretos/)
  })
})
