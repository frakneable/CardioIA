"""Monta, localmente, o espelho da Fase 1 pronto para upload manual ao Drive.

Contexto: o Task 10 original previa subir os artefatos ao Google Drive via
service account. A única credencial de Drive disponível nesta máquina
pertence a uma conta corporativa — este é um projeto pessoal e acadêmico,
sem qualquer vínculo com a empresa, então usar essa credencial está fora de
cogitação. A solução adotada foi upload manual:
este script apenas monta, fora do repositório, a árvore de pastas exatamente
como deve ficar no Drive pessoal do aluno, e o usuário arrasta a pasta
inteira pela interface web. Não há chamada de API, não há credencial nem
rede envolvida — só cópia de arquivo local.

Estrutura gerada em `~/CardioIA-Fase1-upload/`:
    LEIA-ME.txt
    numerico/   <- fase1/data/numerico/
    textos/     <- fase1/docs/textos/
    imagens/    <- fase1/assets/imagens/ (120 .jpg + MANIFEST.csv)

POR QUE NÃO NA ÁREA DE TRABALHO: `Path.home()/"Desktop"` é uma armadilha em
máquina com OneDrive. Quando o Known Folder Move está ativo, a Área de Trabalho
real fica em `~/OneDrive - <Empresa>/Desktop`, e escrever no caminho literal
cria uma pasta `Desktop` fantasma que o Explorer não mostra — foi o que
aconteceu aqui. Escrever na Área de Trabalho real seria pior: sincronizaria os
20 MB deste projeto acadêmico para o OneDrive corporativo, o mesmo motivo pelo
qual a service account da empresa foi descartada acima. Por isso o destino é a
pasta pessoal, que nenhum OneDrive redireciona.

Idempotente: a pasta de destino é removida e recriada a cada execução, então
rodar de novo nunca acumula lixo de execuções antigas.

Uso:
    .venv/bin/python fase1/scripts/preparar_espelho_drive.py [destino]
"""
from __future__ import annotations

import csv
import pathlib
import shutil
import sys

import comum

PADRAO = pathlib.Path.home() / "CardioIA-Fase1-upload"

LEIA_ME = """\
CARDIOIA — FASE 1 — ESPELHO PÚBLICO DE DADOS
=============================================

Este é o espelho público dos dados da Fase 1 do projeto acadêmico CardioIA
(FIAP). O conteúdo aqui é idêntico ao do repositório do projeto — esta cópia
existe apenas para permitir o compartilhamento de arquivos binários (imagens,
CSVs) que não fazem sentido versionar em Git.

Estrutura:
  numerico/  - dados clínicos e de telemetria IoT em formato tabular (CSV)
  textos/    - textos de referência sobre doenças cardiovasculares
  imagens/   - 120 imagens de ECG de 12 derivações + MANIFEST.csv

Integridade das imagens: cada linha do MANIFEST.csv traz o hash SHA-256 do
arquivo correspondente. Para conferir que uma imagem não foi alterada,
recalcule o SHA-256 do arquivo e compare com a coluna `sha256` da linha dele
no manifesto.

Uso: exclusivamente acadêmico, no contexto da disciplina/curso da FIAP.

Atribuições e licenças:
  - Dados clínicos: UCI Heart Disease Dataset (Detrano et al., 1989),
    UCI Machine Learning Repository.
  - Textos: artigos do SciELO, licença CC BY 4.0.
  - Imagens de ECG: "ECG Images dataset of Cardiac Patients", Khan, A.H. &
    Hussain, M., Mendeley Data, DOI 10.17632/gwbz3fsgp8.2, licença CC BY 4.0.
"""


def _copiar_arvore(origem, destino) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for item in sorted(origem.iterdir()):
        if item.is_file():
            shutil.copy2(item, destino / item.name)


def main() -> None:
    destino = pathlib.Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else PADRAO
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)

    (destino / "LEIA-ME.txt").write_text(LEIA_ME, encoding="utf-8")

    grupos = {
        "numerico": comum.RAIZ / "data" / "numerico",
        "textos": comum.RAIZ / "docs" / "textos",
        "imagens": comum.RAIZ / "assets" / "imagens",
    }

    total_bytes = 0
    total_arquivos = 0
    print("== Montando espelho em", destino, "==")
    for nome, origem in grupos.items():
        alvo = destino / nome
        _copiar_arvore(origem, alvo)
        arquivos = [f for f in alvo.iterdir() if f.is_file()]
        tamanho = sum(f.stat().st_size for f in arquivos)
        total_bytes += tamanho
        total_arquivos += len(arquivos)
        print(f"  {nome}/: {len(arquivos)} arquivos, {tamanho / 1_048_576:.2f} MB")

    # Verificação: contagem de imagens copiadas deve bater com o MANIFEST.csv.
    manifest = destino / "imagens" / "MANIFEST.csv"
    with open(manifest, encoding="utf-8") as f:
        linhas_manifesto = sum(1 for _ in csv.DictReader(f))
    imagens_copiadas = len(list((destino / "imagens").glob("*.jpg")))
    if imagens_copiadas != linhas_manifesto:
        print(
            f"ERRO: {imagens_copiadas} imagens .jpg copiadas, mas "
            f"MANIFEST.csv tem {linhas_manifesto} linhas.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"\nVerificação OK: {imagens_copiadas} imagens == "
        f"{linhas_manifesto} linhas do MANIFEST.csv"
    )
    print(f"\nTotal: {total_arquivos + 1} arquivos "
          f"(+ LEIA-ME.txt), {total_bytes / 1_048_576:.2f} MB")
    print(f"\nEspelho pronto em: {destino}")
    print(
        "\nAo atualizar o Drive, SUBSTITUA os arquivos dentro das pastas que já\n"
        "existem lá. Arrastar a pasta inteira de novo cria pastas com IDs novos\n"
        "e quebra os links publicados no README."
    )


if __name__ == "__main__":
    main()
