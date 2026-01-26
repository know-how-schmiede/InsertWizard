# InsertWizard - Fusion 360 Heat-Set Insert Helper

InsertWizard is a Fusion 360 add-in that creates precise heat-set insert holes from sketch points. Pick a preset, select points, and the add-in generates the cuts (and optional chamfers) for you.

## Features
- One-click hole creation from sketch points (multi-select supported).
- Preset library in `presets.json` (e.g., Ruthex, CNC Kitchen, 3D-Jake, ISO-style defaults).
- Optional chamfer with selectable size.
- Parametric features that remain fully editable in Fusion 360.
- Automatic naming and grouping per run.

## Naming and grouping
- Each extrusion created in a run is named: `<Manufacturer>_<Thread>-<N>`
  - Example: `ruthex_M3-1`
  - Whitespace in the thread name is removed (e.g., `M3 kurz` -> `M3kurz`).
- All features created in a single run (extrusions and chamfers) are grouped in the timeline.
  - Group name: `group_<Manufacturer>_<Thread>-<N>`

## Presets file
Presets are loaded from `presets.json` in the add-in root. You can add your own by extending the list:

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
1. Download the latest release ZIP.
2. Extract the folder into your Fusion 360 Add-Ins directory:
   - Windows: `%AppData%\Roaming\Autodesk\Autodesk Fusion 360\API\AddIns`
   - macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns`
3. Start Fusion 360.
4. Open **Add-Ins** and start **InsertWizard**.

## Usage
1. Create a sketch and place points where inserts should be located.
2. Run InsertWizard (Solid workspace -> Create panel).
3. Select one or more sketch points (all from the same sketch).
4. Choose a preset (e.g., `ruthex M3`).
5. Adjust diameter/depth if needed and select a chamfer option.
6. Click **OK**.

## License
MIT License - see `LICENSE` for details.

## Support the project
If you want to support the project, you can contribute via the Amazon wishlist: https://www.amazon.de/hz/wishlist/ls/LHL8DJWGYH8D?ref_=wl_share
