/* How to use the DHT-22 sensor with Arduino uno
   Temperature and humidity sensor
*/

//Libraries
#include <DHT.h>;

//Constants
#define DHTPIN 2     // what pin we're connected to
#define DHTTYPE DHT22   // DHT 22  (AM2302)
DHT dht(DHTPIN, DHTTYPE); //// Initialize DHT sensor for normal 16mhz Arduino

//Variables
int message;
int on=0;
int valve_pin = 8;
float hum;  //Stores humidity value
float temp; //Stores temperature value

void setup()
{
  pinMode(valve_pin, OUTPUT);    // sets the digital pin 13 as output
  Serial.begin(9600);
  dht.begin();
}

void loop()
{

    if (Serial.available() > 0){  //Looking for incoming data
      message = int(Serial.read() - '0');  //Reading the data
    if (message == 1) {on=1;}
    else if (message == 0)  {on=0;}
    }
    if (on==1) {digitalWrite(valve_pin, HIGH);}
    else {digitalWrite(valve_pin, LOW);}
    //Read data and store it to variables hum and temp
    hum = dht.readHumidity();
    temp= dht.readTemperature();
    //Print temp and humidity values to serial monitor
    Serial.print(hum);
    Serial.print(";");
    Serial.print(temp);
    Serial.print(";");
    Serial.println(on);
    delay(1000); //Delay 1 sec.
}
