	# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from time import sleep
from datetime import datetime, timedelta, timezone
import locale

start_time = datetime.now() - timedelta(days=2)

from local_settings import DATABASE

# ---- Formatage en français, sans dépendre de la locale du serveur ---------
JOURS_FR = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
MOIS_FR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
           'août', 'septembre', 'octobre', 'novembre', 'décembre']


def format_date_fr(dt):
    """ex: 'mardi 14 juillet 2026' """
    return "{} {} {} {}".format(JOURS_FR[dt.weekday()], dt.day, MOIS_FR[dt.month - 1], dt.year)


def format_duration_fr(total_seconds):
    """Durée lisible, ex: '2 jours 3 heures', '5 minutes 12 secondes'.
    Affiche au plus les deux unités les plus significatives."""
    total_seconds = int(total_seconds)
    if total_seconds <= 0:
        return "0 seconde"
    units = [
        ('an', 365 * 86400),
        ('mois', 30 * 86400),
        ('jour', 86400),
        ('heure', 3600),
        ('minute', 60),
        ('seconde', 1),
    ]
    parts = []
    remaining = total_seconds
    for name, size in units:
        value = remaining // size
        if value > 0:
            suffix = 's' if value > 1 and name != 'mois' else ''
            parts.append("{} {}{}".format(value, name, suffix))
            remaining -= value * size
        if len(parts) == 2:
            break
    return " ".join(parts)

application = Flask(__name__)

# Change this to your secret key (can be anything, it's for extra protection)
application.secret_key = 'zffuiaozeguzbeunf13znfepZU11213333BV'

# ---- HTTPS (voir nginx_jardin.conf pour la partie reverse proxy) ---------
# Une fois le certificat en place devant gunicorn, ces réglages évitent que
# le cookie de session ne parte jamais en clair, et redirigent tout HTTP
# restant vers HTTPS.
application.config['SESSION_COOKIE_SECURE'] = True
application.config['SESSION_COOKIE_HTTPONLY'] = True
application.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
application.config['PREFERRED_URL_SCHEME'] = 'https'

# Enter your database connection details below
application.config['MYSQL_HOST'] = DATABASE['HOST']
application.config['MYSQL_PORT'] = DATABASE['PORT']
application.config['MYSQL_USER'] = DATABASE['USER']
application.config['MYSQL_PASSWORD'] = DATABASE['PASSWORD']
application.config['MYSQL_DB'] = DATABASE['BASE']

# Intialize MySQL
mysql = MySQL(application)


@application.before_request
def before_request():
    session.permanent = True
#    application.permanent_session_lifetime = timedelta(minutes=5)
    # Nginx transmet ce header pour indiquer le protocole d'origine.
    # Redirige vers HTTPS si jamais quelqu'un arrive encore en HTTP.
    if request.headers.get('X-Forwarded-Proto', 'https') == 'http':
        return redirect(request.url.replace('http://', 'https://', 1), code=301)


@application.route('/login/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM comptes WHERE username = %s AND password = %s', (username, password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            return redirect(url_for('home'))
        else:
            msg = "Le mot de passe n'est pas correct"
    return render_template('index.html', msg=msg)


@application.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))


@application.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM comptes WHERE username = %s', (username,))
        account = cursor.fetchone()
        if account:
            msg = 'Le compte existe déjà'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = "L'adresse mail n'est pas valide."
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Le pseudo ne doit contenir que des chiffres et des lettres !'
        elif not username or not password or not email:
            msg = 'Remplir le formulaire !'
        else:
            cursor.execute('INSERT INTO comptes VALUES (NULL, %s, %s, %s)', (username, password, email,))
            mysql.connection.commit()
            msg = "L'enregistrement est validé !"
    elif request.method == 'POST':
        msg = 'Remplir le formulaire !'
    return render_template('register.html', msg=msg)


@application.route('/profile')
def profile():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM comptes WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        return render_template('profile.html', account=account)
    return redirect(url_for('login'))


class data:
    def __init__(self, backgroundColor, borderColor, nom, values):
        self.backgroundColor = backgroundColor
        self.borderColor = borderColor
        self.nom = nom
        self.values = values


