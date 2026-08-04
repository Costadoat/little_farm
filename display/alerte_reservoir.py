#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérifie le niveau du réservoir à partir de la dernière mesure en base
et envoie un email d'alerte si le niveau est bas depuis trop longtemps.

À exécuter périodiquement via cron, par exemple toutes les 15 minutes :
    */15 * * * * /django/jardin/mvpappenv/bin/python /django/jardin/alerte_reservoir.py

Ce script est volontairement indépendant de Flask : il tourne même si
personne ne consulte le site, ce qui est le seul moyen fiable d'être
prévenu à temps.
"""
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta

import MySQLdb

from local_settings import DATABASE, EMAIL_CONFIG, NIVEAU_ALERTE_PCT, \
    NIVEAU_RETOUR_NORMAL_PCT, DELAI_MIN_ENTRE_ALERTES_HEURES


def send_email(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_CONFIG['EMAIL_FROM']
    msg['To'] = EMAIL_CONFIG['EMAIL_TO']

    with smtplib.SMTP(EMAIL_CONFIG['SMTP_HOST'], EMAIL_CONFIG['SMTP_PORT']) as server:
        server.starttls()
        server.login(EMAIL_CONFIG['SMTP_USER'], EMAIL_CONFIG['SMTP_PASSWORD'])
        server.send_message(msg)


def main():
    conn = MySQLdb.connect(
        host=DATABASE['HOST'], port=DATABASE['PORT'],
        user=DATABASE['USER'], passwd=DATABASE['PASSWORD'], db=DATABASE['BASE']
    )
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT Temps, remplissage_reservoir FROM sensors ORDER BY Id DESC LIMIT 1")
    last = cursor.fetchone()
    if not last:
        return  # aucune mesure, rien à faire

    # Si la dernière mesure est trop vieille, la carte a peut-être un souci
    # de communication : on ne déclenche pas d'alerte "réservoir" pour ça
    # (c'est déjà visible via le statut rouge sur le site).
    if datetime.now() - last['Temps'] > timedelta(minutes=30):
        cursor.close()
        conn.close()
        return

    niveau = last['remplissage_reservoir']  # en %, 100 = plein, 0 = vide

    cursor.execute("SELECT DerniereAlerte, EnAlerte FROM alertes WHERE Id=1")
    etat = cursor.fetchone()
    deja_en_alerte = bool(etat and etat['EnAlerte'])
    derniere_alerte = etat['DerniereAlerte'] if etat else None

    if niveau <= NIVEAU_ALERTE_PCT:
        peut_renvoyer = (
            derniere_alerte is None
            or datetime.now() - derniere_alerte > timedelta(hours=DELAI_MIN_ENTRE_ALERTES_HEURES)
        )
        if not deja_en_alerte or peut_renvoyer:
            send_email(
                "⚠️ Réservoir jardin bas",
                "Le réservoir d'arrosage est bas (niveau mesuré : {:.0f}%, "
                "seuil d'alerte : {}%). Pense à le remplir.".format(niveau, NIVEAU_ALERTE_PCT)
            )
            cursor.execute(
                "UPDATE alertes SET DerniereAlerte=NOW(), EnAlerte=1 WHERE Id=1"
            )
            conn.commit()

    elif niveau >= NIVEAU_RETOUR_NORMAL_PCT and deja_en_alerte:
        # Le réservoir a été rempli : on désarme l'alerte, un email de
        # retour à la normale n'est pas indispensable mais c'est agréable
        send_email(
            "✅ Réservoir jardin rempli",
            "Le niveau du réservoir est revenu à la normale (niveau mesuré : {:.0f}%).".format(niveau)
        )
        cursor.execute("UPDATE alertes SET EnAlerte=0 WHERE Id=1")
        conn.commit()

    cursor.close()
    conn.close()


if __name__ == '__main__':
    main()
