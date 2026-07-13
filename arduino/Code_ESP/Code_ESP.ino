/**
Pour transférer le code sur le ESP8266 :
 - brancher l'ESP8266 dans le slot bleu, orienté vers l'extérieur de la carte,
 - orienter l'interrupteur vers l'ESP8266,
 - appuyer sur le bouton poussoir,
 - transférer le code,
 - relacher le bouton pression quand la console affiche Connecting....
*/

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

#ifndef STASSID
#define STASSID "CLAMAISON"
#define STAPSK  "MOTDEPASSEDUWIFI"
#endif

// IMPORTANT : ce mot de passe WiFi est en clair dans ce fichier .ino.
// Comme il a été partagé dans cette session, pense a le changer une fois
// ce code deploye, comme n'importe quel secret qui a transite en clair.

const char* SERVER_URL = "http://192.168.1.6/jardin.php";
unsigned long lastWifiCheck = 0;

void connectWifi() {
  Serial.print("Connexion WiFi");
  WiFi.begin(STASSID, STAPSK);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.print("Connecté ! IP : ");
    Serial.println(WiFi.localIP());
    digitalWrite(LED_BUILTIN, LOW);
  } else {
    Serial.println("");
    Serial.println("Echec de connexion WiFi, nouvelle tentative au prochain envoi.");
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.println();
  connectWifi();
}

void loop() {
  // Robustesse : si le WiFi tombe, on retente régulièrement plutôt que de rester bloqué
  if (WiFi.status() != WL_CONNECTED && millis() - lastWifiCheck > 10000) {
    lastWifiCheck = millis();
    connectWifi();
  }

  if (Serial.available() > 0) {
    String httpRequestData = Serial.readString();

    if (WiFi.status() == WL_CONNECTED) {
      WiFiClient client;
      HTTPClient http;

      http.setTimeout(5000); // évite de rester bloqué indéfiniment si le serveur ne répond pas
      http.begin(client, SERVER_URL);
      http.addHeader("Content-Type", "application/x-www-form-urlencoded");

      int httpCode = http.POST(httpRequestData);

      if (httpCode > 0) {
        String payload = http.getString();
        Serial.println(payload);
      } else {
        Serial.print("Error code: ");
        Serial.println(httpCode);
        // On renvoie un statut neutre pour que l'Arduino ne reste pas bloqué en attente
        Serial.println("0,ESP_HTTP_ERROR");
      }
      http.end();
    } else {
      Serial.println("0,WIFI_DOWN");
    }
  }
}
