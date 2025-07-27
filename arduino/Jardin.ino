#include <SoftwareSerial.h>
#include <DS3231.h>
#include <Wire.h>
#include <DHT.h>
#include <HCSR04.h>

// parametrage des pins carte
int triggerPin = 10;
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
bool h12Flag =false;
bool pmFlag;

SoftwareSerial SerialESP8266(SerialESP8266RXpin,SerialESP8266TXpin);
DS3231  rtc;
DHT dht(dhtpin, DHT22);

// configuration des variables
int lastrecord; // temps du dernier enregistrement
int deltarecord = 60; // durée entre deux enregistrements en secondes
int wateringduration = 2*60; // durée d'un arrosage en secondes
unsigned long timerwatering;
int TerreBlanc;
int TerreNoir;
int TerreBlancd;
int TerreNoird;
float AirHumidite;
float AirTemperature;
double* Distances;
int heures;
int minutes;
int secondes;
int jour;
int mois;
int annees;

// Récupération des données
String getValue(String data, char separator, int index)
{
    int found = 0;
    int strIndex[] = { 0, -1 };
    int maxIndex = data.length() - 1;
    for (int i = 0; i <= maxIndex && found <= index; i++) {
        if (data.charAt(i) == separator || i == maxIndex) {
            found++;
            strIndex[0] = strIndex[1] + 1;
            strIndex[1] = (i == maxIndex) ? i+1 : i;
        }
    }
    return found > index ? data.substring(strIndex[0], strIndex[1]) : "";
}

