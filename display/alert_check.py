#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alert_check.py — à lancer via cron (ex. toutes les 20 minutes), indépendamment
du site Flask. Vérifie l'âge de la dernière mesure reçue et envoie un mail si ça fait plus de 24h, sauf si l'alerte a été mise en pause depuis le site
(reglages.Id=8), ou si un mail a déjà été envoyé récemment (anti-spam).

Exemple de crontab (toutes les 20 min) :
  */20 * * * * cd /chemin/vers/appli && /chemin/vers/venv/bin/python alert_check.py >> /var/log/jardin_alert.log 2>&1
"""
import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText

import MySQLdb

from local_settings import DATABASE, EMAIL_CONFIG

SEUIL_ALERTE_SECONDES = 24 * 3600      # déclenche l'alerte après 24h sans donnée
DELAI_RELANCE_SECONDES = 12 * 3600     # ne renvoie pas un email avant ce délai


def get_reglage(cursor, id_, default):
    cursor.execute("SELECT valeur FROM reglages WHERE Id=%s", (id_,))
    row = cursor.fetchone()
    return row[0] if row and row[0] is not None else default


def set_reglage(cursor, id_, valeur):
    cursor.execute("UPDATE reglages SET valeur=%s WHERE Id=%s", (valeur, id_))


def envoyer_email(sujet, corps):
    msg = MIMEText(corps)
    msg['Subject'] = sujet
    msg['From'] = EMAIL_CONFIG['EMAIL_FROM']
    msg['Reply-To'] = 'admin@costadoat.fr'
    msg['To'] = EMAIL_CONFIG['EMAIL_TO']

    with smtplib.SMTP(EMAIL_CONFIG['SMTP_HOST'], EMAIL_CONFIG['SMTP_PORT']) as server:
        server.starttls()
        server.login(EMAIL_CONFIG['SMTP_USER'], EMAIL_CONFIG['SMTP_PASSWORD'])
        server.sendmail(EMAIL_CONFIG['EMAIL_FROM'], [EMAIL_CONFIG['EMAIL_TO']], msg.as_string())


def main():
    conn = MySQLdb.connect(
        host=DATABASE['HOST'], port=DATABASE['PORT'],
        user=DATABASE['USER'], passwd=DATABASE['PASSWORD'], db=DATABASE['BASE']
    )
    cursor = conn.cursor()

    alerte_active = get_reglage(cursor, 8, 1)
    if not alerte_active:
        print("Alerte en pause, rien à faire.")
        return

    # Système extérieur déclaré débranché depuis le site (reglages.Id=10) :
    # l'absence de données est normale, on ne prévient pas.
    if not get_reglage(cursor, 10, 1):
        print("Système extérieur débranché, rien à faire.")
        return

    cursor.execute("SELECT Temps FROM sensors ORDER BY Id DESC LIMIT 1")
    row = cursor.fetchone()
    if row is None:
        print("Aucune mesure en base, rien à signaler.")
        return

    last_record = row[0]
    delta = (datetime.now() - last_record).total_seconds()

    if delta <= SEUIL_ALERTE_SECONDES:
        # Tout va bien : on réarme pour qu'une prochaine coupure redéclenche
        # une alerte immédiatement plutôt que d'attendre le délai de relance
        set_reglage(cursor, 9, 0)
        conn.commit()
        print("Dernière mesure il y a {:.0f} min, OK.".format(delta / 60))
        return

    dernier_envoi = get_reglage(cursor, 9, 0)
    maintenant = int(time.time())
    if dernier_envoi and (maintenant - int(dernier_envoi)) < DELAI_RELANCE_SECONDES:
        print("Déjà alerté récemment, on ne renvoie pas.")
        return

    heures = int(delta // 3600)
    envoyer_email(
        "Jardin : aucune donnee recue depuis {}h".format(heures),
        "Le dernier enregistrement du systeme d'arrosage date du {}.\n"
        "Ca fait environ {}h qu'aucune nouvelle mesure n'a ete recue.\n\n"
        "Verifie l'Arduino, l'ESP8266 et la connexion reseau.\n\n"
        "Tu peux mettre cette alerte en pause depuis le site.".format(
            last_record.strftime('%d/%m/%Y %H:%M'), heures
        )
    )
    set_reglage(cursor, 9, maintenant)
    conn.commit()
    print("MAIL d'alerte envoye.")


if __name__ == '__main__':
    main()
