// Capteur température et humidité
#include "DHT.h"
int DHTPIN = 8; // broche ou l'on a branche le capteur
DHT dht(DHTPIN, DHT22);//déclaration du capteur

// Capteur ultrason
/* Constantes pour les broches */
const byte TRIGGER_PIN = 2; // Broche TRIGGER
const byte ECHO_PIN = 3;    // Broche ECHO 
/* Constantes pour le timeout */
const unsigned long MEASURE_TIMEOUT = 25000UL; // 25ms = ~8m à 340m/s
/* Vitesse du son dans l'air en mm/us */
const float SOUND_SPEED = 340.0 / 1000;
 
// Capteurs hygrometrie 
int sensor_ground_white_pin = A1; // sélection de la pin de mesure du capteur d'humidité de sol
int sensor_ground_black_pin = A2; // sélection de la pin de mesure du capteur d'humidité de sol

String message;
int on=0;
int value=-1;
int valve_pin = 8;
int incomingBytes[2];

void setup()
{
 Serial.begin(9600);
 dht.begin();

  /* Initialise les broches du capteur ultra-son*/
  pinMode(TRIGGER_PIN, OUTPUT);
  digitalWrite(TRIGGER_PIN, LOW); // La broche TRIGGER doit être à LOW au repos
  pinMode(ECHO_PIN, INPUT);
  
}
void loop()
{
 if (Serial.available()>2)
   {
    on  = Serial.readStringUntil(',').toInt();
    value  = Serial.readStringUntil('\0').toInt();
    Serial.println(on);
    Serial.println(value);
   }
    if (on==1 && abs(value)>0 ) {digitalWrite(valve_pin, HIGH);Serial.print(value);Serial.println("start");value-=1;}
    else {on=-1;value=-1;digitalWrite(valve_pin, LOW);Serial.println("stop");}
 
 // Lecture du capteur d'humidité/température
 // La lecture du capteur prend 250ms
 // Les valeurs lues peuvet etre vieilles de jusqu'a 2 secondes (le capteur est lent)
 float h = dht.readHumidity();//on lit l'hygrometrie
 float t = dht.readTemperature();//on lit la temperature en celsius (par defaut)
 //On verifie si la lecture a echoue, si oui on quitte la boucle pour recommencer.

  // Lecture du capteur ultra-son
  /* 1. Lance une mesure de distance en envoyant une impulsion HIGH de 10µs sur la broche TRIGGER */
  digitalWrite(TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIGGER_PIN, LOW);
  /* 2. Mesure le temps entre l'envoi de l'impulsion ultrasonique et son écho (si il existe) */
  long measure = pulseIn(ECHO_PIN, HIGH, MEASURE_TIMEOUT); 
  /* 3. Calcul la distance à partir du temps mesuré */
  float distance_mm = measure / 2.0 * SOUND_SPEED;
  float distance_cm = distance_mm / 10.0;
  float remplissage = (35.0 - distance_cm) / 100.0;

  // Lecture des capteur d'hygrométrie du sol   
  float sensor_ground_white_value = 100.*(1023.-analogRead(sensor_ground_white_pin))/1023.; 
  float sensor_ground_black_value = 100.*(1023.-analogRead(sensor_ground_black_pin))/1023.; 
  sensor_ground_white_value=1.12;
  /* Communication serie */
 
  Serial.print(h);
  Serial.print(";");
  Serial.print(t);
  Serial.print(";");
  Serial.print(remplissage, 2);
  Serial.print(";");
  Serial.print(sensor_ground_white_value,2);
  Serial.print(";");
  Serial.print(sensor_ground_black_value,2);
  Serial.print(";");
  Serial.print(on);
  Serial.print(";");
  Serial.println(value);
  delay(900);
 
}
