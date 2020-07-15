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
            print(line)
            try :
                data=line.split(';')
                humid=data[0]
                temp=data[1]
                remplissage=data[2]
                hygro_t_b=data[3]
                hygro_t_n=data[4]
                valve=data[5]
                if valve==-1:
                    sql = 'UPDATE `reglages` SET `valeur`=0 WHERE Id=1'
                    mycursor.execute(sql)
                    sql = 'UPDATE `reglages` SET `valeur`=-1 WHERE Id=2'
                    mycursor.execute(sql)
                    valve=0
            except:
                humid=None
                temp=None
                valve=None
                hygro_t_b=None
                hygro_t_n=None
                remplissage=None
            if humid:
                if last_time_write+timedelta(seconds=delta_write)<datetime.now():
                    sql = "INSERT INTO sensors (Temps, Humidite, Temperature, remplissage_reservoir, hygrometrie_terre_b, hygrometrie_terre_n, Valve) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    val = (datetime.now(), humid, temp, remplissage, hygro_t_b, hygro_t_n, valve)
                    print(val)
                    mycursor.execute(sql, val)
                    last_time_write=datetime.now()
                    mydb.commit()
#                    print(mycursor.rowcount, "record inserted.")
            if last_time_read+timedelta(seconds=delta_read)<datetime.now():
                sql = 'SELECT * FROM reglages WHERE Id=1'
                mycursor.execute(sql)
                marche = mycursor.fetchone()
                print(marche)
                sql = 'SELECT * FROM reglages WHERE Id=2'
                mycursor.execute(sql)
                duree = mycursor.fetchone()
                print(duree)
                last_time_read=datetime.now()
                if marche[2]!=int(valve) :
                    if marche[2]==1 and float(remplissage)>=2.:
                        ser.write(b'1,%i' % int(duree[2]))
                        last_time_write=last_time_write-timedelta(minutes=2)
                    else:
                        ser.write(b'0,-1')
                        last_time_write=last_time_write-timedelta(minutes=2)
                elif marche[2]==int(valve) and float(remplissage)<2:
                    ser.write(b'0,-1')
                    last_time_write=last_time_write-timedelta(minutes=2)
                        