# Plages disponibles pour la navigation des graphes. "interval" est injecté
# directement dans le SQL (INTERVAL ...) : ces valeurs sont des constantes
# fixes définies ici, jamais issues de l'entrée utilisateur, donc sans risque
# d'injection malgré l'absence de placeholder à cet endroit précis.
# "bucket_seconds" agrège les mesures par moyenne sur des tranches de N
# secondes côté SQL, pour limiter le nombre de points envoyés au navigateur.
RANGE_OPTIONS = {
    'heure':   {'label': 'Dernière heure',   'interval': '1 HOUR', 'limit': 800,  'unit': 'minute', 'bucket_seconds': None},
    'jour':    {'label': 'Dernier jour',     'interval': '1 DAY',  'limit': 800,  'unit': 'hour',   'bucket_seconds': 900},   # 15 min -> ~96 points
    'semaine': {'label': 'Dernière semaine', 'interval': '7 DAY',  'limit': 2500, 'unit': 'day',    'bucket_seconds': 7200},  # 2h -> ~84 points
}


@application.route('/', methods=['GET', 'POST'])
def home():
    if 'loggedin' in session and session['id'] == 1:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        if request.method == 'POST':
            # Bouton "Arroser maintenant" (durée fixe, ex. 2 min)
            if 'bouton_arroser' in request.form:
                duree = request.form.get('duree', '120')
                duree = duree if duree.isdigit() else '120'
                cursor.execute('UPDATE reglages SET valeur=%s WHERE Id=2', (duree,))
                mysql.connection.commit()
                cursor.execute('UPDATE reglages SET valeur=1 WHERE Id=1')
                mysql.connection.commit()
            # Bouton "Stop" : on annule un ordre pas encore consommé par la carte
            elif 'bouton_stop' in request.form:
                cursor.execute('UPDATE reglages SET valeur=0 WHERE Id=1')
                mysql.connection.commit()
            # Formulaire "Programmation" : change l'heure de l'arrosage automatique
            elif 'bouton_programmer' in request.form:
                heure_prog = request.form.get('heure_prog', '')
                # attendu au format HH:MM (input type="time")
                if re.match(r'^\d{1,2}:\d{2}$', heure_prog):
                    h, m = heure_prog.split(':')
                    h, m = int(h), int(m)
                    if 0 <= h <= 23 and 0 <= m <= 59:
                        cursor.execute('UPDATE reglages SET valeur=%s WHERE Id=4', (h,))
                        cursor.execute('UPDATE reglages SET valeur=%s WHERE Id=5', (m,))
                        mysql.connection.commit()

            # Pattern Post/Redirect/Get : on redirige vers la page en GET après
            # traitement du formulaire, pour que le rafraîchissement automatique
            # (et un simple F5) ne réexécute jamais un POST déjà traité.
            return redirect(url_for('home'))

        selected_range = request.args.get('range', 'jour')
        if selected_range not in RANGE_OPTIONS:
            selected_range = 'jour'
        range_conf = RANGE_OPTIONS[selected_range]

        Temps = []
        Humidite_values = []
        Temperature_values = []
        Hygrometrie_terre_blanc_values = []
        Hygrometrie_terre_noir_values = []
        Remplissage_reservoir_values = []

        if range_conf['bucket_seconds']:
            # Moyenne par tranche de temps : beaucoup plus léger à charger/
            # afficher qu'une mesure brute toutes les 5 minutes.
            bucket = range_conf['bucket_seconds']
            cursor.execute(
                "SELECT FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(Temps)/%s)*%s) AS Temps, "
                "AVG(Humidite) AS Humidite, AVG(Temperature) AS Temperature, "
                "AVG(hygrometrie_terre_b) AS hygrometrie_terre_b, "
                "AVG(hygrometrie_terre_n) AS hygrometrie_terre_n, "
                "AVG(remplissage_reservoir) AS remplissage_reservoir "
                "FROM sensors WHERE Temps >= (NOW() - INTERVAL " + range_conf['interval'] + ") "
                "GROUP BY Temps ORDER BY Temps",
                (bucket, bucket)
            )
        else:
            cursor.execute(
                "SELECT * FROM (SELECT * FROM sensors WHERE Temps >= (NOW() - INTERVAL "
                + range_conf['interval'] +
                ") ORDER BY `Id` DESC LIMIT %s) t1 ORDER BY t1.Id",
                (range_conf['limit'],)
            )

        myresult = cursor.fetchall()
        for x in myresult:
            temps = x['Temps'] - timedelta(hours=2)
            Temps.append(temps)
            Humidite_values.append([temps, x['Humidite']])
            Temperature_values.append([temps, x['Temperature']])
            Hygrometrie_terre_blanc_values.append([temps, x['hygrometrie_terre_b']])
            Hygrometrie_terre_noir_values.append([temps, x['hygrometrie_terre_n']])
            Remplissage_reservoir_values.append([temps, x['remplissage_reservoir']])

        # Instants d'arrosage sur la même plage que les mesures affichées,
        # pour les superposer aux graphes sous forme de barres verticales.
        cursor.execute(
            "SELECT Debut FROM arrosages WHERE Debut >= (NOW() - INTERVAL "
            + range_conf['interval'] + ") ORDER BY Debut"
        )
        arrosage_instants = [row['Debut'] - timedelta(hours=2) for row in cursor.fetchall()]

        cursor.execute("SELECT valeur FROM reglages WHERE Id=1")
        reglage_row = cursor.fetchone()
        arrosage_demande = bool(reglage_row and reglage_row['valeur'] == 1)

        cursor.execute("SELECT Debut, Duree, Source FROM arrosages ORDER BY Id DESC LIMIT 10")
        historique_arrosages = cursor.fetchall()

        cursor.execute("SELECT valeur FROM reglages WHERE Id=4")
        heure_row = cursor.fetchone()
        cursor.execute("SELECT valeur FROM reglages WHERE Id=5")
        minute_row = cursor.fetchone()
        heure_prog = '{:02d}:{:02d}'.format(
            heure_row['valeur'] if heure_row else 20,
            minute_row['valeur'] if minute_row else 0,
        )

        cursor.execute("SELECT Temps FROM sensors ORDER BY Id DESC LIMIT 1")
        records = cursor.fetchone()
        last_record = records['Temps'] if records else None

        line_labels = Temps
        Temperature = data("rgba(186,125,125,1)", "rgba(186,125,125,1)", 'Température', Temperature_values)
        Humidite = data("rgba(151,187,205,1)", "rgba(151,187,205,1)", 'Humidité', Humidite_values)
        Hygrometrie_terre_blanc = data("rgba(153,204,255,1)", "rgba(153,204,255,1)", 'Hygrométrie terre (blanc)', Hygrometrie_terre_blanc_values)
        Hygrometrie_terre_noir = data("rgba(0,128,255,1)", "rgba(0,128,255,1)", 'Hygrométrie terre (noir)', Hygrometrie_terre_noir_values)
        Niveau_eau = data("rgba(245,75,39,1)", "rgba(245,75,39,1)", "Niveau eau", Remplissage_reservoir_values)
        line_values_1 = [Temperature, Humidite]
        line_values_2 = [Hygrometrie_terre_blanc, Hygrometrie_terre_noir]
        line_values_3 = [Niveau_eau]

        dernieres = myresult[-1] if myresult else None

        if last_record:
            delta_last_record = int((datetime.now() - last_record).total_seconds())
        else:
            delta_last_record = None

        if delta_last_record is None or delta_last_record > 600:
            class2 = 'error'
        else:
            class2 = 'ok'

        maintenant = datetime.now()
        date_aujourdhui_fr = format_date_fr(maintenant)

        if delta_last_record is not None:
            duree_depuis_dernier_enregistrement_fr = format_duration_fr(delta_last_record)
            if delta_last_record > 86400:
                # Décalage de plus de 24h : le jour est plus informatif que l'heure seule
                last_record_display = "{} à {}".format(
                    format_date_fr(last_record), last_record.strftime('%H:%M')
                )
            else:
                last_record_display = last_record.strftime('%H:%M')
        else:
            duree_depuis_dernier_enregistrement_fr = None
            last_record_display = None

        return render_template(
            'home.html',
            username=session['username'],
            title='Capteurs',
            max=100,
            labels=line_labels,
            datasets_temperature=line_values_1,
            datasets_hygrometrie=line_values_2,
            datasets_niveau=line_values_3,
            last_record=last_record,
            delta_last_record=delta_last_record,
            maintenant=maintenant,
            date_aujourdhui_fr=date_aujourdhui_fr,
            duree_depuis_dernier_enregistrement_fr=duree_depuis_dernier_enregistrement_fr,
            last_record_display=last_record_display,
            class2=class2,
            arrosage_demande=arrosage_demande,
            dernieres=dernieres,
            historique_arrosages=historique_arrosages,
            heure_prog=heure_prog,
            selected_range=selected_range,
            range_options=RANGE_OPTIONS,
            chart_unit=range_conf['unit'],
            arrosage_instants=arrosage_instants,
        )
    return redirect(url_for('login'))


if __name__ == '__main__':
    # debug=True est utile en local, mais n'est jamais utilisé en prod
    # (le déploiement réel passe par gunicorn/wsgi.py, voir start.sh)
    application.run(host='0.0.0.0', port=1234, debug=True)
