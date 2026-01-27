# InsertWizard - Fusion 360 Heat-Set-Insert-Helfer

InsertWizard ist ein Fusion-360-Add-In, das praezise Bohrungen fuer Heat-Set Inserts aus Skizzenpunkten erzeugt. Preset waehlen, Punkte auswaehlen, und das Add-In erstellt die Schnitte (und optional Fasen).

## Features
- Ein-Klick-Bohrungen aus Skizzenpunkten (Mehrfachauswahl moeglich).
- Preset-Bibliothek in `presets.json` (z. B. Ruthex, CNC Kitchen, 3D-Jake, ISO-Standards).
- Optionale Fase mit waehlbarer Groesse.
- Zusaetzliche Schraubenbohrung ueber Gewinde-Durchmesser und Schrauben-Tiefe.
- Parametrische Features bleiben in Fusion 360 editierbar.
- Automatische Benennung und Gruppierung pro Ausfuehrung.

## Benennung und Gruppierung
- Jede erzeugte Extrusion wird benannt: `<Manufacturer>_<Thread>-<N>`
  - Beispiel: `ruthex_M3-1`
  - Leerzeichen im Gewinde werden entfernt (z. B. `M3 kurz` -> `M3kurz`).
- Alle in einem Lauf erzeugten Features (Extrusionen und Fasen) werden in der Timeline gruppiert.
  - Gruppenname: `group_<Manufacturer>_<Thread>-<N>`

## Presets-Datei
Die Presets werden aus `presets.json` im Add-In-Verzeichnis geladen. Eigene Presets koennen dort ergaenzt werden:

```json
{
  "presets": [
    {
      "Manufacturer": "ruthex",
      "Thread": "M3",
      "Diameter": 4.0,
      "Length": 5.7
    }
  ]
}
```

## Installation
1. Lade die aktuelle Release-ZIP herunter.
2. Entpacke den Ordner in dein Fusion-360-Add-Ins-Verzeichnis:
   - Windows: `%AppData%\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns`
   - macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns`
3. Starte Fusion 360.
4. Oeffne **Zusatzmodule** und starte **InsertWizard**.

## Bedienung
1. Erstelle eine Skizze und setze Punkte an die Einfuegepositionen.
2. Starte InsertWizard (Arbeitsbereich "Volumenkörper" -> Panel "Erstellen").
3. Waehle einen oder mehrere Skizzenpunkte (alle aus derselben Skizze).
4. Waehle ein Preset (z. B. `ruthex M3`).
5. Passe Durchmesser/Tiefe sowie Gewinde-Durchmesser/Schrauben-Tiefe an und waehle optional eine Fase.
6. Bestaetige mit **OK**.

## Lizenz
MIT-Lizenz - siehe `LICENSE`.
