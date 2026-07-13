#include <SoftwareSerial.h>
#include <DS3231.h>
#include <Wire.h>
#include <DHT.h>

// ---------------------------------------------------------------
//  parametrage des pins carte
// ---------------------------------------------------------------
int trigPin = 10;
int echoPin = 11;
int dhtpin = 4;
int relay_led_pin = 13;
int relay_pin = 12;
int SerialESP8266RXpin = 9;
int SerialESP8266TXpin = 8;
int alarme_pin = 2;

volatile byte tick = 0;
byte alarmDay;
byte alarmHour;
byte alarmMinute;
byte alarmSecond;
byte alarmBits;
bool alarmDayIsDay;
bool alarmH12;
bool alarmPM;
bool century = false;
bool h12Flag = false;
bool pmFlag;

SoftwareSerial SerialESP8266(SerialESP8266RXpin, SerialESP8266TXpin);
DS3231  rtc;
DHT dht(dhtpin, DHT22);

long duree; // durée de l'echo

// ---------------------------------------------------------------
//  configuration des variables
// ---------------------------------------------------------------
int lastrecord;                            // temps du dernier enregistrement
int deltarecord = 5 * 60;                  // durée entre deux enregistrements en secondes
int lastpoll;                              // temps du dernier sondage de commande
int deltapoll = 10;                        // durée entre deux sondages en secondes
unsigned long wateringduration = 2 * 60;   // durée par défaut d'un arrosage en secondes
unsigned long maxwateringduration = 10 * 60; // sécurité absolue : jamais plus de 10 min d'arrosage
unsigned long timerwatering = 0;
bool watering = false;

// File d'attente d'un evenement d'arrosage a signaler au serveur
// (pour l'historique affiche sur le site)
bool logPending = false;
unsigned long logDuree = 0;
String logSource = "";

int TerreBlanc;
int TerreNoir;
int TerreBlancd;
int TerreNoird;
float AirHumidite;
float AirTemperature;
float Distance;
int heures, minutes, secondes, jour, mois, annees;

// ---------------------------------------------------------------
// Récupération des données
// ---------------------------------------------------------------
String getValue(String data, char separator, int index)
{
    int found = 0;
    int strIndex[] = { 0, -1 };
    int maxIndex = data.length() - 1;
    for (int i = 0; i <= maxIndex && found <= index; i++) {
        if (data.charAt(i) == separator || i == maxIndex) {
            found++;
            strIndex[0] = strIndex[1] + 1;
            strIndex[1] = (i == maxIndex) ? i + 1 : i;
        }
    }
    return found > index ? data.substring(strIndex[0], strIndex[1]) : "";
}

// Démarre l'arrosage pour une durée donnée (en secondes), avec garde-fou.
// source = "programme" (alarme RTC) ou "web" (bouton sur le site)
void startWatering(unsigned long dureeSec, String source)
{
    if (dureeSec == 0 || dureeSec > maxwateringduration) {
        dureeSec = wateringduration;
    }
    Serial.print("Arrosage declenche (");
    Serial.print(source);
    Serial.print(") pour ");
    Serial.print(dureeSec);
    Serial.print("s a ");
    showTime();
    digitalWrite(relay_led_pin, HIGH);
    digitalWrite(relay_pin, HIGH);
    watering = true;
    timerwatering = millis() + dureeSec * 1000UL;

    // On demande au prochain tour de loop() d'envoyer cet evenement au
    // serveur pour l'historique (voir bloc d'envoi dans loop())
    logPending = true;
    logDuree = dureeSec;
    logSource = source;
}

void stopWatering()
{
    digitalWrite(relay_led_pin, LOW);
    digitalWrite(relay_pin, LOW);
    watering = false;
}

