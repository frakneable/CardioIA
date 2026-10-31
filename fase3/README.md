# CardioIA — Fase 3: Monitoramento Contínuo (IoT, Edge e Nuvem)

> **Fases do projeto:** [Fase 1 — Batimentos de Dados](../README.md) ·
> [Fase 2 — Diagnóstico Automatizado](../fase2/README.md) · Fase 3 (este documento)

Projeto acadêmico FIAP. Nesta fase o CardioIA vira um vestível simulado:
um ESP32 que captura sinais vitais, processa e guarda os dados localmente,
transmite para a nuvem e alimenta dashboards com alertas.

## 👨‍🎓 Integrantes
- Victor Copque dos Reis — RM566821
- Victor Hugo Ferreira Rolim — RM568006

## 📌 O que está entregue

| Parte | Entregável | Arquivo |
|---|---|---|
| 1 | Projeto no Wokwi | https://wokwi.com/projects/479413654575407105 |
| 1 | Código C++ comentado (ESP32) | [`parte1/sketch.ino`](parte1/sketch.ino) |
| 1 | Circuito do Wokwi e tabela de partições (cria a área do SPIFFS) | [`parte1/diagram.json`](parte1/diagram.json) · [`parte1/partitions.csv`](parte1/partitions.csv) |
| 1 | Relatório: fluxo de funcionamento e lógica de resiliência | [`parte1/RELATORIO.md`](parte1/RELATORIO.md) |

## Parte 1 — Edge Computing

ESP32 com **DHT22** (temperatura e umidade), **potenciômetro** simulando o
sensor de pulso (BPM) e **MPU6050** (movimento e queda). Toda leitura é
classificada no próprio dispositivo (alertas de bradicardia, taquicardia
conforme o movimento, febre, hipotermia e queda), gravada em CSV no **SPIFFS**
e enviada à "nuvem" (`Serial.println`) quando a chave de Wi-Fi está ligada.
Depois do envio, o arquivo local é apagado.

**Resiliência offline:** sem conexão a coleta continua, e ao reconectar tudo é
sincronizado em ordem. Se a conexão cair no meio do envio, o que faltou volta
para o buffer. O buffer comporta **24 h offline (8.640 leituras)**. Quando
enche, as leituras com alerta são todas mantidas e metade das normais é
descartada, para não perder justamente o episódio clínico. Detalhes no
[relatório](parte1/RELATORIO.md).

### Como rodar no Wokwi

O projeto já está montado e salvo em
**https://wokwi.com/projects/479413654575407105**. Para recriar do zero:

1. Em [wokwi.com](https://wokwi.com), crie um projeto **ESP32** novo.
2. Substitua o conteúdo de `sketch.ino` e `diagram.json` pelos desta pasta.
3. Crie o arquivo `partitions.csv` (menu ▾ ao lado das abas → *New file...*)
   com o conteúdo desta pasta. Sem ele, o ESP32 do Wokwi não tem partição de
   dados e o SPIFFS falha com `spiffs partition could not be found`.
4. Em **Library Manager**, adicione as bibliotecas de `libraries.txt`.
5. Inicie a simulação e use os controles:
   - **chave deslizante:** liga e desliga o Wi-Fi;
   - **potenciômetro:** muda o BPM;
   - **DHT22:** clique nele e altere a temperatura;
   - **MPU6050:** clique nele e altere a aceleração (acima de 2,5 g simula
     uma queda).

O modo demonstração (`MODO_DEMO true`) faz uma leitura a cada 2 s e usa um
buffer de 20 registros, para a compactação aparecer rápido. Com `false`, o
código usa os parâmetros de produção (10 s e 8.640 registros).

### Compilar localmente (opcional)

```bash
arduino-cli core install esp32:esp32
arduino-cli lib install "DHT sensor library" "Adafruit MPU6050"
mkdir -p /tmp/cardioia_edge && cp fase3/parte1/sketch.ino /tmp/cardioia_edge/cardioia_edge.ino
arduino-cli compile --fqbn esp32:esp32:esp32 /tmp/cardioia_edge
```
