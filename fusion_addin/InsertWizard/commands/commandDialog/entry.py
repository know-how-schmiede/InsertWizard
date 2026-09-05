import adsk.core
import adsk.fusion
import json
import os
import re
from lib import fusionAddInUtils as futil
import config
import version
app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = f'InsertWizard v{version.__version__}'

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
LOGO_FILE_LIGHT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'images', 'Logo_InsertWizard_200.png')
)
LOGO_FILE_DARK = LOGO_FILE_LIGHT

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

PRESETS = []
PRESET_BY_NAME = {}
KEEP_POINT_SKETCH_VISIBLE = False

PRESET_FILE = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'presets.json')
)

THREAD_CLEARANCE_MM = {
    1.6: 1.8,
    2.0: 2.2,
    2.5: 2.7,
    3.0: 3.2,
    4.0: 4.3,
    5.0: 5.3,
    6.0: 6.4,
    8.0: 8.4,
    10.0: 10.5
}


def _parse_thread_size(thread: str):
    if not thread:
        return None
    match = re.search(r'[mM]\s*([0-9]+(?:[\\.,][0-9]+)?)', thread)
    if not match:
        return None
    value = match.group(1).replace(',', '.')
    try:
        return float(value)
    except:
        return None


def _thread_clearance_diameter(thread: str):
    size = _parse_thread_size(thread)
    if size is None:
        return None
    size_key = round(size, 2)
    if size_key in THREAD_CLEARANCE_MM:
        return THREAD_CLEARANCE_MM[size_key]
    return round(size_key + 0.2, 2)


def _auto_screw_depth_mm(
    depth_input: adsk.core.ValueCommandInput,
    thread_diameter_input: adsk.core.ValueCommandInput
):
    if not depth_input or not thread_diameter_input:
        return None
    try:
        depth_mm = depth_input.value * 10.0
        thread_mm = thread_diameter_input.value * 10.0
    except:
        return None
    return round(depth_mm + int(thread_mm), 3)


def _is_dark_theme() -> bool:
    try:
        return bool(ui.isDarkTheme)
    except:
        pass
    try:
        prefs = app.preferences
    except:
        prefs = None
    if prefs:
        try:
            general = prefs.generalPreferences
        except:
            general = None
        if general:
            for attr in ('isDarkTheme', 'useDarkTheme'):
                try:
                    if hasattr(general, attr):
                        return bool(getattr(general, attr))
                except:
                    continue
    return False

SUPPORTED_LANGS = ('en', 'de', 'fr', 'es', 'it', 'pl')
I18N_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'i18n')
)
I18N_CACHE = {}
ENUM_LANG_CACHE = None
LCID_LANG_MAP = {
    1031: 'de',
    1033: 'en',
    1036: 'fr',
    3082: 'es',
    1040: 'it',
    1045: 'pl'
}


def _load_translation_file(lang: str) -> dict:
    if not lang:
        return {}
    path = os.path.join(I18N_DIR, f'{lang}.json')
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except:
        pass
    return {}


def _get_translations(lang: str) -> dict:
    if lang not in I18N_CACHE:
        I18N_CACHE[lang] = _load_translation_file(lang)
    return I18N_CACHE[lang]


def _language_supported(lang: str) -> bool:
    if not lang:
        return False
    path = os.path.join(I18N_DIR, f'{lang}.json')
    return os.path.isfile(path)

def _lang_from_text(text: str):
    if not text:
        return None
    cleaned = str(text).strip().lower()
    if not cleaned:
        return None
    if '(' in cleaned:
        cleaned = cleaned.split('(')[0].strip()
    for sep in ('.', '/', '\\'):
        if sep in cleaned:
            cleaned = cleaned.split(sep)[-1]
    if ' ' in cleaned:
        cleaned = cleaned.split()[-1]
    for sep in ('-', '_'):
        if sep in cleaned:
            cleaned = cleaned.split(sep)[0]
    if cleaned in SUPPORTED_LANGS:
        return cleaned
    if cleaned in ('german', 'deutsch', 'deu') or 'german' in cleaned or 'deutsch' in cleaned:
        return 'de'
    if cleaned in ('english', 'eng') or 'english' in cleaned:
        return 'en'
    if cleaned in ('french', 'francais', 'franc') or 'french' in cleaned or 'francais' in cleaned or 'franc' in cleaned:
        return 'fr'
    if cleaned in ('spanish', 'espanol', 'esp') or 'spanish' in cleaned or 'espanol' in cleaned:
        return 'es'
    if cleaned in ('italian', 'italiano', 'ita') or 'italian' in cleaned or 'italiano' in cleaned:
        return 'it'
    if cleaned in ('polish', 'polski', 'pol') or 'polish' in cleaned or 'polski' in cleaned:
        return 'pl'
    return None


