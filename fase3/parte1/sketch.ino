/*
 * CardioIA — Fase 3, Parte 1: Edge Computing com ESP32
 * ----------------------------------------------------
 * Protótipo de vestível cardíaco que coleta sinais vitais, processa no próprio
 * dispositivo (Edge), guarda as leituras em SPIFFS e só as entrega à "nuvem"
 * quando há conectividade (store-and-forward).
 *
 * Sensores:
 *   - DHT22 ........... temperatura (°C) e umidade (%)       -> GPIO 15
 *   - Potenciômetro ... simula o sensor de pulso (BPM)        -> GPIO 34 (ADC)
 *   - MPU6050 ......... acelerômetro, detecta atividade/queda -> I2C (SDA 21, SCL 22)
 *
 * Atuadores / controles:
 *   - Chave deslizante: simula o Wi-Fi (variável booleana wifiConectado) -> GPIO 27
 *   - LED verde: online / sincronizando                                 -> GPIO 2
 *   - LED vermelho: alerta clínico na última leitura                    -> GPIO 4
 *
 * "Nuvem" = Serial.println com prefixo [NUVEM]. Na Parte 2 o envio passa a ser MQTT.
 *
 * Situações para testar (mexa nas peças com a simulação rodando):
 *   Situação                Potenciômetro   DHT22     MPU6050 (aceleração Z)  Resultado
 *   ----------------------  --------------  --------  ----------------------  -----------------------
 *   Normal (estado inicial) ~26% -> 74 BPM  36,6 °C   1 g                     sem alerta
 *   Taquicardia em repouso  ~80% -> 165 BPM 36,6 °C   1 g                     ALERTA: taquicardia
 *   Febre                   ~74 BPM         38,6 °C   1 g                     ALERTA: febre
 *   Hipotermia              ~74 BPM         34,5 °C   1 g                     ALERTA: hipotermia
 *   Correndo                ~65% -> 140 BPM 36,6 °C   1,5 g (atividade)       sem alerta (limite 150)
 *   Mesma FC, deitado       ~140 BPM        36,6 °C   1 g (repouso)           ALERTA: taquicardia
 *   Bradicardia             ~6%  -> 40 BPM  36,6 °C   1 g                     ALERTA: bradicardia
 *   Queda                   ~74 BPM         36,6 °C   3 g (impacto)           ALERTA: queda
 *   Sem conexão             qualquer        qualquer  qualquer                chave Wi-Fi desligada:
 *                                                                             [OFFLINE] grava no SPIFFS
 *   Reconexão               qualquer        qualquer  qualquer                chave ligada: [NUVEM] envia
 *                                                                             tudo e apaga o arquivo
 *
 * Para voltar ao normal, desfaça o ajuste. O BPM aparece em cada [LEITURA].
 *
 * Observação sobre o simulador: o SPIFFS do Wokwi funciona durante a sessão,
 * mas é volátil (some ao reiniciar a simulação). Num ESP32 real o arquivo
 * sobrevive a quedas de energia. O Monitor Serial registra tudo o que foi
 * gravado e enviado, servindo como trilha de auditoria alternativa.
 */

#include <Arduino.h>
#include <FS.h>
#include <SPIFFS.h>
#include <Wire.h>
#include <DHT.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// ---------------------------------------------------------------------------
// Pinos
// ---------------------------------------------------------------------------
#define PINO_DHT        15
#define PINO_PULSO      34
#define PINO_WIFI       27
#define PINO_LED_ONLINE 2
#define PINO_LED_ALERTA 4

// ---------------------------------------------------------------------------
// Modelo de armazenamento
// ---------------------------------------------------------------------------
// Produção: 1 leitura a cada 10 s e capacidade de 8.640 registros = 24 h sem
// conexão. Cada linha do CSV tem ~45 bytes, ou seja, ~390 KB, que cabem com
// folga na partição SPIFFS padrão do ESP32 (~1,4 MB). 24 h cobre o caso real
// de um paciente que passa a noite e o dia seguinte longe do celular/gateway.
//
// Demonstração: leitura a cada 2 s e limite de 20 registros, para que a
// compactação do buffer apareça em poucos segundos de vídeo.
#define MODO_DEMO true

#if MODO_DEMO
const unsigned long INTERVALO_LEITURA_MS = 2000;
const unsigned long LIMITE_REGISTROS = 20;
#else
const unsigned long INTERVALO_LEITURA_MS = 10000;
const unsigned long LIMITE_REGISTROS = 8640;
#endif

// Depois de compactar, o buffer não pode passar de 75% do limite; assim a
// compactação não roda de novo a cada leitura.
const unsigned long ALVO_POS_COMPACTACAO = LIMITE_REGISTROS * 3 / 4;

