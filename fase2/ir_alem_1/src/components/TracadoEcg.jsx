import { useEffect, useId, useMemo, useRef } from 'react'
import styles from './TracadoEcg.module.css'

const LARGURA_BATIMENTO = 150 // largura média de um batimento, em unidades do viewBox
const ALTURA = 120
const BASE = 72 // linha de base
const BPM = 72 // frequência média simulada
const VELOCIDADE = (LARGURA_BATIMENTO * BPM) / 60 // unidades por segundo
const VAO = 45 // largura da faixa vazia que separa o traçado novo do antigo
const DURACAO_ENTRADA_MS = 2800 // animação CSS "escrever" (atraso + duração)

// Um ciclo cardíaco em pontos relativos: onda P, complexo QRS e onda T.
// A terceira coluna diz a qual onda o ponto pertence, para variar cada uma.
const CICLO = [
  [0, 0, 'P'], [18, 0, 'P'], [24, -5, 'P'], [30, -7, 'P'], [36, -5, 'P'], [42, 0, 'P'],
  [52, 0, 'R'], [56, 6, 'R'], [62, -58, 'R'], [68, 16, 'R'], [73, 0, 'R'],
  [86, 0, 'T'], [96, -9, 'T'], [106, -13, 'T'], [116, -9, 'T'], [124, 0, 'T'],
]

const sortear = (min, max) => min + Math.random() * (max - min)

// Variações de um ritmo sinusal NORMAL: a forma do batimento não muda, só
// oscila dentro do que acontece num coração saudável.
function novoBatimento(inicio) {
  return {
    inicio,
    largura: LARGURA_BATIMENTO * sortear(0.93, 1.07), // variabilidade da frequência cardíaca
    amplitude: { P: sortear(0.8, 1.2), R: sortear(0.9, 1.08), T: sortear(0.85, 1.15) },
  }
}

// Gera o sinal como uma fita contínua: cada passada da varredura lê o
// próximo trecho da fita, então os batimentos continuam de onde pararam.
function criarFita() {
  const batimentos = [novoBatimento(0)]
  const fase = sortear(0, Math.PI * 2)

  function garantirAte(x) {
    while (batimentos.at(-1).inicio < x) {
      const ultimo = batimentos.at(-1)
      batimentos.push(novoBatimento(ultimo.inicio + ultimo.largura))
    }
    while (batimentos.length > 2 && batimentos[1].inicio + batimentos[1].largura < x - 2000) {
      batimentos.shift() // descarta o que já saiu da tela
    }
  }

  // Caminho SVG do trecho [inicio, inicio + largura] da fita, em coordenadas da tela
  return function trecho(inicio, largura) {
    garantirAte(inicio + largura + LARGURA_BATIMENTO * 2)
    const pontos = []
    for (const b of batimentos) {
      if (b.inicio + b.largura < inicio - LARGURA_BATIMENTO || b.inicio > inicio + largura + LARGURA_BATIMENTO) continue
      const escala = b.largura / LARGURA_BATIMENTO
      for (const [x, y, onda] of CICLO) {
        const gx = b.inicio + x * escala
        const respiracao = 2.2 * Math.sin(gx / 420 + fase) // oscilação lenta da linha de base
        pontos.push([gx - inicio, BASE + y * b.amplitude[onda] + respiracao])
      }
    }
    return pontos.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
  }
}

// Traçado de ECG em loop, como num monitor de beira de leito: depois da
// entrada, uma faixa vazia percorre a tela; atrás dela surge o traçado novo,
// à frente fica o antigo. Cada passada traz batimentos ligeiramente diferentes.
// Decorativo: leitores de tela recebem só o rótulo.
export default function TracadoEcg({ batimentos = 5, rotulo = 'Traçado de eletrocardiograma' }) {
  const largura = batimentos * LARGURA_BATIMENTO
  // useId pode conter ':' ou '«»', que quebram a referência url(#...) do recorte
  const id = `ecg-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`

  const fita = useMemo(() => criarFita(), [])
  const inicial = useMemo(() => fita(0, largura), [fita, largura])

  const atual = useRef(null)
  const anterior = useRef(null)
  const recorteAtual = useRef(null)
  const recorteAnterior = useRef(null)

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    // A varredura atualiza os atributos direto no DOM, a 60 quadros por
    // segundo, sem re-renderizar o componente React.
    const duracaoPassada = ((largura + VAO) / VELOCIDADE) * 1000
    let posicaoNaFita = 0
    let quadro
    let inicioPassada

    function novaPassada(agora) {
      inicioPassada = agora
      posicaoNaFita += largura
      anterior.current.setAttribute('d', atual.current.getAttribute('d'))
      atual.current.setAttribute('d', fita(posicaoNaFita, largura))
    }

    function animar(agora) {
      if ((agora - inicioPassada) >= duracaoPassada) novaPassada(agora)
      // x = borda esquerda da faixa vazia; vai de -VAO até a largura total
      const x = ((agora - inicioPassada) / duracaoPassada) * (largura + VAO) - VAO
      recorteAtual.current.setAttribute('width', Math.max(0, x))
      recorteAnterior.current.setAttribute('x', x + VAO)
      quadro = requestAnimationFrame(animar)
    }

    const espera = setTimeout(() => {
      // Fim da entrada: o traçado desenhado vira o "antigo" da primeira passada
      atual.current.classList.remove(styles.entrada)
      novaPassada(performance.now())
      quadro = requestAnimationFrame(animar)
    }, DURACAO_ENTRADA_MS)

    return () => {
      clearTimeout(espera)
      cancelAnimationFrame(quadro)
    }
  }, [fita, largura])

  return (
    <svg
      className={styles.tracado}
      viewBox={`0 0 ${largura} ${ALTURA}`}
      style={{ aspectRatio: `${largura} / ${ALTURA}` }}
      role="img"
      aria-label={rotulo}
    >
      <defs>
        {/* Começa com o traçado atual em tela cheia e o anterior escondido */}
        <clipPath id={`${id}-atual`}>
          <rect ref={recorteAtual} x="0" y="-20" width={largura} height={ALTURA + 40} />
        </clipPath>
        <clipPath id={`${id}-anterior`}>
          <rect ref={recorteAnterior} x={largura} y="-20" width={largura} height={ALTURA + 40} />
        </clipPath>
      </defs>
      <path ref={anterior} className={styles.linha} clipPath={`url(#${id}-anterior)`} />
      <path
        ref={atual}
        d={inicial}
        pathLength="1"
        className={`${styles.linha} ${styles.entrada}`}
        clipPath={`url(#${id}-atual)`}
      />
    </svg>
  )
}
