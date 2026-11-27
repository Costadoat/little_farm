### local_settings.example.py
### Modèle à copier en local_settings.py, puis à remplir.
### local_settings.py contient des secrets : il est exclu de Git (.gitignore).

# Clé de session Flask : python3 -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY = ''

DATABASE = {
    'USER': '',
    'PASSWORD': '',
    'HOST': '',
    'PORT': 3306,
    'BASE': '',
}

# ---- Alerte réservoir bas -------------------------------------------------
# La carte envoie directement un niveau de remplissage en %
# (100% = plein, 0% = vide — voir RESERVOIR_DIST_PLEIN_CM / VIDE_CM côté
# Arduino et jardin.php). Seuil en dessous duquel le réservoir est
# considéré comme bas.
NIVEAU_ALERTE_PCT = 50

# Seuil au-dessus duquel on considère que le réservoir est de nouveau
# suffisamment rempli (hystérésis pour éviter les allers-retours d'alerte)
NIVEAU_RETOUR_NORMAL_PCT = 90

# Ne pas renvoyer d'email plus d'une fois toutes les X heures tant que
# le réservoir reste bas
DELAI_MIN_ENTRE_ALERTES_HEURES = 12

EMAIL_CONFIG = {
    'SMTP_HOST': '',
    'SMTP_PORT': 587,
    'SMTP_USER': '',
    'SMTP_PASSWORD': '',
    'EMAIL_FROM': '',
    'EMAIL_TO': '',
}