// ---------------------------------------------------------------
// Configuration de la carte en fonction du retour serveur
// codes : 1=ok / 2=erreur / 3=reglage heure / 4=cle api invalide
//         5=ordre d'arrosage a distance (bouton web), suivi de la duree en s
// ---------------------------------------------------------------
void set_param(String input)
{
    String status = getValue(input, ',', 0);
    if (status == "1") {
        Serial.println("Record ok");
    }
    else if (status == "4") {
        Serial.println("Key error");
    }
    else if (status == "2") {
        Serial.println("Error Record");
        Serial.println(getValue(input, ',', 1));
    }
    else if (status == "5") {
        // Ordre d'arrosage envoye depuis l'interface web (bouton)
        unsigned long d = (unsigned long) getValue(input, ',', 1).toInt();
        startWatering(d, "web");
    }
    else if (status == "3") {
        Serial.println("Réglage heure");
        String phptime = getValue(input, ',', 1);
        String jour = getValue(phptime, ' ', 0);
        if (jour.toInt() == 0) {
            rtc.setDoW(7);
        } else {
            rtc.setDoW(jour.toInt());
        }
        String datej = getValue(phptime, ' ', 1);
        String datem = getValue(phptime, ' ', 2);
        String datey = getValue(phptime, ' ', 3).substring(2, 4);
        String heureh = getValue(phptime, ' ', 4);
        String heurem = getValue(phptime, ' ', 5);
        String heures = getValue(phptime, ' ', 6);
        if (heures == "") {
            Serial.println("Erreur");
        } else {
            rtc.setClockMode(h12Flag);
            rtc.setDate(datej.toInt());
            rtc.setMonth(datem.toInt());
            rtc.setYear(datey.toInt());
            rtc.setHour(heureh.toInt());
            rtc.setMinute(heurem.toInt());
            rtc.setSecond(heures.toInt());
            Serial.println("Heure réglée");
        }
    }
    // status "0" = rien a faire (reponse a un sondage sans ordre en attente)
}

int TimeNow()
{
    heures = rtc.getHour(h12Flag, pmFlag);
    minutes = rtc.getMinute();
    secondes = rtc.getSecond();
    jour = rtc.getDate();
    mois = rtc.getMonth(century);
    annees = rtc.getYear();
    return ((((12 * annees + mois) * 30 + jour) * 24 + heures) * 60 + minutes) * 60 + secondes;
}

void showTime()
{
    heures = rtc.getHour(h12Flag, pmFlag);
    minutes = rtc.getMinute();
    secondes = rtc.getSecond();
    jour = rtc.getDate();
    mois = rtc.getMonth(century);
    annees = rtc.getYear();
    Serial.print("showtime ");
    Serial.print(jour, DEC); Serial.print("/");
    Serial.print(mois, DEC); Serial.print("/");
    Serial.print(annees, DEC); Serial.print(" ");
    Serial.print(heures, DEC); Serial.print(":");
    Serial.print(minutes, DEC); Serial.print(":");
    Serial.println(secondes, DEC);
}

void showData()
{
    Serial.print("AirTemperature="); Serial.print(AirTemperature);
    Serial.print(", AirHumidite="); Serial.print(AirHumidite);
    Serial.print(", Distance="); Serial.print(Distance);
    Serial.print(", TerreNoir="); Serial.print(TerreNoir);
    Serial.print(", TerreBlanc="); Serial.println(TerreBlanc);
}

