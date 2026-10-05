// "API" de pacientes. Os dados vêm de um JSON estático em public/data,
// buscado com fetch como se fosse um endpoint real. O atraso artificial deixa
// visíveis os estados de carregamento da interface.

const URL_PACIENTES = '/data/pacientes.json'
const LATENCIA_MS = 500

export function esperar(ms, sinal) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms)
    sinal?.addEventListener('abort', () => {
      clearTimeout(timer)
      reject(new DOMException('Requisição cancelada', 'AbortError'))
    })
  })
}

export async function buscarPacientes({ signal } = {}) {
  await esperar(LATENCIA_MS, signal)
  const resposta = await fetch(URL_PACIENTES, { signal })
  if (!resposta.ok) {
    throw new Error(`Não foi possível carregar os pacientes (erro ${resposta.status}).`)
  }
  return resposta.json()
}