// Configuration de la carte en fonction du retour serveur
void set_param(String input)
{   
    String status = getValue(input, ',', 0);
    if (status=="1")
    {
      Serial.println("Record ok");
    }
    else if  (status=="4")
    {
      Serial.println("Key error");
    }
    else if  (status=="2")
    {
       Serial.println("Error Record");
       Serial.println(getValue(input, ',', 1));
    }
    else if  (status=="3") 
    {
      Serial.println("Réglage heure");
      String phptime = getValue(input, ',', 1);
      String jour = getValue(phptime, ' ', 0);
      if (jour.toInt()==0)
      {
        rtc.setDoW(7);
      }
      else
      {
        rtc.setDoW(jour.toInt());
      }
      String datej = getValue(phptime, ' ', 1);
      String datem = getValue(phptime, ' ', 2);
      String datey = getValue(phptime, ' ', 3).substring(2,4);
      String heureh = getValue(phptime, ' ', 4);
      String heurem = getValue(phptime, ' ', 5);
      String heures = getValue(phptime, ' ', 6);
      if (heures=="")
      {
        Serial.println('Erreur');
      }
      else
      {
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
//          Serial.println("Outset1");
}


int TimeNow()
{
  heures = rtc.getHour(h12Flag, pmFlag);
  minutes = rtc.getMinute();
  secondes = rtc.getSecond();
  jour = rtc.getDate();
  mois = rtc.getMonth(century);
  annees = rtc.getYear();
  if (false ) {
  Serial.print("timenow ");
  Serial.print(jour,DEC);
  Serial.print("/");
  Serial.print(mois,DEC);
  Serial.print("/");
  Serial.print(annees,DEC);
  Serial.print(" ");
  Serial.print(heures,DEC);
  Serial.print(":");
  Serial.print(minutes,DEC);
  Serial.print(":");
  Serial.println(secondes,DEC);}
  return ((((12*annees+mois)*30+jour)*24+heures)*60+minutes)*60+secondes;
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
  Serial.print(jour, DEC);
  Serial.print("/");
  Serial.print(mois, DEC);
  Serial.print("/");
  Serial.print(annees, DEC);
  Serial.print(" ");
  Serial.print(heures, DEC);
  Serial.print(":");
  Serial.print(minutes, DEC);
  Serial.print(":");
  Serial.println(secondes, DEC);
}


void showData()
{
    Serial.print("AirTemperature=");
    Serial.print(AirTemperature);
    Serial.print(", AirHumidite=");
    Serial.print(AirHumidite);
    Serial.print(", Distance=");
    Serial.print(Distances[0]);
    Serial.print(", TerreNoir=");
    Serial.print(TerreNoir);
    Serial.print(", TerreBlanc=");
    Serial.println(TerreBlanc);
}


void setup() {
  // Start the I2C interface  
  Wire.begin();
  dht.begin();
  Serial.begin(9600);
  while (!Serial);
  // Assign parameter values for Alarm 1
  alarmDay = rtc.getDate();
  alarmH12 = false;
  alarmHour = 20;
  alarmMinute = 00;
  alarmSecond = 00; // initialize to the interval length
  alarmBits = 0b00001000; // Alarm 1 when seconds match
  alarmDayIsDay = false; // using date of month

  // Upload initial parameters of Alarm 1
  rtc.turnOffAlarm(1);
  rtc.setA1Time(
     alarmDay, alarmHour, alarmMinute, alarmSecond,
     alarmBits, alarmDayIsDay, alarmH12, alarmPM);
  // clear Alarm 1 flag after setting the alarm time
  rtc.checkIfAlarm(1);
  // now it is safe to enable interrupt output
  rtc.turnOnAlarm(1);

  // When using interrupt with only one of the DS3231 alarms, as in this example,
  // it may be possible to prevent the other alarm entirely,
  // so it will not covertly block the outgoing interrupt signal.

  // Try to prevent Alarm 2 altogether by assigning a 
  // nonsensical alarm minute value that cannot match the clock time,
  // and an alarmBits value to activate "when minutes match".
  alarmMinute = 0xFF; // a value that will never match the time
  alarmBits = 0b01100000; // Alarm 2 when minutes match, i.e., never
  // Upload the parameters to prevent Alarm 2 entirely
  rtc.setA2Time(
      alarmDay, alarmHour, alarmMinute,
      alarmBits, alarmDayIsDay, alarmH12, alarmPM);
  // disable Alarm 2 interrupt
  rtc.turnOffAlarm(2);
  // clear Alarm 2 flag
  rtc.checkIfAlarm(2);
  SerialESP8266.begin(9600);
  pinMode(relay_pin, OUTPUT);
  pinMode(relay_led_pin, OUTPUT);
  HCSR04.begin(triggerPin, echoPin);
  lastrecord=TimeNow();
  SerialESP8266.setTimeout(250);
  delay(1000);

  // NOTE: both of the alarm flags must be clear
  // to enable output of a FALLING interrupt

  pinMode(alarme_pin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(alarme_pin), isr_TickTock, FALLING);
}

void loop() {
  // Lecture des capteurs d'humidité terre
  TerreBlanc = analogRead(A1);
  TerreNoir = analogRead(A2);
  TerreBlancd = digitalRead(6);
  TerreNoird = digitalRead(7);
  AirHumidite = dht.readHumidity();
  AirTemperature = dht.readTemperature();
  Distances = HCSR04.measureDistanceCm();

  // if alarm went of, do alarm stuff
    if (tick) {
        // disable Alarm 1 interrupt
        rtc.turnOffAlarm(1);
        // Clear Alarm 1 flag
        rtc.checkIfAlarm(1);
        rtc.turnOnAlarm(1);
        tick = 0; // reset the local interrupt-received flag
        // optional serial output
        Serial.print("Arrosage : ");
        showTime();
        digitalWrite(relay_led_pin, HIGH);
        digitalWrite(relay_pin, HIGH);
        timerwatering=millis()+wateringduration*1000;
    }
    if(millis()>timerwatering)
    {
        digitalWrite(relay_led_pin, LOW);
        digitalWrite(relay_pin, LOW);
    }
    if (TimeNow()-lastrecord>deltarecord)
    {
      SerialESP8266.println("api_key=tPmAT5Ab&Heure=0&Temp="+String(AirTemperature)+"&Hum="+String(AirHumidite)+"&Dist="+String(Distances[0])+"&TNoir="+String(TerreNoir)+"&TBlanc="+String(TerreBlanc));
      Serial.println("Data Sent");
      lastrecord=TimeNow();
    }

    if (Serial.available()>0) {
      String incomingByte = Serial.readStringUntil('\n');
      if (incomingByte=="heure")
      {
      SerialESP8266.println("api_key=tPmAT5Ab&Heure=1&Temp="+String(AirTemperature)+"&Hum="+String(AirHumidite)+"&Dist="+String(Distances[0])+"&TNoir="+String(TerreNoir)+"&TBlanc="+String(TerreBlanc));
      Serial.println("Demande Réglage heure");
      }
    }

    if (SerialESP8266.available()>0) {
      String input = SerialESP8266.readString();
      set_param(input);
    }  
    delay(1000);
}

void isr_TickTock() {
    // interrupt signals to loop
    tick = 1;
    return;
}
