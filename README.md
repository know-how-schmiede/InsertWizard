# InsertWizard
🚀 Fusion 360 Add-In zur automatisierten Erstellung von Bohrungen für Heat-Set Inserts (z.B. Ruthex). Skizzenpunkte wählen, Preset laden, fertig!

# InsertWizard 🛠️ – Fusion 360 Heat-Set Helper

**Präzision, die schmilzt: Perfekte Heat-Set Bohrungen auf Knopfdruck.**

InsertWizard ist ein Add-In für Autodesk Fusion 360, das den Workflow für 3D-Druck-Konstruktionen beschleunigt. Statt manuell Durchmesser, Tiefen und Fasen für Einschmelzhülsen einzugeben, generiert dieses Tool basierend auf Skizzenpunkten automatisch die exakten Bohrungsgeometrien.

## ✨ Features
* **Ein-Klick-Generierung:** Wähle einfach Skizzenpunkte aus, und das Tool platziert die Bohrungen.
* **Hersteller-Presets:** Vordefinierte Maße für gängige Hülsen (z.B. Ruthex, CNC Kitchen) für M2, M3, M4, M5 und M6.
* **Automatischer Wulst-Schutz:** Erstellt automatisch die notwendige Senkung/Fase, um Materialverdrängung nach außen zu verhindern.
* **Parametrisch:** Alle Bohrungen bleiben innerhalb von Fusion 360 bearbeitbar.

## 🚀 Installation
1. Lade die aktuelle [Release-ZIP](#) herunter.
2. Entpacke den Ordner in deinen Fusion 360 Add-Ins Ordner:
   - **Windows:** `%AppData%\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns`
   - **macOS:** `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns`
3. Starte Fusion 360.
4. Öffne das Menü **Zusatzmodule (Alt+S)** und starte **InsertWizard**.

## 📖 Bedienung
1. Erstelle eine Skizze und setze **Punkte** an die Stellen, an denen Inserts platziert werden sollen.
2. Starte das Plugin über den Reiter "Konstruieren" -> "Erstellen".
3. Wähle die Punkte aus.
4. Wähle den Typ der Hülse (z.B. Ruthex M3) aus dem Dropdown-Menü.
5. Bestätige mit **OK**.



## 🛠️ Unterstützte Hardware
Standardmäßig sind Presets für folgende Hersteller enthalten:
* **Ruthex** (Original & Slim)
* **CNC Kitchen**
* **Standard-ISO** (für generische Hülsen)

## 📄 Lizenz
Dieses Projekt ist unter der MIT-Lizenz lizenziert – siehe [LICENSE](LICENSE) für Details.

---
*Entwickelt für Maker und Profis, die Wert auf passgenaue Verbindungen legen.*