def _lang_from_enum(value):
    global ENUM_LANG_CACHE
    if ENUM_LANG_CACHE is None:
        ENUM_LANG_CACHE = {}
        try:
            enum_cls = adsk.core.UserLanguages
            for name in dir(enum_cls):
                if name.startswith('_'):
                    continue
                try:
                    enum_val = getattr(enum_cls, name)
                except:
                    continue
                if isinstance(enum_val, (int, float)):
                    code = _lang_from_text(name)
                    if code:
                        ENUM_LANG_CACHE[int(enum_val)] = code
        except:
            pass
    try:
        value_int = int(value)
        if value_int in ENUM_LANG_CACHE:
            return ENUM_LANG_CACHE[value_int]
        if value_int in LCID_LANG_MAP:
            return LCID_LANG_MAP[value_int]
        return None
    except:
        return None


def _extract_lang(value):
    if value is None:
        return None
    try:
        if hasattr(value, 'name'):
            value = value.name
    except:
        pass
    if isinstance(value, (int, float)):
        return _lang_from_enum(value)
    try:
        if hasattr(value, 'value'):
            enum_lang = _lang_from_enum(getattr(value, 'value'))
            if enum_lang:
                return enum_lang
    except:
        pass
    try:
        num_value = int(value)
        enum_lang = _lang_from_enum(num_value)
        if enum_lang:
            return enum_lang
    except:
        pass
    return _lang_from_text(value)


def _detect_language():
    candidates = [ui, app]
    try:
        candidates.append(app.preferences)
    except:
        pass
    try:
        candidates.append(app.preferences.generalPreferences)
    except:
        pass

    for obj in candidates:
        if not obj:
            continue
        for attr in (
            'language',
            'locale',
            'userLanguage',
            'userLocale',
            'uiLanguage',
            'languagePreference',
            'userLanguagePreference',
            'languageCode',
            'languageId',
            'languageID',
            'userLanguageId',
            'userLanguageID',
            'userInterfaceLanguage',
            'interfaceLanguage',
            'uiLocale',
            'activeLanguage'
        ):
            try:
                if not hasattr(obj, attr):
                    continue
                lang = _extract_lang(getattr(obj, attr))
                if lang and _language_supported(lang):
                    return lang
            except:
                continue
    return None


def _resolve_language():
    override = None
    try:
        override = getattr(config, 'LANGUAGE', None)
    except:
        override = None
    if not override:
        override = os.environ.get('INSERTWIZARD_LANG', '')
    if override:
        override_text = str(override).strip().lower()
        if override_text == 'auto':
            detected = _detect_language()
            return detected or 'en'
        lang = _extract_lang(override)
        if lang and _language_supported(lang):
            return lang
    detected = _detect_language()
    if detected:
        return detected
    try:
        import locale
        loc = locale.getdefaultlocale()[0]
        lang = _extract_lang(loc)
        if lang and _language_supported(lang):
            return lang
    except:
        pass
    return 'en'


LANGUAGE = None
EN_TRANSLATIONS = _get_translations('en')
ACTIVE_TRANSLATIONS = {}


def _log_language_debug():
    try:
        if not getattr(config, 'LANGUAGE_DEBUG', False):
            return
    except:
        return
    entries = []
    candidates = []
    candidates.append(('ui', ui))
    candidates.append(('app', app))
    try:
        candidates.append(('preferences', app.preferences))
    except:
        pass
    try:
        candidates.append(('generalPreferences', app.preferences.generalPreferences))
    except:
        pass
    for name, obj in candidates:
        if not obj:
            continue
        for attr in dir(obj):
            attr_lower = attr.lower()
            if 'lang' not in attr_lower and 'locale' not in attr_lower:
                continue
            try:
                val = getattr(obj, attr)
            except:
                continue
            val_text = str(val)
            if len(val_text) > 80:
                val_text = val_text[:77] + '...'
            entries.append(f'{name}.{attr}={val_text}')
    futil.log(f"Language debug: override={getattr(config, 'LANGUAGE', None)}", force_console=True)
    futil.log(f'Language debug: detected={_detect_language()} resolved={_resolve_language()}', force_console=True)
    for item in entries:
        futil.log(f'Language debug: {item}', force_console=True)