void setup() {
    Wire.begin();
    dht.begin();
    Serial.begin(9600);
    while (!Serial);

    alarmDay = rtc.getDate();
    alarmH12 = false;
    alarmHour = 20;
    alarmMinute = 0;
    alarmSecond = 0;
    alarmBits = 0b00001000;
    alarmDayIsDay = false;

    rtc.turnOffAlarm(1);
    rtc.setA1Time(alarmDay, alarmHour, alarmMinute, alarmSecond, alarmBits, alarmDayIsDay, alarmH12, alarmPM);
    rtc.checkIfAlarm(1);
    rtc.turnOnAlarm(1);

    alarmMinute = 0xFF;
    alarmBits = 0b01100000;
    rtc.setA2Time(alarmDay, alarmHour, alarmMinute, alarmBits, alarmDayIsDay, alarmH12, alarmPM);
    rtc.turnOffAlarm(2);
    rtc.checkIfAlarm(2);

    SerialESP8266.begin(9600);
    pinMode(relay_pin, OUTPUT);
    pinMode(relay_led_pin, OUTPUT);
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);
    stopWatering(); // etat sur connu au demarrage (relais coupe)

    lastrecord = TimeNow();
    lastpoll = TimeNow();
    SerialESP8266.setTimeout(250);
    delay(1000);

    pinMode(alarme_pin, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(alarme_pin), isr_TickTock, FALLING);
}

void loop() {
    // Lecture des capteurs
    TerreBlanc = analogRead(A1);
    TerreNoir = analogRead(A2);
    TerreBlancd = digitalRead(6);
    TerreNoird = digitalRead(7);
    AirHumidite = dht.readHumidity();
    AirTemperature = dht.readTemperature();
    // Le DHT22 renvoie parfois NaN en cas de glitch : on garde la derniere
    // valeur valide plutot que d'envoyer une lecture aberrante au serveur
    if (isnan(AirHumidite))    AirHumidite = -1;
    if (isnan(AirTemperature)) AirTemperature = -99;

    digitalWrite(trigPin, LOW);
    delayMicroseconds(5);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    duree = pulseIn(echoPin, HIGH);
    Distance = duree * 0.034 / 2;

    // Arrosage programme (alarme RTC quotidienne)
    if (tick) {
        rtc.turnOffAlarm(1);
        rtc.checkIfAlarm(1);
        rtc.turnOnAlarm(1);
        tick = 0;
        startWatering(wateringduration, "programme");
    }

    // Coupure de l'arrosage en cours (programme OU a distance) + garde-fou
    if (watering && millis() > timerwatering) {
        stopWatering();
    }

    // Priorité : signaler un arrosage qui vient de démarrer, pour l'historique web
    if (logPending) {
        SerialESP8266.println("api_key=tPmAT5Ab&arrosage_event=1&Duree=" + String(logDuree) +
                               "&Source=" + logSource);
        Serial.println("Log arrosage envoye");
        logPending = false;
    }
    // Envoi périodique des mesures
    else if (TimeNow() - lastrecord > deltarecord) {
        SerialESP8266.println("api_key=tPmAT5Ab&Heure=0&Temp=" + String(AirTemperature) +
                               "&Hum=" + String(AirHumidite) +
                               "&Dist=" + String(Distance) +
                               "&TNoir=" + String(TerreNoir) +
                               "&TBlanc=" + String(TerreBlanc));
        Serial.println("Data Sent");
        lastrecord = TimeNow();
    }
    // Sondage régulier : y a-t-il un ordre d'arrosage venant du bouton web ?
    else if (TimeNow() - lastpoll > deltapoll) {
        SerialESP8266.println("api_key=tPmAT5Ab&poll=1");
        lastpoll = TimeNow();
    }

    if (Serial.available() > 0) {
        String incomingByte = Serial.readStringUntil('\n');
        if (incomingByte == "heure") {
            SerialESP8266.println("api_key=tPmAT5Ab&Heure=1&Temp=" + String(AirTemperature) +
                                   "&Hum=" + String(AirHumidite) +
                                   "&Dist=" + String(Distance) +
                                   "&TNoir=" + String(TerreNoir) +
                                   "&TBlanc=" + String(TerreBlanc));
            Serial.println("Demande Réglage heure");
        }
        else if (incomingByte == "on") {
            startWatering(wateringduration, "test_serie");
        }
    }

    if (SerialESP8266.available() > 0) {
        String input = SerialESP8266.readString();
        Serial.println(input);
        set_param(input);
    }
    delay(1000);
}

void isr_TickTock() {
    tick = 1;
    return;
}