const char *ARQUIVO_BUFFER = "/leituras.csv";
const char *ARQUIVO_TEMP   = "/leituras.tmp";
const char *CABECALHO_CSV  = "seq,t_s,temp_c,umid_pct,bpm,acel_g,movimento,alerta";

// ---------------------------------------------------------------------------
// Limiares clínicos (processamento no Edge)
// ---------------------------------------------------------------------------
const int   BPM_MIN             = 50;    // bradicardia
const int   BPM_MAX_REPOUSO     = 120;   // taquicardia em repouso
const int   BPM_MAX_ATIVIDADE   = 150;   // em atividade a FC alta é esperada
const float TEMP_FEBRE          = 37.8;
const float TEMP_HIPOTERMIA     = 35.0;
const float ACEL_DESVIO_ATIVO_G = 0.3;   // |a| longe de 1 g = paciente se movendo
const float ACEL_QUEDA_G        = 2.5;   // pico de impacto típico de queda

// ---------------------------------------------------------------------------
// Estado global
// ---------------------------------------------------------------------------
DHT dht(PINO_DHT, DHT22);
Adafruit_MPU6050 mpu;
bool mpuDisponivel = false;

bool wifiConectado = false;   // a "conectividade" simulada exigida pelo enunciado
bool wifiAnterior  = false;

unsigned long seq = 0;             // número de série da leitura: a nuvem usa para deduplicar
unsigned long registrosNoBuffer = 0;
unsigned long ultimaLeitura = 0;

struct Leitura {
  unsigned long seq;
  unsigned long tempoS;
  float temperatura;
  float umidade;
  int bpm;
  float acelG;
  const char *movimento;      // "repouso", "atividade" ou "queda"
  bool alerta;
  String motivo;
};

// ---------------------------------------------------------------------------
// Buffer local (SPIFFS)
// ---------------------------------------------------------------------------

// Conta as linhas de dados do buffer (sem o cabeçalho). Usado no boot, para
// retomar a contagem se o ESP32 real reiniciou com dados pendentes.
unsigned long contarRegistros() {
  File f = SPIFFS.open(ARQUIVO_BUFFER, FILE_READ);
  if (!f) return 0;
  unsigned long n = 0;
  lerLinha(f);                  // pula o cabeçalho
  while (f.available()) {
    if (lerLinha(f).length() > 0) n++;
  }
  f.close();
  return n;
}

// Cria o arquivo com cabeçalho, se ainda não existir.
void garantirArquivo() {
  if (SPIFFS.exists(ARQUIVO_BUFFER)) return;
  File f = SPIFFS.open(ARQUIVO_BUFFER, FILE_WRITE);
  f.println(CABECALHO_CSV);
  f.close();
}

// Lê uma linha do arquivo sem o "\r\n" final (println grava os dois).
String lerLinha(File &f) {
  String linha = f.readStringUntil('\n');
  linha.trim();
  return linha;
}

// Retorna true se a linha CSV tem alerta=1 (última coluna).
bool linhaTemAlerta(const String &linha) {
  return linha.endsWith(",1");
}

/*
 * Estratégia de armazenamento limitado.
 *
 * Quando o buffer enche, NÃO descartamos simplesmente as leituras mais
 * antigas: num monitor cardíaco, o episódio de taquicardia de 3 h atrás é
 * justamente o que o médico precisa ver. A compactação faz duas passadas:
 *
 *   1. Decimação: mantém TODAS as leituras com alerta e metade das normais
 *      (uma sim, uma não). A série normal perde resolução, mas continua
 *      cobrindo o período inteiro.
 *   2. Se ainda passar do alvo (ex.: horas seguidas em alerta), descarta as
 *      leituras mais antigas até chegar ao alvo. Só aqui algo clínico se perde,
 *      e o descarte fica registrado no log.
 */
