# master-thesis_moire_detection
 
Der Ordner "70_Abbildungen_MA_errechnen" enthält Scripte, mit denen die in der Masterarbeit verwendeten Abbildungen erstellt wurden.
Im Ordner "80_Auswertungen" die Ergebnisse der Klassifizierungs- und Generierungsmodelle verarbeitet und bewertet. "30_data_tool" enthält Hilfsfunktionen zur Interaktion mit der Datenbank und den vorgehaltenen Dateien.
In "60_Code" liegen Programme zur Erzeugung von Masken, Umwandlung der PDF-Seiten in Rasterabbildungen usw. Der Unterordner "generate_pattern" enthält Scripte zur Erstellung von Patternvorlagen. Der Unterordner "Model" enthält Scripte zur Erstellung Klassifizierungskacheln sowie zum Training von Klassifizierungsmodellen. Der Unterordner "Musterueberlagerung" enhält Programme zur Erzeugung synthetischer Moirés. Die Erzeugung neuer synthetischer Moirés sowie das Training von Modellen wird nachfolgend beschrieben.

## Neue synthetische Moirés erzeugen
1. Das Script "musterueberlagerung_get_samples.py" ausführen.
2. Das Script "musterueberlagerung.py" ausführen.
3. Das Script "import_musterueberlagerung_batches" ausführen.

## Modell trainieren
1. In der Datei "run_config.json" die Parameter anpassen.
2. Das Script "train_model_server" ausführen.
3. Das Script "calc_model_results" ausführen, um die Ergebnisse des Modells zu errechnen.