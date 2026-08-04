<?php
// ==========================================================
//  jardin.php — point d'entrée appelé par l'ESP8266
// ==========================================================
// IMPORTANT : ces identifiants sont ici en clair pour rester
// simple, mais comme ils ont été partagés dans cette session,
// pense à les changer (mot de passe MySQL + api_key) une fois
// que tu auras mis ce fichier en place.
$user = "jardin";
$pawd = "Jardin75Arduino!";
$bdd  = "little_farm";
$host = "localhost";
$API_KEY = "tPmAT5Ab";

// Calibrage du capteur ultrason, doit rester cohérent avec les
// constantes RESERVOIR_DIST_PLEIN_CM / RESERVOIR_DIST_VIDE_CM du sketch Arduino.
const RESERVOIR_DIST_PLEIN_CM = 26.0; // 100 %
const RESERVOIR_DIST_VIDE_CM  = 54.0; //   0 %

$conn = @new mysqli($host, $user, $pawd, $bdd);
if ($conn->connect_error) {
    http_response_code(500);
    echo '0,DB_ERROR';
    exit;
}
$conn->query("SET NAMES 'utf8'");

if ($_SERVER["REQUEST_METHOD"] !== "POST") {
    http_response_code(405);
    exit;
}

if (!isset($_POST["api_key"]) || !hash_equals($API_KEY, trim((string) $_POST["api_key"]))) {
    echo '55';
    exit;
}

// ---- 1) Demande de réglage de l'heure ------------------------------------
if (isset($_POST["Heure"]) && trim($_POST["Heure"]) === '1') {
    date_default_timezone_set('Europe/Paris');
    echo '3,' . date('N d m Y G i s');
    exit;
}

// ---- 2) Sondage : la carte demande s'il y a un ordre en attente ----------
// (déclenché toutes les ~10s par l'Arduino, voir Jardin.ino)
if (isset($_POST["poll"]) && trim($_POST["poll"]) === '1') {
    $stmt = $conn->prepare("SELECT valeur FROM reglages WHERE Id = 1");
    $stmt->execute();
    $stmt->bind_result($etat);
    $stmt->fetch();
    $stmt->close();

    $stmt = $conn->prepare("SELECT valeur FROM reglages WHERE Id = 4");
    $stmt->execute();
    $stmt->bind_result($heureProg);
    $stmt->fetch();
    $stmt->close();
    $heureProg = ($heureProg !== null) ? intval($heureProg) : 20;

    $stmt = $conn->prepare("SELECT valeur FROM reglages WHERE Id = 5");
    $stmt->execute();
    $stmt->bind_result($minuteProg);
    $stmt->fetch();
    $stmt->close();
    $minuteProg = ($minuteProg !== null) ? intval($minuteProg) : 0;

    if ($etat == 1) {
        $stmt = $conn->prepare("SELECT valeur FROM reglages WHERE Id = 2");
        $stmt->execute();
        $stmt->bind_result($duree);
        $stmt->fetch();
        $stmt->close();

        $duree = ($duree !== null && $duree > 0) ? intval($duree) : 120;

        // On acquitte tout de suite la demande pour ne pas redéclencher en boucle
        $stmt = $conn->prepare("UPDATE reglages SET valeur = 0 WHERE Id = 1");
        $stmt->execute();
        $stmt->close();

        // 5 = "démarre l'arrosage pendant N secondes", suivi de l'heure programmée
        echo '5,' . $duree . ',' . $heureProg . ',' . $minuteProg;
        exit;
    }
    // 0 = rien à arroser ; on renvoie quand même l'heure programmée pour que
    // la carte reste synchronisée si elle a été changée depuis le site
    echo '0,' . $heureProg . ',' . $minuteProg;
    exit;
}

// ---- 3) Signalement d'un arrosage démarré (pour l'historique) ------------
if (isset($_POST["arrosage_event"]) && trim($_POST["arrosage_event"]) === '1') {
    $duree  = isset($_POST['Duree']) ? intval($_POST['Duree']) : 0;
    $source = isset($_POST['Source']) ? substr(trim($_POST['Source']), 0, 20) : 'inconnu';

    $stmt = $conn->prepare("INSERT INTO arrosages (Debut, Duree, Source) VALUES (NOW(), ?, ?)");
    $stmt->bind_param("is", $duree, $source);
    $stmt->execute();
    $stmt->close();

    echo '1,1';
    exit;
}

// ---- 4) Enregistrement d'une mesure ---------------------------------------
if (!isset($_POST['Temp'], $_POST['Hum'], $_POST['Dist'], $_POST['TBlanc'], $_POST['TNoir'])) {
    echo '2,Champs manquants';
    exit;
}

$temp   = floatval($_POST['Temp']);
$hum    = floatval($_POST['Hum']);
$dist   = floatval($_POST['Dist']);
$tblanc = floatval($_POST['TBlanc']);
$tnoir  = floatval($_POST['TNoir']);

// Niveau de remplissage en % : la carte l'envoie désormais directement
// (champ Niveau). On garde un calcul de secours à partir de Dist pour
// rester compatible avec un firmware plus ancien qui ne l'enverrait pas.
if (isset($_POST['Niveau'])) {
    $niveau = floatval($_POST['Niveau']);
} else {
    $niveau = (RESERVOIR_DIST_VIDE_CM - $dist)
             / (RESERVOIR_DIST_VIDE_CM - RESERVOIR_DIST_PLEIN_CM) * 100.0;
}
if ($niveau < 0)   $niveau = 0;
if ($niveau > 100) $niveau = 100;

$stmt = $conn->prepare(
    "INSERT INTO sensors (Temps, Humidite, Temperature, remplissage_reservoir, hygrometrie_terre_b, hygrometrie_terre_n)
     VALUES (NOW(), ?, ?, ?, ?, ?)"
);
$stmt->bind_param("ddddd", $hum, $temp, $niveau, $tblanc, $tnoir);

if ($stmt->execute()) {
    echo '1,1';
} else {
    echo '2,' . $conn->error;
}
$stmt->close();
$conn->close();
