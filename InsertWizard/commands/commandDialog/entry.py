import adsk.core
import adsk.fusion
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

    # Diameter input in mm with a default of 10 mm.
    default_diameter = adsk.core.ValueInput.createByString('10 mm')
    inputs.addValueInput('diameter', 'Durchmesser 1', 'mm', default_diameter)

    # Depth input in mm.
    default_depth = adsk.core.ValueInput.createByString('5 mm')
    inputs.addValueInput('depth', 'Tiefe', 'mm', default_depth)

    # Connect to the events that are needed by this command.
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
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

    if points_input.selectionCount < 1:
        ui.messageBox('Bitte mindestens einen Skizzenpunkt auswählen.')
        return

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        ui.messageBox('Kein aktives Design gefunden.')
        return

    radius = diameter_input.value / 2.0
    depth_value = abs(depth_input.value)

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
        center = entity.geometry
        centers.append((sketch, adsk.core.Point3D.create(center.x, center.y, center.z)))
        futil.log(
            f'Punkt {i + 1}: X={center.x:.3f} Y={center.y:.3f} Z={center.z:.3f}',
            force_console=True
        )

    if mismatched_sketch:
        ui.messageBox('Bitte nur Punkte aus derselben Skizze auswählen.')
        return

    if not centers:
        return

    base_sketch = centers[0][0]
    plane_entity = None
    if hasattr(base_sketch, 'referencePlane') and base_sketch.referencePlane:
        plane_entity = base_sketch.referencePlane
    elif hasattr(base_sketch, 'planarEntity') and base_sketch.planarEntity:
        plane_entity = base_sketch.planarEntity

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

    for _, center in centers:
        circle = target_sketch.sketchCurves.sketchCircles.addByCenterRadius(center, radius)

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
                extrudes.add(ext_input)
                success = True
                break
            except:
                continue

        if not success:
            futil.log('Kein Zielkörper zum Schneiden gefunden.', force_console=True)


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
