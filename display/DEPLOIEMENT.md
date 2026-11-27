# Déploiement des nouveautés

## 1. Base de données
Exécuter `schema_updates.sql` sur `little_farm` (crée les tables
`arrosages` et `alertes`, vérifie `reglages`).

## 2. Alerte réservoir bas
1. Remplir les identifiants SMTP dans `local_settings.py` (section `EMAIL_CONFIG`).
2. Ajuster `NIVEAU_ALERTE_PCT` / `NIVEAU_RETOUR_NORMAL_PCT` (en %) selon
   tes préférences — ces seuils s'appliquent au niveau déjà calculé en
   pourcentage par la carte (voir `RESERVOIR_DIST_PLEIN_CM` / `VIDE_CM`
   dans le sketch Arduino et `jardin.php` pour le calibrage cm -> %).
3. Ajouter au crontab du serveur (`crontab -e`) :
   ```
   */15 * * * * /django/jardin/mvpappenv/bin/python /django/jardin/alerte_reservoir.py
   ```
   (adapter le chemin vers ton venv et le script)

## 3. Historique des arrosages
Rien à configurer : dès que l'Arduino est reflashé avec le nouveau
`Jardin.ino` et que `jardin.php` est mis à jour, chaque arrosage
(programmé ou déclenché depuis le site) apparaît automatiquement dans
la nouvelle carte "Historique des arrosages".

## 4. HTTPS
Voir `nginx_jardin.conf` pour la configuration du reverse proxy et les
commandes certbot. Les réglages `SESSION_COOKIE_SECURE` /
redirection HTTP→HTTPS sont déjà en place dans `display.py`, ils ne
prennent effet qu'une fois Nginx + certificat installés devant gunicorn.

Point d'attention : la communication ESP8266 → `jardin.php` reste en
HTTP simple, car elle circule uniquement sur ton réseau local (derrière
ta box) et est protégée par la clé API. Passer aussi cette liaison en
HTTPS est possible mais demande plus de travail côté ESP8266 (gestion
de certificat avec `WiFiClientSecure`, plus gourmand en mémoire) — à
envisager seulement si ce trafic sort un jour de ton réseau local.

---

# Ajout novembre 2026 : température intérieure + système extérieur débranchable

## 1. Câblage de la sonde DS18B20 (version étanche, 3 fils)

| Fil de la sonde          | Broche Raspberry Pi            |
|--------------------------|--------------------------------|
| Rouge (VDD)              | Broche 1 — 3,3 V               |
| Noir (GND)               | Broche 6 — GND                 |
| Jaune (ou blanc) — DATA  | Broche 7 — GPIO4               |

+ une résistance de **4,7 kΩ entre DATA (broche 7) et 3,3 V (broche 1)**.

- Toujours le **3,3 V**, jamais le 5 V : les GPIO de la Pi ne supportent pas le 5 V.
- Sans la résistance, la sonde n'est pas détectée (ou lit 85 °C / -127 °C).
- Si votre sonde est livrée sur un petit module avec bornier, la résistance
  y est souvent déjà soudée.
- Câble long (plus de 5 m) : passer la résistance à 2,2 kΩ si les lectures
  deviennent instables.

## 2. Activer le bus 1-Wire

```
sudo nano /boot/firmware/config.txt      # (/boot/config.txt sur les anciennes versions)
# ajouter à la fin :
dtoverlay=w1-gpio
sudo reboot
```
Vérification : `ls /sys/bus/w1/devices/` doit afficher un dossier `28-xxxxxxxxxxxx`.

## 3. Base de données
Exécuter de nouveau `schema_updates.sql` (il ne recrée rien d'existant) :
crée la table `temperature_interieure` et le réglage `reglages.Id=10`.

## 4. Lecture automatique
Copier `lecture_ds18b20.py` à côté de `display.py` (il réutilise `local_settings.py`), puis :
```
cd /sites/jardin/display
/sites/jardin/myenv/bin/python lecture_ds18b20.py --test    # affiche la température, n'écrit rien
crontab -e
*/5 * * * * cd /sites/jardin/display && /sites/jardin/myenv/bin/python lecture_ds18b20.py >> /sites/jardin/display/logs/ds18b20.log 2>&1
```

## 5. Débrancher le système extérieur
Sur la page d'accueil, carte « Système extérieur » → **Débrancher** :
- la partie jardin (mesures, arrosage, graphes) est masquée, bandeau neutre au lieu du bandeau rouge ;
- `alert_check.py` et `alerte_reservoir.py` n'envoient plus d'email ;
- la température intérieure continue de s'afficher.

Au retour, cliquer sur **Rebrancher** : l'alerte « pas de donnée depuis 24h »
laisse alors 12h à l'ESP pour renvoyer des mesures avant de prévenir.

## Fichiers modifiés
`display.py`, `templates/home.html`, `static/style.css`, `alert_check.py`,
`alerte_reservoir.py`, `schema_updates.sql` — nouveau : `lecture_ds18b20.py`.
`jardin.php` et le sketch Arduino ne changent pas.
