#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lecture_ds18b20.py — lit la sonde DS18B20 branchée sur la Raspberry Pi
(bus 1-Wire, GPIO4) et enregistre la température intérieure en base.

Indépendant du système extérieur (ESP8266 + jardin.php) : il tourne même
quand celui-ci est débranché.

Prérequis : 1-Wire activé (dtoverlay=w1-gpio dans /boot/firmware/config.txt,
puis redémarrage). Voir DEPLOIEMENT.md.

Exemple de crontab (toutes les 5 minutes) :
  */5 * * * * cd /sites/jardin/display && /sites/jardin/myenv/bin/python lecture_ds18b20.py >> /sites/jardin/display/logs/ds18b20.log 2>&1

Pour tester à la main sans rien écrire en base :
  python lecture_ds18b20.py --test
"""
import glob
import sys
import time

W1_DEVICES = '/sys/bus/w1/devices/28-*'   # 28 = famille des DS18B20
NB_ESSAIS = 3

# Valeurs renvoyées par la sonde quand la lecture est mauvaise :
#  85.0  = valeur de démarrage (conversion pas encore faite)
#  -127  = sonde non joignable
VALEURS_INVALIDES = (85.0, -127.0)


def trouver_sonde():
    sondes = sorted(glob.glob(W1_DEVICES))
    if not sondes:
        raise RuntimeError(
            "Aucune sonde DS18B20 trouvée dans /sys/bus/w1/devices/. "
            "Vérifier le câblage, la résistance de 4,7 kOhm et que "
            "dtoverlay=w1-gpio est bien activé."
        )
    return sondes[0]


def lire_temperature(sonde):
    """Lit w1_slave et vérifie le CRC (ligne 1 terminée par YES)."""
    with open(sonde + '/w1_slave') as f:
        lignes = f.read().strip().splitlines()
    if len(lignes) < 2 or not lignes[0].endswith('YES'):
        return None
    pos = lignes[1].find('t=')
    if pos == -1:
        return None
    temperature = int(lignes[1][pos + 2:]) / 1000.0
    if temperature in VALEURS_INVALIDES:
        return None
    return round(temperature, 2)


def mesurer():
    sonde = trouver_sonde()
    for essai in range(NB_ESSAIS):
        t = lire_temperature(sonde)
        if t is not None:
            return t
        time.sleep(1)
    raise RuntimeError("Lecture invalide après {} essais (CRC ou valeur 85/-127).".format(NB_ESSAIS))


def enregistrer(temperature):
    import MySQLdb
    from local_settings import DATABASE

    conn = MySQLdb.connect(
        host=DATABASE['HOST'], port=DATABASE['PORT'],
        user=DATABASE['USER'], passwd=DATABASE['PASSWORD'], db=DATABASE['BASE']
    )
    try:
        cursor = conn.cursor()
        # NOW() côté MySQL, comme jardin.php, pour que les deux séries de
        # mesures soient sur la même horloge
        cursor.execute(
            "INSERT INTO temperature_interieure (Temps, Temperature) VALUES (NOW(), %s)",
            (temperature,)
        )
        conn.commit()
    finally:
        conn.close()


def main():
    test = '--test' in sys.argv
    horodatage = time.strftime('%Y-%m-%d %H:%M:%S')
    try:
        temperature = mesurer()
    except Exception as e:
        print("{} ERREUR lecture : {}".format(horodatage, e))
        sys.exit(1)

    if test:
        print("{} Température lue : {:.2f} °C (mode test, rien n'est enregistré)".format(horodatage, temperature))
        return

    try:
        enregistrer(temperature)
    except Exception as e:
        print("{} ERREUR base de données : {}".format(horodatage, e))
        sys.exit(1)
    print("{} {:.2f} °C enregistrée".format(horodatage, temperature))


if __name__ == '__main__':
    main()
