import { Link } from 'react-router-dom'
import { Vazio } from '../components/Estado'

export default function NaoEncontrada() {
  return (
    <Vazio titulo="Esta página não existe">
      <p>
        O endereço pode estar incorreto. <Link to="/dashboard">Voltar ao painel</Link>
      </p>
    </Vazio>
  )
}
