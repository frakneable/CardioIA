"""Automação do e-mail de alerta (a parte "RPA" do fluxo).

Monta a mensagem que a enfermagem receberia e entrega por um de dois modos,
escolhido pela variável EMAIL_MODO:

- ``arquivo`` (padrão): grava o e-mail completo (.eml) em ``caixa_saida/``.
  É a simulação: o arquivo abre em qualquer cliente de e-mail.
- ``smtp``: envia de verdade pelo protocolo SMTP (smtplib), com o servidor
  configurado em SMTP_HOST, SMTP_PORTA, SMTP_USUARIO, SMTP_SENHA e SMTP_TLS.
  Para testar sem conta nenhuma: ``python -m aiosmtpd -n -l localhost:1025``.
"""

import html
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

from risco import DESCRICAO, Risco

PASTA_SAIDA = Path(__file__).resolve().parent / "caixa_saida"

REMETENTE = os.getenv("EMAIL_REMETENTE", "CardioIA Alertas <alertas@cardioia.local>")
DESTINATARIOS = os.getenv("EMAIL_DESTINO", "enfermagem@cardioia.local").split(",")

ROTULO = {"critico": "CRÍTICO", "atencao": "ATENÇÃO"}


def nome(motivo: str) -> str:
    return "ausência de movimento" if motivo == "ausencia_movimento" else motivo


def montar_email(leitura: dict, risco: Risco, novos: list[str]) -> EmailMessage:
    """Cria o e-mail com versão em texto e em HTML."""
    quando = datetime.fromtimestamp(leitura["ts"]).strftime("%d/%m/%Y %H:%M:%S")
    rotulo = ROTULO[risco.severidade]
    motivos = ", ".join(nome(m) for m in risco.motivos)

    msg = EmailMessage()
    msg["Subject"] = f"[CardioIA][{rotulo}] {leitura['paciente']}: {motivos}"
    msg["From"] = REMETENTE
    msg["To"] = ", ".join(DESTINATARIOS)
    msg["Message-ID"] = make_msgid(domain="cardioia.local")

    linhas_motivo = [
        f"  - {nome(m)}: {DESCRICAO[m]}" + (" (NOVO)" if m in novos else "")
        for m in risco.motivos
    ]
    sinais = (
        f"  Frequência cardíaca: {leitura['bpm'] or 'sem leitura'} BPM\n"
        f"  Temperatura: {leitura['temp']:.1f} °C\n"
        f"  Umidade da pele: {leitura['umid']:.0f} %\n"
        f"  Movimento: {risco.movimento} ({leitura['acel']:.2f} g)"
    )
    msg.set_content(
        f"Alerta {rotulo} do monitor CardioIA\n\n"
        f"Paciente: {leitura['paciente']}\n"
        f"Leitura nº {leitura['seq']} em {quando}\n\n"
        "Motivos:\n" + "\n".join(linhas_motivo) + "\n\n"
        "Sinais vitais:\n" + sinais + "\n\n"
        "Verifique o paciente. Mensagem automática, não responda.\n"
    )

    cor = "#b42318" if risco.severidade == "critico" else "#b54708"
    itens = "".join(
        f"<li><b>{html.escape(nome(m))}</b>: {html.escape(DESCRICAO[m])}"
        + (" <span style='color:#b42318'>(novo)</span>" if m in novos else "")
        + "</li>"
        for m in risco.motivos
    )
    msg.add_alternative(
        f"""\
<div style="font-family:Arial,sans-serif;max-width:560px;color:#1d2939">
  <div style="background:{cor};color:#fff;padding:14px 18px;border-radius:8px 8px 0 0">
    <div style="font-size:12px;letter-spacing:1px">CARDIOIA · ALERTA {rotulo}</div>
    <div style="font-size:20px;font-weight:bold">{html.escape(leitura['paciente'])}: {html.escape(motivos)}</div>
  </div>
  <div style="border:1px solid #eaecf0;border-top:0;padding:16px 18px;border-radius:0 0 8px 8px">
    <p style="margin:0 0 8px">Leitura nº {leitura['seq']} em {quando}</p>
    <ul style="margin:0 0 12px;padding-left:20px">{itens}</ul>
    <table style="border-collapse:collapse;width:100%">
      <tr><td style="padding:6px 0;color:#667085">Frequência cardíaca</td><td style="text-align:right"><b>{leitura['bpm'] or 'sem leitura'} BPM</b></td></tr>
      <tr><td style="padding:6px 0;color:#667085">Temperatura</td><td style="text-align:right"><b>{leitura['temp']:.1f} °C</b></td></tr>
      <tr><td style="padding:6px 0;color:#667085">Umidade da pele</td><td style="text-align:right"><b>{leitura['umid']:.0f} %</b></td></tr>
      <tr><td style="padding:6px 0;color:#667085">Movimento</td><td style="text-align:right"><b>{risco.movimento} ({leitura['acel']:.2f} g)</b></td></tr>
    </table>
    <p style="margin:14px 0 0;font-size:12px;color:#667085">Verifique o paciente. Mensagem automática do CardioIA, não responda.</p>
  </div>
</div>
""",
        subtype="html",
    )
    return msg


def enviar(msg: EmailMessage) -> str:
    """Entrega o e-mail e devolve onde ele foi parar (caminho ou servidor)."""
    modo = os.getenv("EMAIL_MODO", "arquivo")
    if modo == "smtp":
        host = os.getenv("SMTP_HOST", "localhost")
        porta = int(os.getenv("SMTP_PORTA", "1025"))
        with smtplib.SMTP(host, porta, timeout=10) as smtp:
            if os.getenv("SMTP_TLS", "0") == "1":
                smtp.starttls()
            if os.getenv("SMTP_USUARIO"):
                smtp.login(os.environ["SMTP_USUARIO"], os.environ["SMTP_SENHA"])
            smtp.send_message(msg)
        return f"smtp://{host}:{porta}"

    PASTA_SAIDA.mkdir(exist_ok=True)
    arquivo = datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".eml"
    caminho = PASTA_SAIDA / arquivo
    caminho.write_bytes(bytes(msg))
    return str(caminho.relative_to(PASTA_SAIDA.parent))
