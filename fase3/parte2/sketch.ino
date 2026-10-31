/*
 * CardioIA — Fase 3, Parte 2: Transmissão para a nuvem via MQTT (Fog/Cloud)
 * -------------------------------------------------------------------------
 * Evolução da Parte 1: o mesmo vestível com Edge Computing (alertas no próprio
 * ESP32 e buffer em SPIFFS), agora publicando de verdade num broker MQTT na
 * internet. O Node-RED assina os tópicos e monta a dashboard.
 *
 * Sensores:
 *   - DHT22 ........... temperatura (°C) e umidade (%)          -> GPIO 15
 *   - Botão de pulso .. cada aperto = uma batida; o ESP32 calcula o BPM
 *                       pela média dos últimos intervalos (tecla P) -> GPIO 32
 *   - MPU6050 ......... acelerômetro, detecta atividade/queda    -> I2C (SDA 21, SCL 22)
 *
 * Atuadores / controles:
 *   - Chave deslizante: liga/desliga a conexão (simula perda de sinal) -> GPIO 27
 *   - LED verde: conectado ao broker MQTT                              -> GPIO 2
 *   - LED vermelho: alerta clínico na última leitura                   -> GPIO 4
 *
 * MQTT (broker público broker.hivemq.com:1883, ver relatório sobre segurança):
 *   cardioia/fiap-rm566821/paciente01/vitais  leitura em JSON a cada intervalo
 *   cardioia/fiap-rm566821/paciente01/alerta  estado do alerta (retained)
 *   cardioia/fiap-rm566821/paciente01/status  "online" / "offline" (retained + LWT)
 *
 * Situações para testar (com a simulação rodando):
 *   Situação                Botão de pulso           DHT22     MPU6050 (Z)  Resultado
 *   ----------------------  -----------------------  --------  -----------  ----------------------
 *   Normal                  ~1 aperto por segundo    36,6 °C   1 g          sem alerta (~60-80 BPM)
 *   Taquicardia em repouso  ~2-3 apertos por segundo 36,6 °C   1 g          ALERTA: taquicardia
 *   Febre                   ritmo normal             38,6 °C   1 g          ALERTA: febre
 *   Correndo                ~2,3 apertos/s (~140)    36,6 °C   1,5 g        sem alerta (limite 150)
 *   Bradicardia             1 aperto a cada 1,5 s    36,6 °C   1 g          ALERTA: bradicardia
 *   Queda                   ritmo normal             36,6 °C   3 g          ALERTA: queda
 *   Perda de conexão        qualquer                 qualquer  qualquer     chave desligada: grava
 *                                                                           no SPIFFS; ao religar,
 *                                                                           reenvia tudo por MQTT
 *
 * Sem apertar o botão por 30 s, o BPM volta a "sem leitura" (não gera alerta).
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <time.h>
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
#define PINO_PULSO      32
#define PINO_CONEXAO    27
#define PINO_LED_ONLINE 2
#define PINO_LED_ALERTA 4

// ---------------------------------------------------------------------------
// Rede e MQTT
// ---------------------------------------------------------------------------
const char *WIFI_SSID   = "Wokwi-GUEST";   // rede com internet do simulador
const char *WIFI_SENHA  = "";
const char *MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORTA  = 1883;

// Prefixo único: o broker é público, então o RM evita colisão com outros grupos
#define TOPICO_BASE "cardioia/fiap-rm566821/paciente01"
const char *TOPICO_VITAIS = TOPICO_BASE "/vitais";
const char *TOPICO_ALERTA = TOPICO_BASE "/alerta";
const char *TOPICO_STATUS = TOPICO_BASE "/status";

const unsigned long INTERVALO_RECONEXAO_MS = 3000;

// ---------------------------------------------------------------------------
// Coleta e armazenamento (mesmo modelo da Parte 1)
// ---------------------------------------------------------------------------
#define MODO_DEMO true

#if MODO_DEMO
const unsigned long INTERVALO_LEITURA_MS = 2000;
const unsigned long LIMITE_REGISTROS = 20;
#else
const unsigned long INTERVALO_LEITURA_MS = 10000;
const unsigned long LIMITE_REGISTROS = 8640;      // 24 h offline
#endif
const unsigned long ALVO_POS_COMPACTACAO = LIMITE_REGISTROS * 3 / 4;

// Uma leitura por linha, já no formato JSON que vai para o broker
const char *ARQUIVO_FILA = "/fila.jsonl";
const char *ARQUIVO_TEMP = "/fila.tmp";

// ---------------------------------------------------------------------------
// Batimentos pelo botão de pulso
// ---------------------------------------------------------------------------
const unsigned long DEBOUNCE_PULSO_MS = 200;     // limita a 300 BPM
const unsigned long PULSO_EXPIRA_MS   = 30000;   // sem apertos: "sem leitura"
const unsigned long PAUSA_MAX_MS      = 2500;    // intervalo maior = pausa, não batida (< 24 BPM)
const int           JANELA_BATIDAS    = 6;       // média de 5 intervalos

volatile unsigned long batidas[JANELA_BATIDAS];  // instantes das últimas batidas
volatile int  proximaBatida = 0;
volatile int  totalBatidas  = 0;
volatile unsigned long ultimaBatida = 0;

// ---------------------------------------------------------------------------
// Limiares clínicos (processamento no Edge)
// ---------------------------------------------------------------------------
const int   BPM_MIN             = 50;
const int   BPM_MAX_REPOUSO     = 120;
const int   BPM_MAX_ATIVIDADE   = 150;
const float TEMP_FEBRE          = 37.8;
const float TEMP_HIPOTERMIA     = 35.0;
const float ACEL_DESVIO_ATIVO_G = 0.3;
const float ACEL_QUEDA_G        = 2.5;

// ---------------------------------------------------------------------------
// Estado global
// ---------------------------------------------------------------------------
DHT dht(PINO_DHT, DHT22);
Adafruit_MPU6050 mpu;
bool mpuDisponivel = false;

WiFiClient wifiCliente;
PubSubClient mqtt(wifiCliente);
char mqttClientId[40];

bool conexaoHabilitada = false;   // a chave: simula o paciente sair da área de sinal
bool conexaoAnterior   = false;
unsigned long ultimaTentativaMqtt = 0;

unsigned long seq = 0;
unsigned long registrosNaFila = 0;
unsigned long ultimaLeitura = 0;
bool alertaAnterior = false;
bool alertaPendente = false;   // estado do alerta ainda não publicado (ex.: mudou offline)

struct Leitura {
  unsigned long seq;
  time_t ts;                 // horário real (NTP), em segundos
  float temperatura;
  float umidade;
  int bpm;                   // 0 = sem leitura de pulso
  float acelG;
  const char *movimento;
  bool alerta;
  String motivo;
};

// ---------------------------------------------------------------------------
// Botão de pulso (interrupção)
// ---------------------------------------------------------------------------

// Roda a cada aperto. Guarda o instante num anel; o debounce descarta o
// "repique" mecânico do botão, que senão contaria várias batidas por aperto.
void IRAM_ATTR aoBater() {
  unsigned long agora = millis();
  if (agora - ultimaBatida < DEBOUNCE_PULSO_MS) return;
  // Depois de uma pausa, recomeça a medição: senão o intervalo da pausa entra
  // na média e o BPM despenca (bradicardia falsa).
  if (agora - ultimaBatida > PAUSA_MAX_MS) totalBatidas = 0;
  ultimaBatida = agora;
  batidas[proximaBatida] = agora;
  proximaBatida = (proximaBatida + 1) % JANELA_BATIDAS;
  if (totalBatidas < JANELA_BATIDAS) totalBatidas = totalBatidas + 1;
}

// BPM = 60.000 / média dos intervalos entre as últimas batidas.
int calcularBpm() {
  noInterrupts();
  int n = totalBatidas;
  int prox = proximaBatida;
  unsigned long ultima = ultimaBatida;
  unsigned long copia[JANELA_BATIDAS];
  for (int i = 0; i < JANELA_BATIDAS; i++) copia[i] = batidas[i];
  interrupts();

  if (n < 2 || millis() - ultima > PULSO_EXPIRA_MS) return 0;
  int maisNova = (prox - 1 + JANELA_BATIDAS) % JANELA_BATIDAS;
  int maisAntiga = (prox - n + JANELA_BATIDAS) % JANELA_BATIDAS;
  unsigned long media = (copia[maisNova] - copia[maisAntiga]) / (n - 1);
  return media > 0 ? 60000 / media : 0;
}

// ---------------------------------------------------------------------------
// Fila local (SPIFFS): store-and-forward
// ---------------------------------------------------------------------------

String lerLinha(File &f) {
  String linha = f.readStringUntil('\n');
  linha.trim();
  return linha;
}

unsigned long contarRegistros() {
  File f = SPIFFS.open(ARQUIVO_FILA, FILE_READ);
  if (!f) return 0;
  unsigned long n = 0;
  while (f.available()) {
    if (lerLinha(f).length() > 0) n++;
  }
  f.close();
  return n;
}

bool linhaTemAlerta(const String &linha) {
  return linha.indexOf("\"alerta\":1") >= 0;
}

// Mesma estratégia da Parte 1: mantém todos os alertas e metade das leituras
// normais; só descarta as mais antigas se ainda assim não couber.
void compactarFila() {
  Serial.printf("[EDGE] Fila cheia (%lu/%lu). Compactando...\n", registrosNaFila, LIMITE_REGISTROS);

  File origem = SPIFFS.open(ARQUIVO_FILA, FILE_READ);
  File destino = SPIFFS.open(ARQUIVO_TEMP, FILE_WRITE);
  unsigned long mantidos = 0, normais = 0;
  while (origem.available()) {
    String linha = lerLinha(origem);
    if (linha.length() == 0) continue;
    if (linhaTemAlerta(linha) || (normais++ % 2 == 0)) {
      destino.println(linha);
      mantidos++;
    }
  }
  origem.close();
  destino.close();
  SPIFFS.remove(ARQUIVO_FILA);
  SPIFFS.rename(ARQUIVO_TEMP, ARQUIVO_FILA);
  Serial.printf("[EDGE] Decimação: %lu -> %lu registros (alertas preservados)\n", registrosNaFila, mantidos);
  registrosNaFila = mantidos;

  if (registrosNaFila > ALVO_POS_COMPACTACAO) {
    unsigned long descartar = registrosNaFila - ALVO_POS_COMPACTACAO;
    origem = SPIFFS.open(ARQUIVO_FILA, FILE_READ);
    destino = SPIFFS.open(ARQUIVO_TEMP, FILE_WRITE);
    unsigned long i = 0;
    while (origem.available()) {
      String linha = lerLinha(origem);
      if (linha.length() == 0) continue;
      if (i++ >= descartar) destino.println(linha);
    }
    origem.close();
    destino.close();
    SPIFFS.remove(ARQUIVO_FILA);
    SPIFFS.rename(ARQUIVO_TEMP, ARQUIVO_FILA);
    registrosNaFila -= descartar;
    Serial.printf("[EDGE] Ainda acima do alvo: %lu registros mais antigos descartados\n", descartar);
  }
}

void enfileirar(const char *json) {
  if (registrosNaFila >= LIMITE_REGISTROS) compactarFila();
  File f = SPIFFS.open(ARQUIVO_FILA, FILE_APPEND);
  f.println(json);
  f.close();
  registrosNaFila++;
}

bool online() {
  return conexaoHabilitada && WiFi.status() == WL_CONNECTED && mqtt.connected();
}

// Publica a fila em ordem. Se a conexão cair no meio, o que não saiu volta
// para um arquivo novo; nada se perde nem é publicado duas vezes. O número
// de série (seq) permite à nuvem descartar repetidos se o ESP32 reiniciar.
void descarregarFila() {
  if (registrosNaFila == 0) return;
  bool lote = registrosNaFila > 1;
  if (lote) Serial.printf("[SYNC] Reenviando %lu leitura(s) guardada(s) offline...\n", registrosNaFila);

  File origem = SPIFFS.open(ARQUIVO_FILA, FILE_READ);
  unsigned long enviados = 0;
  bool interrompido = false;
  File restante;

  while (origem.available()) {
    String linha = lerLinha(origem);
    if (linha.length() == 0) continue;

    if (!interrompido) {
      conexaoHabilitada = digitalRead(PINO_CONEXAO) == HIGH;
      mqtt.loop();
      if (online() && mqtt.publish(TOPICO_VITAIS, linha.c_str())) {
        Serial.print("[MQTT] -> vitais ");
        Serial.println(linha);
        enviados++;
        continue;
      }
      interrompido = true;
      restante = SPIFFS.open(ARQUIVO_TEMP, FILE_WRITE);
    }
    restante.println(linha);
  }
  origem.close();

  SPIFFS.remove(ARQUIVO_FILA);
  if (interrompido) {
    restante.close();
    SPIFFS.rename(ARQUIVO_TEMP, ARQUIVO_FILA);
    registrosNaFila -= enviados;
    Serial.printf("[SYNC] Conexão perdida: %lu publicada(s), %lu continuam na fila\n", enviados, registrosNaFila);
  } else {
    registrosNaFila = 0;
    if (lote) Serial.printf("[SYNC] Concluído: %lu leitura(s) publicada(s), fila local apagada\n", enviados);
  }
}

// ---------------------------------------------------------------------------
// Conexão
// ---------------------------------------------------------------------------

// Antes do NTP responder, time() devolve segundos desde o boot (1970).
bool horarioValido() {
  return time(nullptr) > 1700000000;
}

void conectarWifi() {
  Serial.printf("[WIFI] Conectando a %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_SENHA, 6);
  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 15000) {
    delay(250);
    Serial.print(".");
  }
  Serial.println(WiFi.status() == WL_CONNECTED ? " ok" : " falhou (segue offline)");

  // Horário real para o carimbo de cada leitura (fuso de Brasília). Espera
  // o primeiro acerto do relógio, senão as leituras iniciais saem datadas de 1970.
  configTime(-3 * 3600, 0, "pool.ntp.org", "time.google.com");
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[NTP] Acertando o relógio");
    inicio = millis();
    while (!horarioValido() && millis() - inicio < 10000) {
      delay(250);
      Serial.print(".");
    }
    Serial.println(horarioValido() ? " ok" : " sem resposta (usa horário de chegada)");
  }
}

// Publica o estado do alerta com retain: quem abrir a dashboard depois vê na
// hora se o paciente está em alerta, sem esperar a próxima leitura.
void publicarAlerta(const Leitura &l) {
  char json[160];
  snprintf(json, sizeof(json), "{\"ativo\":%s,\"motivo\":\"%s\",\"bpm\":%d,\"temp\":%.1f,\"ts\":%ld}",
           l.alerta ? "true" : "false", l.motivo.c_str(), l.bpm, l.temperatura, (long)l.ts);
  if (online()) mqtt.publish(TOPICO_ALERTA, json, true);
}

void tentarMqtt() {
  if (mqtt.connected() || millis() - ultimaTentativaMqtt < INTERVALO_RECONEXAO_MS) return;
  ultimaTentativaMqtt = millis();
  if (WiFi.status() != WL_CONNECTED) WiFi.reconnect();

  // Last Will: se o ESP32 sumir sem avisar, o próprio broker publica "offline"
  if (mqtt.connect(mqttClientId, TOPICO_STATUS, 1, true, "offline")) {
    mqtt.publish(TOPICO_STATUS, "online", true);
    alertaPendente = true;   // reconectou: republica o estado atual do alerta
    Serial.printf("[MQTT] Conectado a %s como %s\n", MQTT_BROKER, mqttClientId);
  } else {
    Serial.printf("[MQTT] Falha ao conectar (estado %d), nova tentativa em %lu s\n",
                  mqtt.state(), INTERVALO_RECONEXAO_MS / 1000);
  }
}

// ---------------------------------------------------------------------------
// Leitura e processamento dos sensores
// ---------------------------------------------------------------------------

Leitura lerSensores() {
  Leitura l;
  l.seq = ++seq;
  l.ts = horarioValido() ? time(nullptr) : 0;   // 0 = sem horário: a nuvem usa o de chegada
  l.temperatura = dht.readTemperature();
  l.umidade = dht.readHumidity();
  l.bpm = calcularBpm();

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

  // Mesmas regras da Parte 1. Sem leitura de pulso (bpm = 0), a FC não é
  // avaliada: falta de dado não é bradicardia.
  l.motivo = "";
  int bpmMax = strcmp(l.movimento, "atividade") == 0 ? BPM_MAX_ATIVIDADE : BPM_MAX_REPOUSO;
  if (l.bpm > 0 && l.bpm < BPM_MIN)  l.motivo += "bradicardia ";
  if (l.bpm > bpmMax)                l.motivo += "taquicardia ";
  if (isnan(l.temperatura))          l.motivo += "falha_DHT22 ";
  else if (l.temperatura >= TEMP_FEBRE)      l.motivo += "febre ";
  else if (l.temperatura <= TEMP_HIPOTERMIA) l.motivo += "hipotermia ";
  if (strcmp(l.movimento, "queda") == 0)     l.motivo += "queda ";
  l.motivo.trim();
  l.alerta = l.motivo.length() > 0;
  return l;
}

void paraJson(const Leitura &l, char *json, size_t tam) {
  snprintf(json, tam,
           "{\"seq\":%lu,\"ts\":%ld,\"temp\":%.1f,\"umid\":%.1f,\"bpm\":%d,"
           "\"acel\":%.2f,\"mov\":\"%s\",\"alerta\":%d,\"motivo\":\"%s\"}",
           l.seq, (long)l.ts, l.temperatura, l.umidade, l.bpm, l.acelG,
           l.movimento, l.alerta ? 1 : 0, l.motivo.c_str());
}

void imprimirLeitura(const Leitura &l) {
  char bpm[16];
  if (l.bpm > 0) snprintf(bpm, sizeof(bpm), "%d BPM", l.bpm);
  else           snprintf(bpm, sizeof(bpm), "-- BPM");
  Serial.printf("[LEITURA #%lu] %.1f C | %.1f %% | %s | %.2f g (%s)%s%s\n",
                l.seq, l.temperatura, l.umidade, bpm, l.acelG, l.movimento,
                l.alerta ? " | ALERTA: " : "", l.motivo.c_str());
}

// ---------------------------------------------------------------------------
// Setup e loop
// ---------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  pinMode(PINO_CONEXAO, INPUT);
  pinMode(PINO_LED_ONLINE, OUTPUT);
  pinMode(PINO_LED_ALERTA, OUTPUT);
  pinMode(PINO_PULSO, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PINO_PULSO), aoBater, FALLING);

  dht.begin();
  Wire.begin(21, 22);
  mpuDisponivel = mpu.begin();
  if (mpuDisponivel) mpu.setAccelerometerRange(MPU6050_RANGE_8_G);

  if (!SPIFFS.begin(true)) {
    Serial.println("[ERRO] SPIFFS indisponível. Sem fila local, o dispositivo não é seguro para uso offline.");
    while (true) delay(1000);
  }
  registrosNaFila = contarRegistros();

  Serial.println();
  Serial.println("=== CardioIA — vestível conectado (MQTT) ===");
  Serial.printf("Modo %s | leitura a cada %lu s | fila de até %lu registros\n",
                MODO_DEMO ? "DEMO" : "PRODUÇÃO", INTERVALO_LEITURA_MS / 1000, LIMITE_REGISTROS);
  Serial.println("Aperte o botão de pulso (ou a tecla P) no ritmo do coração.");

  conectarWifi();
  snprintf(mqttClientId, sizeof(mqttClientId), "cardioia-%08lx", (unsigned long)esp_random());
  mqtt.setServer(MQTT_BROKER, MQTT_PORTA);
  mqtt.setBufferSize(512);
  mqtt.setKeepAlive(15);
}

void loop() {
  // 1. Conexão: a chave simula o paciente sair da área de sinal
  conexaoHabilitada = digitalRead(PINO_CONEXAO) == HIGH;
  if (conexaoHabilitada != conexaoAnterior) {
    if (!conexaoHabilitada && mqtt.connected()) {
      mqtt.publish(TOPICO_STATUS, "offline", true);   // saída "educada" avisa a dashboard
      mqtt.disconnect();
    }
    Serial.println(conexaoHabilitada ? "[REDE] Conexão habilitada" : "[REDE] Sem conexão: operando offline");
    conexaoAnterior = conexaoHabilitada;
  }
  if (conexaoHabilitada) {
    tentarMqtt();
    mqtt.loop();
  }
  digitalWrite(PINO_LED_ONLINE, online() ? HIGH : LOW);

  // 2. Coleta periódica, com ou sem conexão
  if (millis() - ultimaLeitura >= INTERVALO_LEITURA_MS || ultimaLeitura == 0) {
    ultimaLeitura = millis();
    Leitura l = lerSensores();
    imprimirLeitura(l);
    digitalWrite(PINO_LED_ALERTA, l.alerta ? HIGH : LOW);

    // 3. Toda leitura entra na fila; online, a fila é publicada na hora
    char json[220];
    paraJson(l, json, sizeof(json));
    enfileirar(json);
    if (!online()) {
      Serial.printf("[OFFLINE] Leitura #%lu guardada no SPIFFS (%lu/%lu na fila)\n",
                    l.seq, registrosNaFila, LIMITE_REGISTROS);
    }

    if (l.alerta != alertaAnterior || alertaPendente) {
      publicarAlerta(l);
      alertaAnterior = l.alerta;
      alertaPendente = !online();
    }
  }

  // 4. Com conexão, esvazia a fila
  if (online()) descarregarFila();

  delay(20);
}
