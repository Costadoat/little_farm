#include <SoftwareSerial.h>
#include <DS3231.h>
#include <Wire.h>
#include <DHT.h>

// ---------------------------------------------------------------
//  parametrage des pins carte (byte suffit : valeurs 0-19 max)
// ---------------------------------------------------------------
const byte trigPin = 10;
const byte echoPin = 11;
const byte dhtpin = 4;
const byte relay_led_pin = 13;
const byte relay_pin = 12;
const byte SerialESP8266RXpin = 9;
const byte SerialESP8266TXpin = 8;
const byte alarme_pin = 2;

const char* API_KEY = "tPmAT5Ab";

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

unsigned long duree; // durée de l'echo (pulseIn renvoie un unsigned long)

// ---------------------------------------------------------------
//  configuration des variables
// ---------------------------------------------------------------
int lastrecord;                    // temps du dernier enregistrement (cumul TimeNow(), doit rester int)
int deltarecord = 5 * 60;          // durée entre deux enregistrements en secondes
int lastpoll;                      // temps du dernier sondage de commande
byte deltapoll = 10;               // durée entre deux sondages en secondes (< 255, byte suffit)
unsigned int wateringduration = 2 * 60;    // durée par défaut d'un arrosage en secondes
unsigned int maxwateringduration = 10 * 60; // sécurité absolue : jamais plus de 10 min d'arrosage
unsigned long timerwatering = 0;
bool watering = false;

// File d'attente d'un evenement d'arrosage a signaler au serveur (historique web)
bool logPending = false;
unsigned int logDuree = 0;
const char* logSource = "";

// Heure d'arrosage programme actuellement appliquee sur le RTC
// (255 = valeur impossible, force la synchro au premier sondage recu)
byte currentSchedHour = 255;
byte currentSchedMinute = 255;
bool firedThisMinute = false; // evite de redeclencher plusieurs fois dans la meme minute

int TerreBlanc;   // analogRead : 0-1023, ne tient pas dans un byte
int TerreNoir;    // idem
byte TerreBlancd; // digitalRead : 0 ou 1
byte TerreNoird;  // idem
float AirHumidite;
float AirTemperature;
float Distance;
byte heures, minutes, secondes, jour, mois, annees; // la lib DS3231 renvoie deja des byte

// buffers reutilises, taille au plus juste des messages reellement envoyes/recus
char outBuf[110];
char inBuf[80];

// ---------------------------------------------------------------
// Extrait le N-ieme champ d'une chaine C separee par "sep", sans allocation.
// Retourne true si le champ existe, et le copie (tronque si besoin) dans out.
// ---------------------------------------------------------------
bool getToken(const char* data, char sep, byte index, char* out, byte outSize)
{
    byte found = 0;
    const char* start = data;
    const char* p = data;
    while (true) {
        if (*p == sep || *p == '\0') {
            if (found == index) {
                byte len = (byte)(p - start);
                if (len >= outSize) len = outSize - 1;
                memcpy(out, start, len);
                out[len] = '\0';
                return true;
            }
            found++;
            start = p + 1;
            if (*p == '\0') break;
        }
        p++;
    }
    out[0] = '\0';
    return false;
}

// Applique une nouvelle heure d'arrosage programme sur l'alarme du RTC,
// seulement si elle a change (evite des ecritures I2C inutiles)
void applySchedule(byte h, byte m)
{
    if (h > 23 || m > 59) return; // valeur invalide recue, on ignore
    if (h == currentSchedHour && m == currentSchedMinute) return; // deja a jour

    rtc.turnOffAlarm(1);
    rtc.setA1Time(alarmDay, h, m, 0, alarmBits, alarmDayIsDay, alarmH12, alarmPM);
    rtc.checkIfAlarm(1);
    rtc.turnOnAlarm(1);

    currentSchedHour = h;
    currentSchedMinute = m;

    Serial.print(F("Heure d'arrosage programmee mise a jour : "));
    Serial.print(h);
    Serial.print(F("h"));
    if (m < 10) Serial.print(F("0"));
    Serial.println(m);
}