def _set_language(lang: str):
    global LANGUAGE, ACTIVE_TRANSLATIONS
    if not lang:
        lang = 'en'
    if lang == LANGUAGE:
        return
    LANGUAGE = lang
    ACTIVE_TRANSLATIONS = _get_translations(lang)


def _ensure_language():
    if not LANGUAGE:
        _set_language(_resolve_language())


def tr(key: str, **kwargs) -> str:
    _ensure_language()
    text = ACTIVE_TRANSLATIONS.get(key) or EN_TRANSLATIONS.get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except:
            return text
    return text

def _preset_display_name(preset: dict) -> str:
    manufacturer = str(preset.get('Manufacturer', preset.get('Hersteller', 'Preset'))).strip()
    thread = str(preset.get('Thread', preset.get('Gewinde', ''))).strip()
    if thread:
        return f'{manufacturer} {thread}'
    return manufacturer


def _preset_manufacturer(preset: dict) -> str:
    manufacturer = str(preset.get('Manufacturer', preset.get('Hersteller', ''))).strip()
    return manufacturer or 'Preset'


def _unique_manufacturers(presets: list) -> list:
    manufacturers = []
    seen = set()
    for preset in presets:
        name = _preset_manufacturer(preset)
        if name not in seen:
            manufacturers.append(name)
            seen.add(name)
    return manufacturers


def _find_default_preset(presets: list):
    fallback = None
    for preset in presets:
        if _preset_manufacturer(preset).lower() != 'default':
            continue
        if fallback is None:
            fallback = preset
        thread = str(preset.get('Thread', preset.get('Gewinde', ''))).strip()
        if ''.join(thread.split()).lower().startswith('m3'):
            return preset
    return fallback


def _clear_dropdown_items(dropdown: adsk.core.DropDownCommandInput):
    items = dropdown.listItems
    try:
        items.clear()
        return
    except:
        pass
    try:
        for idx in range(items.count - 1, -1, -1):
            try:
                items.item(idx).deleteMe()
            except:
                pass
    except:
        pass


def _populate_preset_list(presets: list, preset_input: adsk.core.DropDownCommandInput, manufacturer: str):
    global PRESET_BY_NAME
    PRESET_BY_NAME = {}
    _clear_dropdown_items(preset_input)
    items = preset_input.listItems

    def add_preset_item(preset, is_selected):
        name = _preset_display_name(preset)
        if name in PRESET_BY_NAME:
            suffix = 2
            candidate = f'{name} ({suffix})'
            while candidate in PRESET_BY_NAME:
                suffix += 1
                candidate = f'{name} ({suffix})'
            name = candidate
        PRESET_BY_NAME[name] = preset
        items.add(name, is_selected, '')

    default_preset = _find_default_preset(presets)
    filtered = []
    for preset in presets:
        if preset is default_preset:
            continue
        if manufacturer and _preset_manufacturer(preset).lower() != manufacturer.lower():
            continue
        filtered.append(preset)

    if filtered:
        if default_preset:
            add_preset_item(default_preset, False)
        for idx, preset in enumerate(filtered):
            add_preset_item(preset, idx == 0)
    else:
        if default_preset:
            add_preset_item(default_preset, True)


