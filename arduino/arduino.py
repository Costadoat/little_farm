#!/usr/bin/env python3
import serial
from datetime import datetime, timedelta
import mysql.connector

from local_settings import DATABASE

mydb = mysql.connector.connect(
  host=DATABASE['HOST'],
  user=DATABASE['USER'],
  passwd=DATABASE['PASSWORD'],
  database=DATABASE['BASE']  
  )

mycursor = mydb.cursor()
valve=None
last_time_write=datetime.now()
delta_write=60
last_time_read=datetime.now()
delta_read=30

if __name__ == '__main__':
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    ser.flush()
    
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').rstrip()
#            print(line)
            try :
                data=line.split(';')
                humid=data[0]
                temp=data[1]
                hauteur=35-data[2]
                hygro_t_b=data[3]
                hygro_t_n=data[4]
                valve=data[5]
            except:
                humid=None
                temp=None
                valve=None
                hygro_t_b=None
                hygro_t_n=None
                hauteur=None
            if humid:
                if last_time_write+timedelta(seconds=delta_write)<datetime.now():
                    sql = "INSERT INTO sensors (Temps, Humidite, Temperature, hauteur_reservoir, hygrometrie_terre_b, hygrometrie_terre_n, Valve) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    val = (datetime.now(), humid, temp, hauteur, hygro_t_b, hygro_t_n, valve)
                    mycursor.execute(sql, val)
                    last_time_write=datetime.now()
                    mydb.commit()
#                    print(mycursor.rowcount, "record inserted.")
            if last_time_read+timedelta(seconds=delta_read)<datetime.now():
                sql = 'SELECT * FROM reglages WHERE Id=1'
                mycursor.execute(sql)
                marche = mycursor.fetchone()
                sql = 'SELECT * FROM reglages WHERE Id=2'
                mycursor.execute(sql)
                duree = mycursor.fetchone()
                last_time_read=datetime.now()
                if marche and valve:
                    if marche[2]!=int(valve) :
                        if marche[2]==1 and hauteur>=3:
                            ser.write(b'1')
                            last_time_write=last_time_write-timedelta(minutes=2)
                        else:
                            ser.write(b'0')
                            last_time_write=last_time_write-timedelta(minutes=2)
                    elif marche[2]==int(valve) and hauteur<3:
                        ser.write(b'0')
                        last_time_write=last_time_write-timedelta(minutes=2)
                        