void compactarBuffer() {
  Serial.printf("[EDGE] Buffer cheio (%lu/%lu). Compactando...\n",
                registrosNoBuffer, LIMITE_REGISTROS);

  // Passada 1: decimação das leituras normais
  File origem = SPIFFS.open(ARQUIVO_BUFFER, FILE_READ);
  File destino = SPIFFS.open(ARQUIVO_TEMP, FILE_WRITE);
  destino.println(lerLinha(origem));   // copia o cabeçalho
  unsigned long mantidos = 0, normais = 0;
  while (origem.available()) {
    String linha = lerLinha(origem);
    if (linha.length() == 0) continue;
    bool manter = linhaTemAlerta(linha) || (normais++ % 2 == 0);
    if (manter) {
      destino.println(linha);
      mantidos++;
    }
  }
  origem.close();
  destino.close();
  SPIFFS.remove(ARQUIVO_BUFFER);
  SPIFFS.rename(ARQUIVO_TEMP, ARQUIVO_BUFFER);
  Serial.printf("[EDGE] Decimação: %lu -> %lu registros (alertas preservados)\n",
                registrosNoBuffer, mantidos);
  registrosNoBuffer = mantidos;

  // Passada 2: descarte FIFO, só se a decimação não bastou
  if (registrosNoBuffer > ALVO_POS_COMPACTACAO) {
    unsigned long descartar = registrosNoBuffer - ALVO_POS_COMPACTACAO;
    origem = SPIFFS.open(ARQUIVO_BUFFER, FILE_READ);
    destino = SPIFFS.open(ARQUIVO_TEMP, FILE_WRITE);
    destino.println(lerLinha(origem));
    unsigned long i = 0;
    while (origem.available()) {
      String linha = lerLinha(origem);
      if (linha.length() == 0) continue;
      if (i++ >= descartar) destino.println(linha);
    }
    origem.close();
    destino.close();
    SPIFFS.remove(ARQUIVO_BUFFER);
    SPIFFS.rename(ARQUIVO_TEMP, ARQUIVO_BUFFER);
    registrosNoBuffer -= descartar;
    Serial.printf("[EDGE] Ainda acima do alvo: %lu registros mais antigos descartados\n",
                  descartar);
  }
}

// Acrescenta uma leitura ao final do CSV (append: não reescreve o arquivo).
void gravarLeitura(const Leitura &l) {
  if (registrosNoBuffer >= LIMITE_REGISTROS) compactarBuffer();

  File f = SPIFFS.open(ARQUIVO_BUFFER, FILE_APPEND);
  f.printf("%lu,%lu,%.1f,%.1f,%d,%.2f,%s,%d\n",
           l.seq, l.tempoS, l.temperatura, l.umidade, l.bpm, l.acelG,
           l.movimento, l.alerta ? 1 : 0);
  f.close();
  registrosNoBuffer++;
}

/*
 * Sincronização com a nuvem.
 *
 * Envia o buffer linha a linha e checa o Wi-Fi antes de cada envio. Se a
 * conexão cai no meio, o que ainda não foi enviado é regravado num arquivo
 * novo, e nada se perde nem é enviado duas vezes. Só quando tudo foi
 * entregue o arquivo local é apagado, como pede o enunciado.
 */
void sincronizar() {
  if (registrosNoBuffer == 0) return;

  Serial.printf("[SYNC] Enviando %lu registro(s) pendente(s) para a nuvem...\n",
                registrosNoBuffer);
  digitalWrite(PINO_LED_ONLINE, LOW);   // pisca durante o envio

  File origem = SPIFFS.open(ARQUIVO_BUFFER, FILE_READ);
  String cabecalho = lerLinha(origem);
  unsigned long enviados = 0;
  bool interrompido = false;
  File restante;

  while (origem.available()) {
    String linha = lerLinha(origem);
    if (linha.length() == 0) continue;

    wifiConectado = digitalRead(PINO_WIFI) == HIGH;
    if (!wifiConectado && !interrompido) {
      interrompido = true;
      restante = SPIFFS.open(ARQUIVO_TEMP, FILE_WRITE);
      restante.println(cabecalho);
    }

    if (interrompido) {
      restante.println(linha);        // guarda para a próxima conexão
    } else {
      Serial.print("[NUVEM] ");
      Serial.println(linha);          // "transmissão" para a nuvem
      enviados++;
      delay(50);                      // simula a latência de rede
    }
  }
  origem.close();

  SPIFFS.remove(ARQUIVO_BUFFER);      // apaga o arquivo local já sincronizado
  if (interrompido) {
    restante.close();
    SPIFFS.rename(ARQUIVO_TEMP, ARQUIVO_BUFFER);
    registrosNoBuffer -= enviados;
    Serial.printf("[SYNC] Conexão perdida: %lu enviado(s), %lu continuam no buffer\n",
                  enviados, registrosNoBuffer);
  } else {
    registrosNoBuffer = 0;
    Serial.printf("[SYNC] Concluído: %lu registro(s) entregue(s), arquivo local apagado\n",
                  enviados);
  }
  garantirArquivo();
  digitalWrite(PINO_LED_ONLINE, wifiConectado ? HIGH : LOW);
}

// ---------------------------------------------------------------------------
// Leitura e processamento dos sensores
// ---------------------------------------------------------------------------