def _load_presets() -> list:
    try:
        with open(PRESET_FILE, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
        presets = data.get('presets', data) if isinstance(data, dict) else data
        if not isinstance(presets, list):
            raise ValueError(tr('log_invalid_preset_format'))
    except Exception as exc:
        futil.log(tr('log_preset_load_failed', error=exc), force_console=True)
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


def _apply_preset(
    preset: dict,
    diameter_input: adsk.core.ValueCommandInput,
    depth_input: adsk.core.ValueCommandInput,
    thread_diameter_input: adsk.core.ValueCommandInput = None,
    screw_depth_input: adsk.core.ValueCommandInput = None
):
    if not preset:
        return
    diameter = preset.get('Diameter_d3', preset.get('Diameter', preset.get('durchmesser', None)))
    depth = preset.get('Length', preset.get('Länge', None))
    length_plus = preset.get('Length_plus', preset.get('LengthPlus', None))
    if depth is not None and length_plus is not None:
        try:
            depth = float(depth) + float(length_plus)
        except:
            pass
    thread = str(preset.get('Thread', preset.get('Gewinde', ''))).strip()

    old_depth_value = None
    old_thread_value = None
    old_screw_depth_value = None
    if screw_depth_input:
        try:
            old_depth_value = depth_input.value
            if thread_diameter_input:
                old_thread_value = thread_diameter_input.value
            old_screw_depth_value = screw_depth_input.value
        except:
            pass

    if diameter is not None:
        diameter_input.expression = f'{diameter} mm'
    if depth is not None:
        depth_input.expression = f'{depth} mm'

    if thread_diameter_input:
        thread_diameter = preset.get('ThreadDiameter', preset.get('GewindeDurchmesser', preset.get('Gewindedurchmesser', None)))
        if thread_diameter is None:
            thread_diameter = _thread_clearance_diameter(thread)
        if thread_diameter is not None:
            thread_diameter_input.expression = f'{thread_diameter} mm'

    if screw_depth_input:
        screw_depth = preset.get(
            'ScrewDepth',
            preset.get('SchraubenTiefe', preset.get('Schrauben-Tiefe', preset.get('Schraubentiefe', None)))
        )
        if screw_depth is not None:
            screw_depth_input.expression = f'{screw_depth} mm'
        else:
            auto_mm = _auto_screw_depth_mm(depth_input, thread_diameter_input)
            if auto_mm is not None:
                old_auto_cm = None
                if old_depth_value is not None and old_thread_value is not None:
                    old_auto_cm = (old_depth_value * 10.0 + int(old_thread_value * 10.0)) / 10.0
                if old_screw_depth_value is None or old_auto_cm is None:
                    screw_depth_input.expression = f'{auto_mm} mm'
                elif abs(old_screw_depth_value - old_auto_cm) < 1e-6:
                    screw_depth_input.expression = f'{auto_mm} mm'


def _preset_base_name(preset: dict) -> str:
    manufacturer = str(preset.get('Manufacturer', preset.get('Hersteller', 'Preset'))).strip()
    thread = str(preset.get('Thread', preset.get('Gewinde', ''))).strip()
    thread = ''.join(thread.split())
    if thread:
        return f'{manufacturer}_{thread}'
    return manufacturer


def _next_extrude_index(component: adsk.fusion.Component, base_name: str) -> int:
    prefix = f'{base_name}-'
    max_index = 0
    for feat in component.features.extrudeFeatures:
        try:
            name = feat.name
        except:
            continue
        if not name.startswith(prefix):
            continue
        suffix = name[len(prefix):]
        try:
            idx = int(suffix)
        except:
            continue
        if idx > max_index:
            max_index = idx
    return max_index + 1



# Executed when add-in is run.
def start():
    # Create a command Definition.
    futil.log(f'{CMD_NAME}: loaded from {__file__}', force_console=True)
    _set_language(_resolve_language())
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, tr('cmd_description'), ICON_FOLDER)

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
    _set_language(_resolve_language())
    _log_language_debug()

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    # Show a simple dialog that displays the add-in name.
    inputs.addTextBoxCommandInput('title', '', CMD_NAME, 1, True)
    try:
        logo_path = LOGO_FILE_LIGHT
        if _is_dark_theme() and os.path.exists(LOGO_FILE_DARK):
            logo_path = LOGO_FILE_DARK
        logo_input = inputs.addImageCommandInput('logo', '', logo_path)
        logo_input.isFullWidth = True
    except:
        pass

    # Selection input for one or more sketch points.
    points_input = inputs.addSelectionInput('points', tr('points_label'), tr('points_prompt'))
    points_input.addSelectionFilter('SketchPoints')
    points_input.setSelectionLimits(1, 0)
    try:
        points_input.isMultiSelectEnabled = True
    except:
        # Older API versions may not expose this property.
        pass

    # Manufacturer + preset selection.
    global PRESETS, PRESET_BY_NAME
    PRESETS = _load_presets()
    PRESET_BY_NAME = {}

    manufacturers = _unique_manufacturers(PRESETS)
    default_manufacturer = manufacturers[0] if manufacturers else ''
    for name in manufacturers:
        if name.lower() != 'default':
            default_manufacturer = name
            break

    manufacturer_input = inputs.addDropDownCommandInput(
        'manufacturer',
        tr('manufacturer_label'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    for name in manufacturers:
        manufacturer_input.listItems.add(name, name == default_manufacturer, '')

    preset_input = inputs.addDropDownCommandInput(
        'preset',
        tr('preset_label'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    selected_manufacturer = manufacturer_input.selectedItem.name if manufacturer_input.selectedItem else ''
    _populate_preset_list(PRESETS, preset_input, selected_manufacturer)

    # Diameter input in mm with a default of 10 mm.
    default_diameter = adsk.core.ValueInput.createByString('10 mm')
    inputs.addValueInput('diameter', tr('diameter_label'), 'mm', default_diameter)

    # Depth input in mm.
    default_depth = adsk.core.ValueInput.createByString('5 mm')
    inputs.addValueInput('depth', tr('depth_label'), 'mm', default_depth)

    # Thread diameter and screw depth inputs in mm.
    default_thread_diameter = adsk.core.ValueInput.createByString('3.2 mm')
    inputs.addValueInput('thread_diameter', tr('thread_diameter_label'), 'mm', default_thread_diameter)

    default_screw_depth = adsk.core.ValueInput.createByString('5 mm')
    inputs.addValueInput('screw_depth', tr('screw_depth_label'), 'mm', default_screw_depth)

    diameter_input: adsk.core.ValueCommandInput = inputs.itemById('diameter')
    depth_input: adsk.core.ValueCommandInput = inputs.itemById('depth')
    thread_diameter_input: adsk.core.ValueCommandInput = inputs.itemById('thread_diameter')
    screw_depth_input: adsk.core.ValueCommandInput = inputs.itemById('screw_depth')
    auto_screw_depth = _auto_screw_depth_mm(depth_input, thread_diameter_input)
    if auto_screw_depth is not None:
        screw_depth_input.expression = f'{auto_screw_depth} mm'
    if preset_input.selectedItem:
        _apply_preset(
            PRESET_BY_NAME[preset_input.selectedItem.name],
            diameter_input,
            depth_input,
            thread_diameter_input,
            screw_depth_input
        )

    # Chamfer on/off toggle.
    inputs.addBoolValueInput('chamfer_enabled', tr('chamfer_enabled_label'), True, '', True)

    # Chamfer size selection.
    chamfer_input = inputs.addDropDownCommandInput(
        'chamfer',
        tr('chamfer_label'),
        adsk.core.DropDownStyles.TextListDropDownStyle
    )
    chamfer_items = chamfer_input.listItems
    chamfer_items.add('0.2 mm', True, '')
    chamfer_items.add('0.4 mm', False, '')
    chamfer_items.add('0.6 mm', False, '')

    # Keep the placement sketch visible after creating features.
    inputs.addBoolValueInput(
        'keep_point_sketch_visible',
        tr('keep_point_sketch_visible_label'),
        True,
        '',
        KEEP_POINT_SKETCH_VISIBLE
    )

    # Connect to the events that are needed by this command.
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    futil.log(f'{CMD_NAME}: starting hole creation (timeline fix)', force_console=True)
    try:
        _execute_holes(args)
    except Exception:
        # Let Fusion roll back the command and show the actual API failure.
        args.executeFailed = True
        args.executeFailedMessage = tr('msg_creation_failed')
        futil.handle_error('InsertWizard: command_execute')


def _get_reference_plane(sketch, design):
    """Read face-backed references at their original timeline position."""
    try:
        return sketch.referencePlane
    except RuntimeError:
        if not sketch.isParametric:
            raise

    timeline = design.timeline
    marker = timeline.markerPosition
    try:
        if not sketch.timelineObject.rollTo(True):
            raise RuntimeError('Could not roll timeline before placement sketch')
        reference = sketch.referencePlane
        token = reference.entityToken if reference else None
    finally:
        timeline.markerPosition = marker

    if token is None:
        return None
    # Do not reuse a BRepFace obtained in an earlier state of the model.
    references = design.findEntityByToken(token)
    if not references:
        raise RuntimeError('Sketch reference plane no longer exists at the current timeline position')
    return references[0]


def _find_circle_edge(sketch_circle, bodies):
    """Match the actual opening in component space, including assembly proxies."""
    native_circle = sketch_circle.nativeObject or sketch_circle
    opening = native_circle.worldGeometry
    tolerance = 1e-5  # cm; geometric matching, not a manufacturing clearance.
    for body in bodies:
        native_body = body.nativeObject or body
        for edge in native_body.edges:
            geometry = edge.geometry
            circular = adsk.core.Circle3D.cast(geometry) or adsk.core.Arc3D.cast(geometry)
            if not circular:
                continue
            if abs(circular.radius - opening.radius) > tolerance:
                continue
            # The entrance center excludes the concentric edge at the hole bottom.
            if circular.center.distanceTo(opening.center) <= tolerance:
                return edge
    return None


def _create_cut(extrudes, profile, depth, bodies):
    """Accept a direction only when its feature actually removes material."""
    errors = []
    volume_before = sum(body.volume for body in bodies)
    for direction in (
        adsk.fusion.ExtentDirections.PositiveExtentDirection,
        adsk.fusion.ExtentDirections.NegativeExtentDirection
    ):
        feature = None
        try:
            cut_input = extrudes.createInput(
                profile, adsk.fusion.FeatureOperations.CutFeatureOperation
            )
            extent = adsk.fusion.DistanceExtentDefinition.create(
                adsk.core.ValueInput.createByReal(abs(depth))
            )
            if not cut_input.setOneSideExtent(extent, direction):
                raise RuntimeError('setOneSideExtent returned False')
            # Fusion expects a Python list, not an ObjectCollection.
            cut_input.participantBodies = list(bodies)
            feature = extrudes.add(cut_input)
            if not feature:
                raise RuntimeError('extrudeFeatures.add returned no feature')
            if feature.healthState == adsk.fusion.FeatureHealthStates.ErrorFeatureHealthState:
                raise RuntimeError(feature.errorOrWarningMessage or 'Extrusion has an error')
            volume_after = sum(body.volume for body in bodies)
            if volume_before - volume_after <= max(1e-9, abs(volume_before) * 1e-12):
                raise RuntimeError('Extrusion did not remove material')
            return feature
        except Exception as exc:
            # Remove an unsuccessful feature before trying the opposite direction.
            # If cleanup fails, abort instead of stacking features on a bad result.
            if feature and not feature.deleteMe():
                raise RuntimeError('Could not remove unsuccessful extrusion') from exc
            errors.append(f'{direction}: {exc}')
    raise RuntimeError('Cut failed in both directions: ' + ' | '.join(errors))


def _execute_holes(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Execute Event')

    inputs = args.command.commandInputs
    points_input: adsk.core.SelectionCommandInput = inputs.itemById('points')
    diameter_input: adsk.core.ValueCommandInput = inputs.itemById('diameter')
    depth_input: adsk.core.ValueCommandInput = inputs.itemById('depth')
    thread_diameter_input: adsk.core.ValueCommandInput = inputs.itemById('thread_diameter')
    screw_depth_input: adsk.core.ValueCommandInput = inputs.itemById('screw_depth')
    preset_input: adsk.core.DropDownCommandInput = inputs.itemById('preset')
    chamfer_enabled: adsk.core.BoolValueCommandInput = inputs.itemById('chamfer_enabled')
    chamfer_input: adsk.core.DropDownCommandInput = inputs.itemById('chamfer')
    keep_point_sketch_visible: adsk.core.BoolValueCommandInput = inputs.itemById('keep_point_sketch_visible')

    if points_input.selectionCount < 1:
        ui.messageBox(tr('msg_select_point'))
        return

    global KEEP_POINT_SKETCH_VISIBLE
    if keep_point_sketch_visible:
        KEEP_POINT_SKETCH_VISIBLE = bool(keep_point_sketch_visible.value)

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        ui.messageBox(tr('msg_no_design'))
        return

    radius = diameter_input.value / 2.0
    depth_value = abs(depth_input.value)
    thread_radius = thread_diameter_input.value / 2.0 if thread_diameter_input else 0.0
    screw_depth_value = abs(screw_depth_input.value) if screw_depth_input else 0.0
    chamfer_value = None
    if chamfer_enabled.value:
        chamfer_value = adsk.core.ValueInput.createByString(chamfer_input.selectedItem.name)
        futil.log(tr('log_chamfer', value=chamfer_input.selectedItem.name), force_console=True)
    else:
        futil.log(tr('log_chamfer_disabled'), force_console=True)

    selection_count = points_input.selectionCount
    futil.log(tr('log_selected_points', count=selection_count), force_console=True)

    centers = []
    base_sketch = None
    mismatched_sketch = False
    for i in range(selection_count):
        try:
            selection = points_input.selection(i)
        except:
            futil.log(tr('log_invalid_selection_index', index=i), force_console=True)
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
            tr(
                'log_point_coords',
                index=i + 1,
                x=sketch_center.x,
                y=sketch_center.y,
                z=sketch_center.z
            ),
            force_console=True
        )

    if mismatched_sketch:
        ui.messageBox(tr('msg_same_sketch'))
        return

    if not centers:
        return

    base_sketch = centers[0][0]
    base_name = 'Insert'
    selected_preset = None
    if preset_input and preset_input.selectedItem:
        selected_preset = PRESET_BY_NAME.get(preset_input.selectedItem.name)
    if selected_preset:
        base_name = _preset_base_name(selected_preset)
    plane_entity = _get_reference_plane(base_sketch, design)

    target_sketch = base_sketch
    next_index = _next_extrude_index(target_sketch.parentComponent, base_name)
    created_timeline_indices = []
    group_index = None

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
        futil.log(tr('log_no_target_body'), force_console=True)
        return

    bodies = []
    for i in range(target_bodies.count):
        bodies.append(target_bodies.item(i))

    def find_profile_for_circle(sketch: adsk.fusion.Sketch, circle):
        fallback_profile = None
        for prof in sketch.profiles:
            for loop in prof.profileLoops:
                for curve in loop.profileCurves:
                    if curve.sketchEntity == circle:
                        if hasattr(loop, 'isOuter') and loop.isOuter:
                            return prof
                        fallback_profile = prof
        return fallback_profile

    screw_sketch = None
    if thread_radius > 0 and screw_depth_value > 0:
        try:
            sketch_plane = plane_entity if plane_entity else base_sketch
            screw_sketch = target_sketch.parentComponent.sketches.add(sketch_plane)
            try:
                screw_sketch.isVisible = False
            except:
                pass
            try:
                timeline_obj = screw_sketch.timelineObject
                if timeline_obj:
                    created_timeline_indices.append(timeline_obj.index)
            except:
                pass
        except:
            screw_sketch = None

    for _, sketch_center, model_center in centers:
        point_index = next_index
        circle = target_sketch.sketchCurves.sketchCircles.addByCenterRadius(sketch_center, radius)

        profile = find_profile_for_circle(target_sketch, circle)

        if not profile:
            futil.log(tr('log_no_profile_circle'), force_console=True)
            continue

        extrudes = target_sketch.parentComponent.features.extrudeFeatures
        ext_feature = _create_cut(extrudes, profile, depth_value, bodies)

        if ext_feature:
            try:
                ext_feature.name = f'{base_name}-{point_index}'
            except:
                pass
            if group_index is None:
                group_index = point_index
            try:
                timeline_obj = ext_feature.timelineObject
                if timeline_obj:
                    created_timeline_indices.append(timeline_obj.index)
            except:
                pass
            next_index += 1

        if screw_sketch and thread_radius > 0 and screw_depth_value > 0:
            screw_center = None
            if hasattr(screw_sketch, 'modelToSketchSpace'):
                try:
                    screw_center = screw_sketch.modelToSketchSpace(model_center)
                except:
                    screw_center = None
            if not screw_center:
                screw_center = adsk.core.Point3D.create(sketch_center.x, sketch_center.y, sketch_center.z)

            screw_circle = screw_sketch.sketchCurves.sketchCircles.addByCenterRadius(screw_center, thread_radius)
            screw_profile = find_profile_for_circle(screw_sketch, screw_circle)
            if not screw_profile:
                futil.log(tr('log_no_profile_screw'), force_console=True)
            else:
                screw_feature = _create_cut(extrudes, screw_profile, screw_depth_value, bodies)
                if screw_feature:
                    try:
                        screw_feature.name = f'{base_name}-{point_index}-screw'
                    except:
                        pass
                    try:
                        timeline_obj = screw_feature.timelineObject
                        if timeline_obj:
                            created_timeline_indices.append(timeline_obj.index)
                    except:
                        pass


        if chamfer_enabled.value:
            edge = _find_circle_edge(circle, bodies)
            if edge:
                try:
                    token = edge.entityToken
                except:
                    token = 'n/a'
                futil.log(tr('log_chamfer_edge', token=token), force_console=True)
                chamfer_feats = target_sketch.parentComponent.features.chamferFeatures
                single = adsk.core.ObjectCollection.create()
                single.add(edge)
                try:
                    chamfer_feat_input = chamfer_feats.createInput(single, False)
                    chamfer_feat_input.setToEqualDistance(chamfer_value)
                    chamfer_feature = chamfer_feats.add(chamfer_feat_input)
                    try:
                        timeline_obj = chamfer_feature.timelineObject
                        if timeline_obj:
                            created_timeline_indices.append(timeline_obj.index)
                    except:
                        pass
                except:
                    futil.log(tr('log_chamfer_failed'), force_console=True)
            else:
                futil.log(tr('log_chamfer_edge_missing'), force_console=True)

    if created_timeline_indices:
        try:
            min_index = min(created_timeline_indices)
            max_index = max(created_timeline_indices)
            timeline_groups = design.timeline.timelineGroups
            group = timeline_groups.add(min_index, max_index)
            group_name = f'group_{base_name}'
            if group_index is not None:
                group_name = f'group_{base_name}-{group_index}'
            try:
                group.name = group_name
            except:
                pass
        except:
            pass

    if keep_point_sketch_visible and keep_point_sketch_visible.value and base_sketch:
        try:
            base_sketch.isVisible = True
        except:
            pass


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    if not changed_input:
        return

    if changed_input.id == 'keep_point_sketch_visible':
        global KEEP_POINT_SKETCH_VISIBLE
        KEEP_POINT_SKETCH_VISIBLE = bool(changed_input.value)

    if changed_input.id == 'manufacturer':
        preset_input: adsk.core.DropDownCommandInput = args.inputs.itemById('preset')
        selected_manufacturer = changed_input.selectedItem.name if changed_input.selectedItem else ''
        _populate_preset_list(PRESETS, preset_input, selected_manufacturer)
        if preset_input.selectedItem:
            diameter_input: adsk.core.ValueCommandInput = args.inputs.itemById('diameter')
            depth_input: adsk.core.ValueCommandInput = args.inputs.itemById('depth')
            thread_diameter_input: adsk.core.ValueCommandInput = args.inputs.itemById('thread_diameter')
            screw_depth_input: adsk.core.ValueCommandInput = args.inputs.itemById('screw_depth')
            _apply_preset(
                PRESET_BY_NAME[preset_input.selectedItem.name],
                diameter_input,
                depth_input,
                thread_diameter_input,
                screw_depth_input
            )

    if changed_input.id == 'preset':
        preset = PRESET_BY_NAME.get(changed_input.selectedItem.name)
        if not preset:
            return
        diameter_input: adsk.core.ValueCommandInput = args.inputs.itemById('diameter')
        depth_input: adsk.core.ValueCommandInput = args.inputs.itemById('depth')
        thread_diameter_input: adsk.core.ValueCommandInput = args.inputs.itemById('thread_diameter')
        screw_depth_input: adsk.core.ValueCommandInput = args.inputs.itemById('screw_depth')
        _apply_preset(preset, diameter_input, depth_input, thread_diameter_input, screw_depth_input)


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Validate Input Event')

    inputs = args.inputs
    points_input: adsk.core.SelectionCommandInput = inputs.itemById('points')
    diameter_input: adsk.core.ValueCommandInput = inputs.itemById('diameter')
    depth_input: adsk.core.ValueCommandInput = inputs.itemById('depth')
    thread_diameter_input: adsk.core.ValueCommandInput = inputs.itemById('thread_diameter')
    screw_depth_input: adsk.core.ValueCommandInput = inputs.itemById('screw_depth')

    if (
        points_input.selectionCount < 1
        or diameter_input.value <= 0
        or depth_input.value <= 0
        or thread_diameter_input.value <= 0
        or screw_depth_input.value <= 0
    ):
        args.areInputsValid = False
        return

    args.areInputsValid = True

# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Destroy Event')

    global local_handlers
    local_handlers = []


