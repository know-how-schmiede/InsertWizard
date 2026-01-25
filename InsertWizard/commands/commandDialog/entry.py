import adsk.core
import adsk.fusion
import json
import os
from ...lib import fusionAddInUtils as futil
from ... import config
from ... import version
app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = f'InsertWizard v{version.__version__}'
CMD_Description = 'InsertWizard Dialog'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidCreatePanel'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

PRESETS = []
PRESET_BY_NAME = {}

PRESET_FILE = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'presets.json')
)


def _preset_display_name(preset: dict) -> str:
    manufacturer = str(preset.get('Manufacturer', preset.get('Hersteller', 'Preset'))).strip()
    thread = str(preset.get('Thread', preset.get('Gewinde', ''))).strip()
    if thread:
        return f'{manufacturer} {thread}'
    return manufacturer


def _load_presets() -> list:
    try:
        with open(PRESET_FILE, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        presets = data.get('presets', data) if isinstance(data, dict) else data
        if not isinstance(presets, list):
            raise ValueError('Ungültiges Preset-Format')
    except Exception as exc:
        futil.log(f'Preset-Datei konnte nicht geladen werden: {exc}', force_console=True)
        presets = []

    if not presets:
        presets = [
            {
                'Hersteller': 'Default',
                'Gewinde': 'M3',
                'durchmesser': 10.0,
                'Länge': 5.0
            }
        ]

    return presets


def _apply_preset(preset: dict, diameter_input: adsk.core.ValueCommandInput, depth_input: adsk.core.ValueCommandInput):
    if not preset:
        return
    diameter = preset.get('Diameter', preset.get('durchmesser', None))
    depth = preset.get('Length', preset.get('Länge', None))

    if diameter is not None:
        diameter_input.expression = f'{diameter} mm'
    if depth is not None:
        depth_input.expression = f'{depth} mm'


# Executed when add-in is run.
def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def)

    # Specify if the command is promoted to the main toolbar. 
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Created Event')

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    # Show a simple dialog that displays the add-in name.
    inputs.addTextBoxCommandInput('title', '', CMD_NAME, 1, True)

    # Selection input for one or more sketch points.
    points_input = inputs.addSelectionInput('points', 'Punkte', 'Skizzenpunkte auswählen')
    points_input.addSelectionFilter('SketchPoints')
    points_input.setSelectionLimits(1, 0)
    try:
        points_input.isMultiSelectEnabled = True
    except:
        # Older API versions may not expose this property.
        pass

    # Preset selection.
    global PRESETS, PRESET_BY_NAME
    PRESETS = _load_presets()
    PRESET_BY_NAME = {}
    preset_input = inputs.addDropDownCommandInput(
        'preset',
        'Preset',
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    for index, preset in enumerate(PRESETS):
        name = _preset_display_name(preset)
        if name in PRESET_BY_NAME:
            name = f'{name} ({index + 1})'
        PRESET_BY_NAME[name] = preset
        preset_input.listItems.add(name, index == 0, '')

    # Diameter input in mm with a default of 10 mm.
    default_diameter = adsk.core.ValueInput.createByString('10 mm')
    inputs.addValueInput('diameter', 'Durchmesser 1', 'mm', default_diameter)

    # Depth input in mm.
    default_depth = adsk.core.ValueInput.createByString('5 mm')
    inputs.addValueInput('depth', 'Tiefe 1', 'mm', default_depth)

    diameter_input: adsk.core.ValueCommandInput = inputs.itemById('diameter')
    depth_input: adsk.core.ValueCommandInput = inputs.itemById('depth')
    if preset_input.listItems.count > 0:
        _apply_preset(PRESET_BY_NAME[preset_input.listItems.item(0).name], diameter_input, depth_input)

    # Chamfer on/off toggle.
    inputs.addBoolValueInput('chamfer_enabled', 'Fase erstellen', True, '', True)

    # Chamfer size selection.
    chamfer_input = inputs.addDropDownCommandInput(
        'chamfer',
        'Fase',
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    chamfer_items = chamfer_input.listItems
    chamfer_items.add('0.2 mm', True, '')
    chamfer_items.add('0.4 mm', False, '')
    chamfer_items.add('0.6 mm', False, '')

    # Connect to the events that are needed by this command.
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Execute Event')

    inputs = args.command.commandInputs
    points_input: adsk.core.SelectionCommandInput = inputs.itemById('points')
    diameter_input: adsk.core.ValueCommandInput = inputs.itemById('diameter')
    depth_input: adsk.core.ValueCommandInput = inputs.itemById('depth')
    chamfer_enabled: adsk.core.BoolValueCommandInput = inputs.itemById('chamfer_enabled')
    chamfer_input: adsk.core.DropDownCommandInput = inputs.itemById('chamfer')

    if points_input.selectionCount < 1:
        ui.messageBox('Bitte mindestens einen Skizzenpunkt auswählen.')
        return

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        ui.messageBox('Kein aktives Design gefunden.')
        return

    radius = diameter_input.value / 2.0
    depth_value = abs(depth_input.value)
    chamfer_value = None
    if chamfer_enabled.value:
        chamfer_value = adsk.core.ValueInput.createByString(chamfer_input.selectedItem.name)
        futil.log(f'Fase: {chamfer_input.selectedItem.name}', force_console=True)
    else:
        futil.log('Fase: deaktiviert', force_console=True)

    selection_count = points_input.selectionCount
    futil.log(f'Ausgewählte Punkte: {selection_count}', force_console=True)

    centers = []
    base_sketch = None
    mismatched_sketch = False
    for i in range(selection_count):
        try:
            selection = points_input.selection(i)
        except:
            futil.log(f'Ungültiger Auswahlindex: {i}', force_console=True)
            break
        entity = selection.entity
        if not entity:
            continue
        if not hasattr(entity, 'parentSketch') or not hasattr(entity, 'geometry'):
            continue

        sketch = entity.parentSketch
        if not base_sketch:
            base_sketch = sketch
        elif sketch != base_sketch:
            mismatched_sketch = True
            break
        sketch_center = entity.geometry
        model_center = None
        if hasattr(entity, 'worldGeometry') and entity.worldGeometry:
            model_center = entity.worldGeometry
        elif hasattr(sketch, 'sketchToModelSpace'):
            try:
                model_center = sketch.sketchToModelSpace(sketch_center)
            except:
                model_center = None
        if not model_center:
            model_center = sketch_center

        centers.append(
            (
                sketch,
                adsk.core.Point3D.create(sketch_center.x, sketch_center.y, sketch_center.z),
                adsk.core.Point3D.create(model_center.x, model_center.y, model_center.z)
            )
        )
        futil.log(
            f'Punkt {i + 1}: X={sketch_center.x:.3f} Y={sketch_center.y:.3f} Z={sketch_center.z:.3f}',
            force_console=True
        )

    if mismatched_sketch:
        ui.messageBox('Bitte nur Punkte aus derselben Skizze auswählen.')
        return

    if not centers:
        return

    base_sketch = centers[0][0]
    plane_entity = None
    plane_origin = None
    plane_normal = None
    if hasattr(base_sketch, 'referencePlane') and base_sketch.referencePlane:
        plane_entity = base_sketch.referencePlane
    elif hasattr(base_sketch, 'planarEntity') and base_sketch.planarEntity:
        plane_entity = base_sketch.planarEntity

    plane = None
    if plane_entity and hasattr(plane_entity, 'geometry'):
        plane = adsk.core.Plane.cast(plane_entity.geometry)
    if plane:
        plane_origin = plane.origin
        plane_normal = plane.normal

    target_sketch = base_sketch

    # Determine target bodies for the cut.
    target_bodies = adsk.core.ObjectCollection.create()
    face = adsk.fusion.BRepFace.cast(plane_entity)
    if face:
        target_bodies.add(face.body)
    else:
        for body in target_sketch.parentComponent.bRepBodies:
            if body.isSolid:
                target_bodies.add(body)

    if target_bodies.count == 0:
        futil.log('Kein Zielkörper im Component gefunden.', force_console=True)
        return

    bodies = []
    for i in range(target_bodies.count):
        bodies.append(target_bodies.item(i))

    def point_plane_distance(point: adsk.core.Point3D) -> float:
        if not plane_origin or not plane_normal:
            return 0.0
        vec = plane_origin.vectorTo(point)
        return abs(vec.dotProduct(plane_normal))

    def find_circle_edge(center_point: adsk.core.Point3D, ext_feature: adsk.fusion.ExtrudeFeature):
        tol = 0.02  # cm (0.2 mm)
        best_edge = None
        best_plane_dist = None

        if ext_feature:
            for face in ext_feature.sideFaces:
                cyl = adsk.core.Cylinder.cast(face.geometry)
                if not cyl:
                    continue
                if abs(cyl.radius - radius) > tol:
                    continue
                for edge in face.edges:
                    circle = adsk.core.Circle3D.cast(edge.geometry)
                    if not circle:
                        continue
                    if abs(circle.radius - radius) > tol:
                        continue
                    if circle.center.distanceTo(center_point) > tol:
                        continue
                    if plane_origin and plane_normal:
                        if point_plane_distance(circle.center) > tol:
                            continue
                    return edge

        for body in bodies:
            for edge in body.edges:
                circle = adsk.core.Circle3D.cast(edge.geometry)
                if not circle:
                    continue
                if abs(circle.radius - radius) > tol:
                    continue
                if circle.center.distanceTo(center_point) > tol:
                    continue

                plane_dist = point_plane_distance(circle.center)
                if best_plane_dist is None or plane_dist < best_plane_dist:
                    best_plane_dist = plane_dist
                    best_edge = edge
        return best_edge

    for _, sketch_center, model_center in centers:
        circle = target_sketch.sketchCurves.sketchCircles.addByCenterRadius(sketch_center, radius)

        profile = None
        fallback_profile = None
        for prof in target_sketch.profiles:
            for loop in prof.profileLoops:
                for curve in loop.profileCurves:
                    if curve.sketchEntity == circle:
                        if hasattr(loop, 'isOuter') and loop.isOuter:
                            profile = prof
                            break
                        fallback_profile = prof
                if profile:
                    break
            if profile:
                break

        if not profile:
            profile = fallback_profile

        if not profile:
            futil.log('Kein Profil für Kreis gefunden.', force_console=True)
            continue

        extrudes = target_sketch.parentComponent.features.extrudeFeatures
        success = False
        ext_feature = None
        for is_positive in (True, False):
            ext_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
            ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(depth_value))
            try:
                ext_input.participantBodies = target_bodies
            except:
                pass
            if hasattr(ext_input, 'isPositiveDirection'):
                ext_input.isPositiveDirection = is_positive
            elif not is_positive:
                ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-depth_value))
            try:
                ext_feature = extrudes.add(ext_input)
                success = True
                break
            except:
                continue

        if not success:
            futil.log('Kein Zielkörper zum Schneiden gefunden.', force_console=True)
            continue

        if chamfer_enabled.value:
            edge = find_circle_edge(model_center, ext_feature)
            if edge:
                try:
                    token = edge.entityToken
                except:
                    token = 'n/a'
                futil.log(f'Fasen-Kante gefunden: {token}', force_console=True)
                chamfer_feats = target_sketch.parentComponent.features.chamferFeatures
                single = adsk.core.ObjectCollection.create()
                single.add(edge)
                try:
                    chamfer_feat_input = chamfer_feats.createInput(single, False)
                    chamfer_feat_input.setToEqualDistance(chamfer_value)
                    chamfer_feats.add(chamfer_feat_input)
                except:
                    futil.log('Fase für diese Kante fehlgeschlagen.', force_console=True)
            else:
                futil.log('Keine passende Fasen-Kante gefunden.', force_console=True)


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    if not changed_input:
        return

    if changed_input.id == 'preset':
        preset = PRESET_BY_NAME.get(changed_input.selectedItem.name)
        if not preset:
            return
        diameter_input: adsk.core.ValueCommandInput = args.inputs.itemById('diameter')
        depth_input: adsk.core.ValueCommandInput = args.inputs.itemById('depth')
        _apply_preset(preset, diameter_input, depth_input)


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Validate Input Event')

    inputs = args.inputs
    points_input: adsk.core.SelectionCommandInput = inputs.itemById('points')
    diameter_input: adsk.core.ValueCommandInput = inputs.itemById('diameter')
    depth_input: adsk.core.ValueCommandInput = inputs.itemById('depth')

    if points_input.selectionCount < 1 or diameter_input.value <= 0 or depth_input.value <= 0:
        args.areInputsValid = False
        return

    args.areInputsValid = True

# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Destroy Event')

    global local_handlers
    local_handlers = []
