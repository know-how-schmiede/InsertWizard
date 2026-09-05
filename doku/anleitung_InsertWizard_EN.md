# InsertWizard Guide Ver. 0.4.1
![InsertWizard Logo](./images/Logo_InsertWizard_1024.png)

## Installation

1. Download the latest release ZIP and extract it.
2. Copy the `InsertWizard` folder into your Fusion Add-Ins directory:
   - Windows: `%AppData%\\Roaming\\Autodesk\\Autodesk Fusion 360\\API\\AddIns`
   - macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns`
3. Restart Fusion 360.
4. Open **Add-Ins** and enable **InsertWizard**.

## Launching InsertWizard

After installation, InsertWizard can be started from this menu:

**Design / Solid / Create**

After launching, the InsertWizard dialog opens.

![Launch InsertWizard](./images/InsertWizard-AddIn-Aufrufen.png)

## InsertWizard Dialog

Use the "Select" button to pick sketch points where heat-set insert holes should be created.

Dialog settings:
- Manufacturer: filters presets by manufacturer.
- Preset: fills Diameter 1 and Depth 1 with preset values.
- Diameter 1 / Depth 1: dimensions for the insert hole; can be adjusted manually.
- Thread Diameter / Screw Depth: clearance hole for the screw; set from preset or default table and can be overridden.
- Create Chamfer / Chamfer: adds a chamfer with the selected size.
- Keep point sketch visible: keeps the sketch with points visible.

### Reuse / Keep point sketch visible

- Enable "Keep point sketch visible" to keep the sketch visible after execution.
- This allows multiple runs on the same sketch without re-showing it.
- Only points from the same sketch are accepted.

### Important Notes

- Multiple points are supported, but only from the same sketch.
- The "Manufacturer" field filters presets. "Default M3" is always shown.
- Thread diameter is taken from the preset or a default table (e.g., M3=3.2 mm, M4=4.3 mm) and can be overridden.
- Screw depth starts as: `Depth 1 + int(Thread Diameter)` and can be adjusted.
- A screw clearance hole is also created at the center and cut to the screw depth.

![InsertWizard dialog overview](./images/InsertWizard-AddIn-Uebersicht.png)

## Design History

In the timeline, all generated features are grouped and named after the preset. You can expand the group and edit each extrusion/chamfer. This allows you to adjust diameter, depth, thread diameter, or screw depth for each feature. Changes only affect the specific feature in the group.

![Design history in Fusion](./images/InsertWizard-Gruppe.png)

![Group contents](./images/InsertWizard-GruppeInhalt.png)

## Troubleshooting

- Dialog does not appear: verify the add-in is enabled in **Add-Ins** and the folder is in the correct Add-Ins directory.
- Points cannot be selected: they must be sketch points and all points must be from the same sketch.
- Presets missing or empty: validate `presets.json` and check the Add-In logs in the Text Command window.
- Language mismatch: restart Fusion or set an override in `InsertWizard/config.py`.
- Screw depth or thread diameter looks wrong: adjust the values manually in the dialog.

## Advanced Settings

- Language follows Fusion preferences automatically. If no translation is available, English is used.
- Optional override in `InsertWizard/config.py`: `LANGUAGE = 'de' | 'en' | 'fr' | 'es' | 'it' | 'pl' | 'auto'`.
- Presets can be modified or extended in `InsertWizard/presets.json`.
