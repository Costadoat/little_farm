-- À exécuter une fois sur la base little_farm avant de déployer le nouveau code.

-- Historique des arrosages (déclenchés par programmation OU par le bouton web)
CREATE TABLE IF NOT EXISTS arrosages (
    Id INT AUTO_INCREMENT PRIMARY KEY,
    Debut DATETIME NOT NULL,
    Duree INT NOT NULL,               -- durée en secondes
    Source VARCHAR(20) NOT NULL       -- 'programme' ou 'web'
);

-- Mémorise le dernier état d'alerte réservoir pour éviter le spam d'emails
-- (une seule ligne, Id=1)
CREATE TABLE IF NOT EXISTS alertes (
    Id INT PRIMARY KEY,
    DerniereAlerte DATETIME NULL,
    EnAlerte TINYINT(1) NOT NULL DEFAULT 0
);
INSERT INTO alertes (Id, DerniereAlerte, EnAlerte)
VALUES (1, NULL, 0)
ON DUPLICATE KEY UPDATE Id = Id;

-- S'assurer que la table reglages a bien ses deux lignes (arrosage à distance)
INSERT INTO reglages (Id, valeur) VALUES (1, 0), (2, 120)
ON DUPLICATE KEY UPDATE valeur = valeur;
