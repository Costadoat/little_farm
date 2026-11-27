#!/usr/bin/env python3
"""Récapitulatif mensuel des lundis, avec alertes sur erreur."""
import logging
import os
import smtplib
import sys
from datetime import date, datetime, time, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE = Path('/home/renaud/Florentina')
TOKEN_FILE = BASE / 'token.json'
STATE_FILE = BASE / 'dernier_envoi.txt'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CALENDAR_IDS = [
    '87lj2dndimsptl8r9j4eqt8r5k@group.calendar.google.com',
    'fr.french#holiday@group.v.calendar.google.com',
]
TZ = ZoneInfo('Europe/Paris')
PRICE_PER_MONDAY = 26
MONTHS = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet',
          'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']


def send_email(subject: str, body: str, recipient: str) -> None:
    username = os.environ['SMTP_USER']
    password = os.environ['SMTP_PASSWORD']
    sender = os.environ.get('SMTP_FROM', username)
    msg = EmailMessage()
    msg['From'] = sender
    msg['Reply-To'] = 'admin@costadoat.fr'
    msg['To'] = recipient
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg.set_content(body)
    with smtplib.SMTP('smtp.free.fr', 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(username, password)
        smtp.send_message(msg)


def calendar_service():
    if not TOKEN_FILE.is_file():
        raise RuntimeError(f'Token Google absent : {TOKEN_FILE}. '
                           'Autoriser Google Agenda sur une machine avec navigateur, puis installer token.json.')
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding='utf-8')
            TOKEN_FILE.chmod(0o600)
        else:
            raise RuntimeError('Token Google invalide ou sans refresh_token : renouveler l’autorisation OAuth.')
    return build('calendar', 'v3', credentials=creds, cache_discovery=False)


def events_for_day(service, calendar_id: str, day: date) -> list[str]:
    start_local = datetime.combine(day, time.min, TZ)
    end_local = datetime.combine(day + timedelta(days=1), time.min, TZ)
    result = []
    page_token = None
    while True:
        response = service.events().list(
            calendarId=calendar_id,
            timeMin=start_local.isoformat(),
            timeMax=end_local.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            maxResults=250,
            pageToken=page_token,
        ).execute()
        for event in response.get('items', []):
            result.append(event.get('summary', '(Sans titre)'))
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    return result


def main() -> None:
    today = datetime.now(TZ).date()
    if today.weekday() != 1:  # Mardi
        logging.info('Pas mardi : aucun envoi.')
        return
    last_monday = today - timedelta(days=1)
    next_monday = last_monday + timedelta(days=7)
    if next_monday.month == last_monday.month:
        logging.info('Ce n’est pas le dernier lundi du mois : aucun envoi.')
        return

    month_key = last_monday.strftime('%Y-%m')
    if STATE_FILE.exists() and STATE_FILE.read_text(encoding='utf-8').strip() == month_key:
        logging.info('Récapitulatif %s déjà envoyé : aucun doublon.', month_key)
        return

    service = calendar_service()
    first_day = last_monday.replace(day=1)
    mondays = []
    day = last_monday
    while day >= first_day:
        mondays.append(day)
        day -= timedelta(days=7)
    mondays.reverse()

    lines = [f'Programme des lundis de {MONTHS[last_monday.month - 1]} {last_monday.year} :', '']
    for monday in mondays:
        lines.append(monday.strftime('%d/%m/%Y'))
        titles = []
        for calendar_id in CALENDAR_IDS:
            titles.extend(events_for_day(service, calendar_id, monday))
        lines.extend(titles or ["Pas d’activités"])
        lines.append('')

    count = len(mondays)
    lines.extend([
        f'Il y avait {count} lundis ce mois-ci.',
        f'Si Florentina est venue {count} fois, le montant indicatif est de {count * PRICE_PER_MONDAY} euros.',
        'Montant à confirmer selon les présences réelles.',
        '',
        'Déclaration CESU : https://www.cesu.urssaf.fr/info/accueil.html',
        '',
        '--',
        'Renaud',
    ])
    recipient = os.environ['REPORT_TO']
    subject = f'[Florentina] Paye de {MONTHS[last_monday.month - 1]} {last_monday.year}'
    send_email(subject, '\n'.join(lines), recipient)
    # Enregistrer uniquement après succès SMTP. En cas de crash juste après
    # acceptation SMTP, un doublon reste théoriquement possible.
    STATE_FILE.write_text(month_key + '\n', encoding='utf-8')
    STATE_FILE.chmod(0o600)
    logging.info('Récapitulatif %s envoyé à %s.', month_key, recipient)


def notify_failure(exc: Exception) -> None:
    recipient = os.environ.get('ALERT_TO') or os.environ.get('REPORT_TO')
    if not recipient:
        logging.error('Impossible d’alerter : ALERT_TO et REPORT_TO absents.')
        return
    try:
        send_email('[ALERTE Florentina] Échec du script',
                   f'Le script Florentina a échoué le {datetime.now(TZ).isoformat()}.\n\n'
                   f'Erreur : {type(exc).__name__}: {exc}\n\n'
                   'Consulter : journalctl -u florentina.service -n 100 --no-pager\n',
                   recipient)
        logging.info('Alerte envoyée à %s.', recipient)
    except Exception:
        logging.exception('Échec de l’envoi du mail d’alerte (SMTP peut être indisponible).')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        main()
    except Exception as error:
        logging.exception('Échec du script Florentina.')
        notify_failure(error)
        sys.exit(1)
