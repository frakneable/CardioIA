// Autenticação SIMULADA. Não existe servidor: o "login" confere as credenciais
// de demonstração abaixo e gera um JWT falso no próprio navegador.
//
// Um JWT real tem três partes em base64url: cabeçalho.payload.assinatura.
// Aqui o cabeçalho e o payload seguem o formato real, mas a assinatura é um
// texto fixo. Por isso este token NÃO oferece segurança alguma: serve só para
// simular o fluxo de autenticação no front-end.

import { esperar } from './api'

export const CHAVE_TOKEN = 'cardioia:token'
const DURACAO_SESSAO_MS = 8 * 60 * 60 * 1000 // um plantão de 8 horas

const USUARIOS_DEMO = [
  { email: 'medico@cardioia.com', senha: 'cardio123', nome: 'Dra. Marina Albuquerque', papel: 'Cardiologista' },
  { email: 'recepcao@cardioia.com', senha: 'cardio123', nome: 'Rafael Nogueira', papel: 'Recepção' },
]

export const CREDENCIAIS_DEMO = USUARIOS_DEMO.map(({ email, senha, papel }) => ({ email, senha, papel }))

// Perfis que podem ver a tabela de pacientes com dados clínicos. A recepção
// só agenda consultas: pressão, colesterol e diagnóstico não são da conta dela.
export const PAPEIS_DADOS_CLINICOS = ['Cardiologista']

export function podeAcessar(usuario, papeis) {
  return !papeis || papeis.includes(usuario?.papel)
}

function paraBase64Url(objeto) {
  // TextEncoder garante que acentos ("Albuquerque", "Recepção") sejam codificados corretamente
  const bytes = new TextEncoder().encode(JSON.stringify(objeto))
  const binario = Array.from(bytes, (b) => String.fromCharCode(b)).join('')
  return btoa(binario).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function deBase64Url(texto) {
  const base64 = texto.replace(/-/g, '+').replace(/_/g, '/')
  const binario = atob(base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '='))
  return JSON.parse(new TextDecoder().decode(Uint8Array.from(binario, (c) => c.charCodeAt(0))))
}

export function criarTokenFalso(usuario, agora = Date.now()) {
  const cabecalho = { alg: 'HS256', typ: 'JWT' }
  const payload = {
    sub: usuario.email,
    nome: usuario.nome,
    papel: usuario.papel,
    iat: Math.floor(agora / 1000),
    exp: Math.floor((agora + DURACAO_SESSAO_MS) / 1000),
  }
  return `${paraBase64Url(cabecalho)}.${paraBase64Url(payload)}.assinatura-simulada`
}

// Devolve o payload se o token tiver formato válido e não estiver expirado; senão, null.
export function lerToken(token, agora = Date.now()) {
  if (typeof token !== 'string') return null
  const partes = token.split('.')
  if (partes.length !== 3) return null
  try {
    const payload = deBase64Url(partes[1])
    if (!payload.exp || payload.exp * 1000 <= agora) return null
    return payload
  } catch {
    return null
  }
}

export async function login(email, senha) {
  await esperar(600) // simula a ida ao servidor
  const usuario = USUARIOS_DEMO.find(
    (u) => u.email === email.trim().toLowerCase() && u.senha === senha,
  )
  if (!usuario) {
    throw new Error('E-mail ou senha incorretos. Use uma das contas de demonstração abaixo.')
  }
  return criarTokenFalso(usuario)
}
