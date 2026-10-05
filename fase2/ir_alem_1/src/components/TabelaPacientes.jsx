import styles from './TabelaPacientes.module.css'

function medida(valor, unidade) {
  return valor === null ? <span className={styles.ausente}>não medido</span> : `${valor} ${unidade}`
}

export default function TabelaPacientes({ pacientes, aoAbrir }) {
  return (
    <div className={styles.moldura}>
      <table className={styles.tabela}>
        <thead>
          <tr>
            <th scope="col">Paciente</th>
            <th scope="col">Idade</th>
            <th scope="col">Pressão sistólica</th>
            <th scope="col">Colesterol</th>
            <th scope="col">Diagnóstico</th>
            <th scope="col"><span className="visually-hidden">Ações</span></th>
          </tr>
        </thead>
        <tbody>
          {pacientes.map((p) => (
            <tr key={p.id}>
              <th scope="row" data-rotulo="Paciente">
                <span className={styles.nome}>{p.nome}</span>
                <span className={styles.meta}>{p.sexo === 'feminino' ? 'Feminino' : 'Masculino'}, {p.centro}</span>
              </th>
              <td data-rotulo="Idade">{p.idade} anos</td>
              <td data-rotulo="Pressão sistólica">{medida(p.pressaoSistolica, 'mmHg')}</td>
              <td data-rotulo="Colesterol">{medida(p.colesterol, 'mg/dL')}</td>
              <td data-rotulo="Diagnóstico">
                <span className={p.doencaCardiaca ? styles.com : styles.sem}>
                  {p.doencaCardiaca ? 'Doença cardíaca' : 'Sem doença cardíaca'}
                </span>
              </td>
              <td className={styles.acao}>
                <button type="button" onClick={() => aoAbrir(p.id)}>
                  Ver ficha<span className="visually-hidden"> de {p.nome}</span>
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