// Démarre l'arrosage pour une durée donnée (en secondes), avec garde-fou.
// source = "programme" (alarme RTC) ou "web" (bouton sur le site)
void startWatering(unsigned int dureeSec, const char* source)
{
    if (dureeSec == 0 || dureeSec > maxwateringduration) {
        dureeSec = wateringduration;
    }
    Serial.print(F("Arrosage declenche ("));
    Serial.print(source);
    Serial.print(F(") pour "));
    Serial.print(dureeSec);
    Serial.print(F("s a "));
    showTime();
    digitalWrite(relay_led_pin, HIGH);
    digitalWrite(relay_pin, HIGH);
    watering = true;
    timerwatering = millis() + (unsigned long)dureeSec * 1000UL;

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
//         5=ordre d'arrosage a distance (bouton web), suivi de
//           duree,heure_prog,minute_prog
//         0=rien a faire, suivi de heure_prog,minute_prog (sondage normal)
// ---------------------------------------------------------------
void set_param(char* input)
{
    char status[3];
    getToken(input, ',', 0, status, sizeof(status));

    if (strcmp(status, "1") == 0) {
        Serial.println(F("Record ok"));
    }
    else if (strcmp(status, "4") == 0) {
        Serial.println(F("Key error"));
    }
    else if (strcmp(status, "2") == 0) {
        char err[48];
        getToken(input, ',', 1, err, sizeof(err));
        Serial.print(F("Error Record "));
        Serial.println(err);
    }
    else if (strcmp(status, "5") == 0) {
        // Ordre d'arrosage envoye depuis l'interface web (bouton)
        char durStr[6], hStr[3], mStr[3];
        getToken(input, ',', 1, durStr, sizeof(durStr));
        getToken(input, ',', 2, hStr, sizeof(hStr));
        getToken(input, ',', 3, mStr, sizeof(mStr));

        if (hStr[0] != '\0' && mStr[0] != '\0') {
            applySchedule((byte)atoi(hStr), (byte)atoi(mStr));
        }
        startWatering((unsigned int)atoi(durStr), "web");
    }
    else if (strcmp(status, "0") == 0) {
        // Rien a arroser, mais on profite du sondage pour resynchroniser
        // l'heure programmee si elle a change depuis le site
        char hStr[3], mStr[3];
        getToken(input, ',', 1, hStr, sizeof(hStr));
        getToken(input, ',', 2, mStr, sizeof(mStr));
        if (hStr[0] != '\0' && mStr[0] != '\0') {
            applySchedule((byte)atoi(hStr), (byte)atoi(mStr));
        }
    }
    else if (strcmp(status, "3") == 0) {
        Serial.println(F("Réglage heure"));
        char phptime[32];
        getToken(input, ',', 1, phptime, sizeof(phptime));

        char jourStr[3], datejStr[3], datemStr[3], dateyStr[5];
        char heurehStr[3], heuremStr[3], heuresStr[3];
        getToken(phptime, ' ', 0, jourStr, sizeof(jourStr));
        getToken(phptime, ' ', 1, datejStr, sizeof(datejStr));
        getToken(phptime, ' ', 2, datemStr, sizeof(datemStr));
        getToken(phptime, ' ', 3, dateyStr, sizeof(dateyStr));
        getToken(phptime, ' ', 4, heurehStr, sizeof(heurehStr));
        getToken(phptime, ' ', 5, heuremStr, sizeof(heuremStr));
        getToken(phptime, ' ', 6, heuresStr, sizeof(heuresStr));

        byte jourVal = (byte)atoi(jourStr);
        if (jourVal == 0) {
            rtc.setDoW(7);
        } else {
            rtc.setDoW(jourVal);
        }

        if (heuresStr[0] == '\0') {
            Serial.println(F("Erreur"));
        } else {
            // dateyStr contient l'annee complete (ex "2026"), on ne garde
            // que les 2 derniers chiffres comme l'ancien code
            const char* anneeCourte = dateyStr;
            byte len = (byte)strlen(dateyStr);
            if (len >= 2) anneeCourte = dateyStr + len - 2;

            rtc.setClockMode(h12Flag);
            rtc.setDate((byte)atoi(datejStr));
            rtc.setMonth((byte)atoi(datemStr));
            rtc.setYear((byte)atoi(anneeCourte));
            rtc.setHour((byte)atoi(heurehStr));
            rtc.setMinute((byte)atoi(heuremStr));
            rtc.setSecond((byte)atoi(heuresStr));
            Serial.println(F("Heure réglée"));
        }
    }
}

int TimeNow()
{
    heures = rtc.getHour(h12Flag, pmFlag);
    minutes = rtc.getMinute();
    secondes = rtc.getSecond();
    jour = rtc.getDate();
    mois = rtc.getMonth(century);
    annees = rtc.getYear();
    return ((((12 * (int)annees + mois) * 30 + jour) * 24 + heures) * 60 + minutes) * 60 + secondes;
}

void showTime()
{
    heures = rtc.getHour(h12Flag, pmFlag);
    minutes = rtc.getMinute();
    secondes = rtc.getSecond();
    jour = rtc.getDate();
    mois = rtc.getMonth(century);
    annees = rtc.getYear();
    Serial.print(F("showtime "));
    Serial.print(jour, DEC); Serial.print(F("/"));
    Serial.print(mois, DEC); Serial.print(F("/"));
    Serial.print(annees, DEC); Serial.print(F(" "));
    Serial.print(heures, DEC); Serial.print(F(":"));
    Serial.print(minutes, DEC); Serial.print(F(":"));
    Serial.println(secondes, DEC);
}

void showData()
{
    Serial.print(F("AirTemperature=")); Serial.print(AirTemperature);
    Serial.print(F(", AirHumidite=")); Serial.print(AirHumidite);
    Serial.print(F(", Distance=")); Serial.print(Distance);
    Serial.print(F(", TerreNoir=")); Serial.print(TerreNoir);
    Serial.print(F(", TerreBlanc=")); Serial.println(TerreBlanc);
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
    currentSchedHour = alarmHour;
    currentSchedMinute = alarmMinute;

    alarmMinute = 0xFF;
    alarmBits = 0b01100000;
    rtc.setA2Time(alarmDay, alarmHour, alarmMinute, alarmBits, alarmDayIsDay, alarmH12, alarmPM);
    rtc.turnOffAlarm(2);
    rtc.checkIfAlarm(2);
    // alarmBits est réutilisé plus tard pour l'alarme 1 (programmation web) :
    // on le remet à la valeur "heures/minutes/secondes" avant de continuer
    alarmBits = 0b00001000;

    SerialESP8266.begin(9600);
    pinMode(relay_pin, OUTPUT);
    pinMode(relay_led_pin, OUTPUT);
    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);
    stopWatering(); // etat sur connu au demarrage (relais coupe)

    lastrecord = TimeNow();
    lastpoll = TimeNow();
    delay(1000);

    pinMode(alarme_pin, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(alarme_pin), isr_TickTock, FALLING);
}

