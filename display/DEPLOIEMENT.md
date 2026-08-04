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
