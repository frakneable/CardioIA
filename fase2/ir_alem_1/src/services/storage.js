// Acesso ao localStorage protegido: em janela anônima ou com armazenamento
// bloqueado, o navegador pode lançar erro, e o portal deve continuar funcionando.

export function lerJSON(chave, padrao) {
  try {
    const valor = localStorage.getItem(chave)
    return valor === null ? padrao : JSON.parse(valor)
  } catch {
    return padrao
  }
}

export function gravarJSON(chave, valor) {
  try {
    localStorage.setItem(chave, JSON.stringify(valor))
  } catch {
    // sem armazenamento disponível: os dados ficam só na memória desta aba
  }
}

export function lerTexto(chave) {
  try {
    return localStorage.getItem(chave)
  } catch {
    return null
  }
}

export function gravarTexto(chave, valor) {
  try {
    if (valor === null) localStorage.removeItem(chave)
    else localStorage.setItem(chave, valor)
  } catch {
    // idem
  }
}