void loop() {
    // Lecture des capteurs
    TerreBlanc = analogRead(A1);
    TerreNoir = analogRead(A2);
    TerreBlancd = (byte)digitalRead(6);
    TerreNoird = (byte)digitalRead(7);
    AirHumidite = dht.readHumidity();
    AirTemperature = dht.readTemperature();
    // Le DHT22 renvoie parfois NaN en cas de glitch : on garde une valeur
    // sentinelle plutot que d'envoyer une lecture aberrante au serveur
    if (isnan(AirHumidite))    AirHumidite = -1;
    if (isnan(AirTemperature)) AirTemperature = -99;

    digitalWrite(trigPin, LOW);
    delayMicroseconds(5);
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);
    duree = pulseIn(echoPin, HIGH);
    Distance = duree * 0.034 / 2;

    // Arrosage programme : declenchement normal via l'interruption materielle du RTC
    if (tick) {
        rtc.turnOffAlarm(1);
        rtc.checkIfAlarm(1);
        rtc.turnOnAlarm(1);
        tick = 0;
        firedThisMinute = true; // evite un double declenchement via la verif logicielle ci-dessous
        startWatering(wateringduration, "programme");
    }

    // Filet de securite logiciel : si l'interruption materielle du RTC ne
    // fonctionne pas (cablage de la broche INT/SQW, etc.), on verifie aussi
    // directement l'heure courante a chaque tour de boucle.
    {
        byte curH = rtc.getHour(h12Flag, pmFlag);
        byte curM = rtc.getMinute();
        if (curH == currentSchedHour && curM == currentSchedMinute) {
            if (!firedThisMinute) {
                firedThisMinute = true;
                startWatering(wateringduration, "programme (secours logiciel)");
            }
        } else {
            firedThisMinute = false;
        }
    }

    // Coupure de l'arrosage en cours (programme OU a distance) + garde-fou
    if (watering && millis() > timerwatering) {
        stopWatering();
    }

    // Priorité : signaler un arrosage qui vient de démarrer, pour l'historique web
    if (logPending) {
        snprintf(outBuf, sizeof(outBuf), "api_key=%s&arrosage_event=1&Duree=%u&Source=%s",
                 API_KEY, logDuree, logSource);
        SerialESP8266.println(outBuf);
        Serial.println(F("Log arrosage envoye"));
        logPending = false;
    }
    // Envoi périodique des mesures
    else if (TimeNow() - lastrecord > deltarecord) {
        char tempStr[8], humStr[8], distStr[8];
        dtostrf(AirTemperature, 4, 2, tempStr);
        dtostrf(AirHumidite, 4, 2, humStr);
        dtostrf(Distance, 4, 2, distStr);
        snprintf(outBuf, sizeof(outBuf),
                 "api_key=%s&Heure=0&Temp=%s&Hum=%s&Dist=%s&TNoir=%d&TBlanc=%d",
                 API_KEY, tempStr, humStr, distStr, TerreNoir, TerreBlanc);
        SerialESP8266.println(outBuf);
        Serial.println(F("Data Sent"));
        lastrecord = TimeNow();
    }
    // Sondage régulier : ordre d'arrosage en attente ? heure programmee a jour ?
    else if (TimeNow() - lastpoll > deltapoll) {
        snprintf(outBuf, sizeof(outBuf), "api_key=%s&poll=1", API_KEY);
        SerialESP8266.println(outBuf);
        lastpoll = TimeNow();
    }

    if (Serial.available() > 0) {
        char incoming[8];
        byte n = Serial.readBytesUntil('\n', incoming, sizeof(incoming) - 1);
        incoming[n] = '\0';
        while (n > 0 && (incoming[n-1] == '\r')) { incoming[--n] = '\0'; }

        if (strcmp(incoming, "heure") == 0) {
            char tempStr[8], humStr[8], distStr[8];
            dtostrf(AirTemperature, 4, 2, tempStr);
            dtostrf(AirHumidite, 4, 2, humStr);
            dtostrf(Distance, 4, 2, distStr);
            snprintf(outBuf, sizeof(outBuf),
                     "api_key=%s&Heure=1&Temp=%s&Hum=%s&Dist=%s&TNoir=%d&TBlanc=%d",
                     API_KEY, tempStr, humStr, distStr, TerreNoir, TerreBlanc);
            SerialESP8266.println(outBuf);
            Serial.println(F("Demande Réglage heure"));
        }
        else if (strcmp(incoming, "on") == 0) {
            startWatering(wateringduration, "test_serie");
        }
    }

    if (SerialESP8266.available() > 0) {
        byte idx = 0;
        unsigned long startWait = millis();
        while (millis() - startWait < 250 && idx < sizeof(inBuf) - 1) {
            if (SerialESP8266.available()) {
                inBuf[idx++] = (char)SerialESP8266.read();
            }
        }
        inBuf[idx] = '\0';
        // on retire les retours a la ligne de fin envoyes par println()
        while (idx > 0 && (inBuf[idx-1] == '\r' || inBuf[idx-1] == '\n')) {
            inBuf[--idx] = '\0';
        }
        Serial.println(inBuf);
        set_param(inBuf);
    }
    delay(1000);
}

void isr_TickTock() {
    tick = 1;
    return;
}
