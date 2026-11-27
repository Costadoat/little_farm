# Florentina — récapitulatif mensuel des lundis

Script Python qui lit un agenda Google, compte les lundis travaillés du mois écoulé (en excluant les jours fériés français) et envoie par e-mail un récapitulatif avec le montant dû (26 € par lundi). En cas d'erreur, un e-mail d'alerte est envoyé.

Le script est lancé chaque mardi à 9 h par un timer systemd. Il n'envoie le récapitulatif qu'une fois par mois (le dernier mois traité est mémorisé dans `dernier_envoi.txt`).

## Contenu

| Fichier | Rôle |
|---|---|
| `florentina.py` | Script principal (Google Agenda en lecture seule + envoi SMTP) |
| `florentina.service` | Service systemd (oneshot) |
| `florentina.timer` | Déclenchement chaque mardi à 9 h (`Persistent=true` : rattrapage si la machine était éteinte) |
| `florentina.sh` | Lancement manuel |
| `florentina.env.example` | Modèle des variables d'environnement |
| `requirements.txt` | Dépendances Python |

## Fichiers non versionnés (secrets)

Ces fichiers sont exclus par `.gitignore` et doivent être placés à la main sur le serveur :

- `florentina.env` : identifiants SMTP et destinataires (copier `florentina.env.example`) ;
- `credentials.json` : identifiants OAuth du projet Google Cloud (« application de bureau ») ;
- `token.json` : jeton d'accès Google Agenda, généré après autorisation ;
- `dernier_envoi.txt` : état, créé par le script.

## Installation

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp florentina.env.example florentina.env && chmod 600 florentina.env   # puis le remplir
```

### Autorisation Google Agenda

Le serveur n'a pas de navigateur : générez `token.json` sur un poste qui en a un (avec `credentials.json` et la portée `calendar.readonly`), puis copiez-le sur le serveur avec les droits `600`. Le script rafraîchit ensuite le jeton tout seul.

### Variables (`florentina.env`)

| Variable | Description |
|---|---|
| `SMTP_USER` / `SMTP_PASSWORD` | Compte SMTP (serveur `smtp.free.fr:587`, STARTTLS) |
| `SMTP_FROM` | Expéditeur (par défaut `SMTP_USER`) |
| `REPORT_TO` | Destinataire du récapitulatif |
| `ALERT_TO` | Destinataire des alertes d'erreur (par défaut `REPORT_TO`) |

### systemd

```bash
sudo cp florentina.service florentina.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now florentina.timer
systemctl list-timers florentina.timer      # prochaine exécution
sudo systemctl start florentina.service     # test immédiat
journalctl -u florentina.service            # journal
```

## Points à vérifier

Les chemins ne sont pas cohérents d'un fichier à l'autre ; harmonisez-les selon l'emplacement réel :

- `florentina.py` utilise `BASE = /home/renaud/Florentina` (pour `token.json` et `dernier_envoi.txt`) ;
- `florentina.service` utilise `/sites/Florentina` et `venv/` ;
- `florentina.sh` utilise `myenv/` et appelle `Florentina.py` avec une majuscule, alors que le fichier s'appelle `florentina.py`.
