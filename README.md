# Jardin — supervision du potager et de l'arrosage

Application web Flask, hébergée sur une Raspberry Pi, qui affiche les mesures envoyées par un ESP8266 placé au jardin (température, humidité, niveau du réservoir), l'historique des arrosages et la température intérieure lue par une sonde DS18B20. Le site permet aussi de déclencher un arrosage, et des scripts cron envoient des alertes par e-mail.

```
ESP8266 (jardin) ──HTTP + clé API──► jardin.php ──► MySQL/MariaDB (little_farm) ◄── display.py (Flask/gunicorn) ◄── nginx ◄── navigateur
Sonde DS18B20 (Raspberry) ──► lecture_ds18b20.py (cron) ──┘
```

## Contenu

| Fichier | Rôle |
|---|---|
| `display/display.py` | Application Flask : connexion, profil, tableau de bord, graphiques, réglages |
| `display/wsgi.py`, `display/start.sh` | Lancement via gunicorn (socket Unix `jardin_display.sock`) |
| `display/templates/`, `display/static/` | Gabarits HTML et CSS |
| `display/alert_check.py` | Cron : alerte si aucune mesure depuis 24 h |
| `display/alerte_reservoir.py` | Cron : alerte si le réservoir est bas |
| `display/lecture_ds18b20.py` | Cron : lecture de la sonde de température intérieure |
| `display/schema_updates.sql` | Mise à jour du schéma de la base (idempotent) |
| `display/nginx_jardin.conf` | Exemple de reverse proxy nginx + HTTPS |
| `display/local_settings.example.py` | Modèle de configuration |
| `display/DEPLOIEMENT.md` | Notes de déploiement détaillées (câblage de la sonde, 1-Wire, cron) |

Le sketch Arduino (`Jardin.ino`) et `jardin.php`, qui reçoit les mesures de l'ESP8266, ne font pas partie de ce dépôt.

## Installation

```bash
python3 -m venv /sites/jardin/myenv
/sites/jardin/myenv/bin/pip install -r display/requirements.txt   # nécessite libmysqlclient-dev
cd display
cp local_settings.example.py local_settings.py   # puis renseigner la base, le SMTP et SECRET_KEY
mysql little_farm < schema_updates.sql
./start.sh
```

`local_settings.py` contient les secrets : il est exclu de Git. La clé de session Flask est lue dans `local_settings.SECRET_KEY` (ou, à défaut, dans la variable d'environnement `JARDIN_SECRET_KEY`).

### Tâches planifiées (`crontab -e`)

```cron
*/5  * * * * cd /sites/jardin/display && /sites/jardin/myenv/bin/python lecture_ds18b20.py >> logs/ds18b20.log 2>&1
*/15 * * * * cd /sites/jardin/display && /sites/jardin/myenv/bin/python alerte_reservoir.py
*/20 * * * * cd /sites/jardin/display && /sites/jardin/myenv/bin/python alert_check.py >> logs/alert.log 2>&1
```

### Système extérieur débranchable

Sur la page d'accueil, le bouton **Débrancher** de la carte « Système extérieur » masque la partie jardin et coupe les alertes e-mail (pendant l'hiver par exemple). La température intérieure reste affichée. Voir `display/DEPLOIEMENT.md`.
