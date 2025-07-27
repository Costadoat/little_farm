<?php
$user = "jardin"; /* Utilisateur */
$pawd = "Jardin75Arduino!"; /* Mot de passe */
$bdd = "little_farm"; /* Base de données */
$host = "localhost"; /* Hote */
$conn = new mysqli($host, $user, $pawd, $bdd);
$conn->query("SET NAMES 'utf8'");

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    if ($_POST["api_key"]=='tPmAT5Ab') {


        if ($_POST["Heure"]=='1')
            {
                date_default_timezone_set('Europe/Paris');
                echo '3,';
                echo date('N d m Y G i s');
            }
            else
            {
                $sql = "INSERT INTO `sensors`(`Temps`, `Humidite`, `Temperature`, `remplissage_reservoir`, `hygrometrie_terre_b`, `hygrometrie_terre_n`) VALUES (NOW(),".$_POST['Hum'].",".$_POST['Temp'].",".$_POST['Dist'].",".$_POST['TBlanc'].",".$_POST['TNoir'].")";
				$result = $conn->query($sql);
				echo '1,1';
			}
      }
      else
      {
      echo '55';
      }
 }
?>