Leitura lerSensores() {
  Leitura l;
  l.seq = ++seq;
  l.tempoS = millis() / 1000;

  l.temperatura = dht.readTemperature();
  l.umidade = dht.readHumidity();

  // Potenciômetro 0..4095 mapeado para 30..200 BPM. Representa a saída já
  // processada de um sensor de pulso (ex.: MAX30102), que o Wokwi não tem.
  l.bpm = map(analogRead(PINO_PULSO), 0, 4095, 30, 200);

  // Módulo da aceleração em g. Parado = ~1 g (só a gravidade).
  l.acelG = 1.0;
  if (mpuDisponivel) {
    sensors_event_t a, g, t;
    mpu.getEvent(&a, &g, &t);
    l.acelG = sqrt(a.acceleration.x * a.acceleration.x +
                   a.acceleration.y * a.acceleration.y +
                   a.acceleration.z * a.acceleration.z) / SENSORS_GRAVITY_STANDARD;
  }
  if (l.acelG >= ACEL_QUEDA_G)                         l.movimento = "queda";
  else if (fabs(l.acelG - 1.0) > ACEL_DESVIO_ATIVO_G)  l.movimento = "atividade";
  else                                                 l.movimento = "repouso";

  // Regras de alerta. A FC é avaliada no contexto do movimento: 140 BPM
  // correndo é normal, 140 BPM deitado não é. Isso evita falso alarme sem
  // depender da nuvem para decidir.
  l.motivo = "";
  int bpmMax = strcmp(l.movimento, "atividade") == 0 ? BPM_MAX_ATIVIDADE : BPM_MAX_REPOUSO;
  if (l.bpm < BPM_MIN)               l.motivo += "bradicardia ";
  if (l.bpm > bpmMax)                l.motivo += "taquicardia ";
  if (isnan(l.temperatura))          l.motivo += "falha_DHT22 ";
  else if (l.temperatura >= TEMP_FEBRE)      l.motivo += "febre ";
  else if (l.temperatura <= TEMP_HIPOTERMIA) l.motivo += "hipotermia ";
  if (strcmp(l.movimento, "queda") == 0)     l.motivo += "queda ";
  l.alerta = l.motivo.length() > 0;

  return l;
}

void imprimirLeitura(const Leitura &l) {
  Serial.printf("[LEITURA #%lu] %.1f C | %.1f %% | %d BPM | %.2f g (%s)%s%s\n",
                l.seq, l.temperatura, l.umidade, l.bpm, l.acelG, l.movimento,
                l.alerta ? " | ALERTA: " : "", l.motivo.c_str());
}

// ---------------------------------------------------------------------------
// Setup e loop
// ---------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  pinMode(PINO_WIFI, INPUT);
  pinMode(PINO_LED_ONLINE, OUTPUT);
  pinMode(PINO_LED_ALERTA, OUTPUT);

  dht.begin();
  Wire.begin(21, 22);
  mpuDisponivel = mpu.begin();
  if (mpuDisponivel) mpu.setAccelerometerRange(MPU6050_RANGE_8_G);

  // true = formata a partição se ela ainda não existir (primeiro boot)
  if (!SPIFFS.begin(true)) {
    Serial.println("[ERRO] SPIFFS indisponível. Sem buffer local, o dispositivo não é seguro para uso offline.");
    while (true) delay(1000);
  }
  garantirArquivo();
  registrosNoBuffer = contarRegistros();

  Serial.println();
  Serial.println("=== CardioIA Edge — monitor cardíaco vestível ===");
  Serial.printf("Modo %s | leitura a cada %lu s | buffer de até %lu registros\n",
                MODO_DEMO ? "DEMO" : "PRODUÇÃO", INTERVALO_LEITURA_MS / 1000, LIMITE_REGISTROS);
  Serial.printf("MPU6050: %s | pendentes no boot: %lu\n",
                mpuDisponivel ? "ok" : "não encontrado", registrosNoBuffer);
  Serial.println("Use a chave deslizante para ligar/desligar o Wi-Fi.");
  Serial.println(CABECALHO_CSV);
}

void loop() {
  // 1. Conectividade (a variável booleana exigida pelo enunciado)
  wifiConectado = digitalRead(PINO_WIFI) == HIGH;
  if (wifiConectado != wifiAnterior) {
    Serial.println(wifiConectado ? "[WIFI] Conectado" : "[WIFI] Desconectado: operando offline");
    wifiAnterior = wifiConectado;
  }
  digitalWrite(PINO_LED_ONLINE, wifiConectado ? HIGH : LOW);

  // 2. Coleta periódica, que nunca para, com ou sem conexão
  if (millis() - ultimaLeitura >= INTERVALO_LEITURA_MS || ultimaLeitura == 0) {
    ultimaLeitura = millis();
    Leitura l = lerSensores();
    imprimirLeitura(l);
    digitalWrite(PINO_LED_ALERTA, l.alerta ? HIGH : LOW);

    // 3. Toda leitura passa pelo buffer local antes de sair do dispositivo
    gravarLeitura(l);
    if (!wifiConectado) {
      Serial.printf("[OFFLINE] Leitura #%lu gravada no SPIFFS (%lu/%lu no buffer)\n",
                    l.seq, registrosNoBuffer, LIMITE_REGISTROS);
    }
  }

  // 4. Com conexão, esvazia o buffer
  if (wifiConectado) sincronizar();

  delay(50);
}
