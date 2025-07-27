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
#define STAPSK "ZLC*j}=10K,s2mLB;J+34Zo8.<x>yKrn0YGkDbO?SdTs4,o*nL,-d*P-+Xh=?GU"
#endif


void setup() {

  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);  // Initialize the LED_BUILTIN pin as an output
  Serial.println();
  Serial.println();
  Serial.println();

  WiFi.begin(STASSID, STAPSK);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected! IP address: ");
  Serial.println(WiFi.localIP());
  digitalWrite(LED_BUILTIN, LOW);  // Turn the LED on (Note that LOW is the voltage level

}

void loop() {
  if (Serial.available() > 0) {
    // read the incoming byte:
    String httpRequestData = Serial.readString();

  // wait for WiFi connection
  if ((WiFi.status() == WL_CONNECTED)) {

    WiFiClient client;
    HTTPClient http;

//    Serial.print("[HTTP] begin...\n");
    // configure traged server and url
    http.begin(client, "http://192.168.1.6/jardin.php");  // HTTP
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");

 //   Serial.print("[HTTP] POST...\n");
    // start connection and send HTTP header and body
    int httpCode = http.POST(httpRequestData);

    // httpCode will be negative on error
       if (httpCode>0) {
//        Serial.print("HTTP Response code: ");
//        Serial.println(httpCode);
        String payload = http.getString();
        Serial.println(payload);
      }
      else {
        Serial.print("Error code: ");
        Serial.println(httpCode);
      }
      // Free resources
      http.end();
  }

  }
}
