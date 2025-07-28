	# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from time import sleep
from datetime import datetime, timedelta
import locale

start_time=datetime.now()- timedelta(days=2)

from local_settings import DATABASE

application = Flask(__name__)

# Change this to your secret key (can be anything, it's for extra protection)
application.secret_key = 'zffuiaozeguzbeunf13znfepZU11213333BV'

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

@application.route('/login/', methods=['GET', 'POST'])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM comptes WHERE username = %s AND password = %s', (username, password,))
        # Fetch one record and return result
        account = cursor.fetchone()
        # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # Account doesnt exist or username/password incorrect
            msg = "Le mot de passe n'est pas correct"
    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)

# http://localhost:5000/python/logout - this will be the logout page
@application.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))


# http://localhost:5000/pythinlogin/register - this will be the registration page, we need to use both GET and POST requests
@application.route('/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
         # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM comptes WHERE username = %s', (username,))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Le compte existe déjà'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = "L'adresse mail n'est pas valide."
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Le pseudo ne doit contenir que des chiffres et des lettres !'
        elif not username or not password or not email:
            msg = 'Remplir le formulaire !'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO comptes VALUES (NULL, %s, %s, %s)', (username, password, email,))
            mysql.connection.commit()
            msg = "L'enregistrement est validé !"
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Remplir le formulaire !'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

# http://localhost:5000/pythinlogin/profile - this will be the profile page, only accessible for loggedin users
@application.route('/profile')
def profile():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM comptes WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

class data:
    def __init__(self, backgroundColor, borderColor, nom, values):
        self.backgroundColor = backgroundColor
       	self.borderColor = borderColor
        self.nom = nom
        self.values = values


# http://localhost:5000/pythinlogin/home - this will be the home page, only accessible for loggedin users
@application.route('/', methods=['GET', 'POST'])
def home():
    # Check if user is loggedin
    if 'loggedin' in session and session['id']==1:
        # User is loggedin show them the home page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if request.method == 'POST':
            if request.form.getlist('bouton_allume') == ['on']:
                cursor.execute('UPDATE reglages SET valeur=1 WHERE Id=1')
                mysql.connection.commit()
            else:
                cursor.execute('UPDATE reglages SET valeur=0 WHERE Id=1')
                mysql.connection.commit()
            print(request.form)
            if 'bouton_2min' in request.form:
                cursor.execute('UPDATE reglages SET valeur=1 WHERE Id=1')
                mysql.connection.commit()
                cursor.execute('UPDATE reglages SET valeur=120 WHERE Id=2')
                mysql.connection.commit()
            elif 'bouton_stop' in request.form:
                cursor.execute('UPDATE reglages SET valeur=0 WHERE Id=1')
                mysql.connection.commit()
                cursor.execute('UPDATE reglages SET valeur=-1 WHERE Id=2')
                mysql.connection.commit()
            sleep(2)
        Temps=[]
        Humidite_values=[]
        Temperature_values=[]
        Hygrometrie_terre_blanc_values=[]
        Hygrometrie_terre_noir_values=[]
        Remplissage_reservoir_values=[]
        cursor.execute("SELECT * FROM(SELECT * FROM sensors ORDER BY `Id` DESC LIMIT 500) t1 ORDER BY t1.Id")
#        cursor.execute("SELECT * FROM sensors WHERE Temps> '%s'" % (start_time))
        
        myresult = cursor.fetchall()
        for x in myresult:
            Temps.append(x['Temps'])
            Humidite_values.append([x['Temps'],x['Humidite']])
            Temperature_values.append([x['Temps'],x['Temperature']])
            Hygrometrie_terre_blanc_values.append([x['Temps'],x['hygrometrie_terre_b']])
            Hygrometrie_terre_noir_values.append([x['Temps'],x['hygrometrie_terre_n']])
            Remplissage_reservoir_values.append([x['Temps'],x['remplissage_reservoir']])
        cursor.execute("SELECT * FROM reglages WHERE Id=1")
        reglage = cursor.fetchone()
        cursor.execute("SELECT Temps FROM sensors ORDER BY Id DESC LIMIT 1")
        records = cursor.fetchone()
        last_record=records['Temps']
        line_labels=Temps
        Temperature=data("rgba(186,125,125,1)","rgba(186,125,125,1)",'Température',Temperature_values)
        Humidite=data("rgba(151,187,205,1)","rgba(151,187,205,1)",'Humidité',Humidite_values)
        Hygrometrie_terre_blanc=data("rgba(153,204,255,1)","rgba(153,204,255,1)",'Hygrométrie terre (blanc)',Hygrometrie_terre_blanc_values)
        Hygrometrie_terre_noir=data("rgba(0,128,255,1)","rgba(0,128,255,1)",'Hygrométrie terre (noir)',Hygrometrie_terre_noir_values)
        Niveau_eau=data("rgba(245,75,39,1)","rgba(245,75,39,1)","Niveau eau",Remplissage_reservoir_values)
        line_values_1=[Temperature,Humidite]
        line_values_2=[Hygrometrie_terre_blanc,Hygrometrie_terre_noir]
        line_values_3=[Niveau_eau]
        line_values=[Temperature,Humidite,Hygrometrie_terre_blanc,Hygrometrie_terre_noir, Niveau_eau]
        delta_last_record=int((datetime.now()-last_record).total_seconds())
        if delta_last_record>600:
            class2='error'
        else:
            class2='ok'

        return render_template('home.html', username=session['username'], title='Capteurs', max=100, labels=line_labels, datasets=line_values, datasets_temperature=line_values_1, datasets_hygrometrie=line_values_2, datasets_niveau=line_values_3, last_record=last_record, delta_last_record=delta_last_record, maintenant=datetime.now(), class2=class2)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


if __name__ == '__main__':
    application.run(host='0.0.0.0', port=1234, debug=True)
