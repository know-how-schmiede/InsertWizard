"""Regression checks for cut creation without a running Fusion UI."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


def load_functions(path, names, namespace):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    nodes = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    module = ast.Module(body=[ast.ImportFrom(
        module='__future__', names=[ast.alias(name='annotations')], level=0
    )] + nodes, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), namespace)
    return namespace


class CutTests(unittest.TestCase):
    def setUp(self):
        self.api = NS(
            core=NS(ValueInput=NS(createByReal=lambda value: value)),
            fusion=NS(
                ExtentDirections=NS(PositiveExtentDirection=1, NegativeExtentDirection=-1),
                FeatureOperations=NS(CutFeatureOperation='cut'),
                FeatureHealthStates=NS(ErrorFeatureHealthState='error'),
                DistanceExtentDefinition=NS(create=lambda value: value)
            )
        )
        self.ns = load_functions(
            'fusion_addin/InsertWizard/commands/commandDialog/entry.py',
            {'_create_cut', 'command_execute', '_get_reference_plane'},
            {'adsk': self.api, 'CMD_NAME': 'InsertWizard', 'futil': Mock()}
        )
        self.inputs = []
        def create_input(*args):
            cut = Mock()
            cut.setOneSideExtent.return_value = True
            self.inputs.append(cut)
            return cut
        self.extrudes = Mock()
        self.extrudes.createInput.side_effect = create_input
        self.bodies = [NS(volume=10.0)]
        def add(cut):
            self.bodies[0].volume = 9.0
            return self.extrudes.add.return_value
        self.extrudes.add.side_effect = add

    def cut(self):
        return self.ns['_create_cut'](self.extrudes, 'profile', 0.5, self.bodies)

    def test_positive_cut_stops_after_success_and_sets_bodies(self):
        self.assertIs(self.cut(), self.extrudes.add.return_value)
        self.assertEqual(len(self.inputs), 1)
        self.inputs[0].setOneSideExtent.assert_called_once_with(0.5, 1)
        self.assertEqual(self.inputs[0].participantBodies, self.bodies)
        self.assertIsInstance(self.inputs[0].participantBodies, list)

    def test_opposite_side_is_tried_after_no_intersection(self):
        feature = Mock()
        def add(cut):
            if len(self.inputs) == 1:
                raise RuntimeError('no intersection')
            self.bodies[0].volume = 9.0
            return feature
        self.extrudes.add.side_effect = add
        self.assertIs(self.cut(), feature)
        self.inputs[1].setOneSideExtent.assert_called_once_with(0.5, -1)

    def test_both_failures_are_reported(self):
        self.extrudes.add.side_effect = [RuntimeError('positive failure'), RuntimeError('negative failure')]
        with self.assertRaisesRegex(RuntimeError, 'positive failure.*negative failure'):
            self.cut()

    def test_returned_feature_without_material_removal_retries(self):
        empty = Mock(healthState='healthy')
        good = Mock(healthState='healthy')
        def add(cut):
            if len(self.inputs) == 1:
                return empty
            empty.deleteMe.assert_called_once()
            self.bodies[0].volume = 9.0
            return good
        self.extrudes.add.side_effect = add
        self.assertIs(self.cut(), good)
        self.inputs[1].setOneSideExtent.assert_called_once_with(0.5, -1)

    def test_error_feature_is_removed_before_retry(self):
        broken = Mock(healthState='error', errorOrWarningMessage='No target body')
        good = Mock(healthState='healthy')
        def add(cut):
            if len(self.inputs) == 1:
                return broken
            broken.deleteMe.assert_called_once()
            self.bodies[0].volume = 9.0
            return good
        self.extrudes.add.side_effect = add
        self.assertIs(self.cut(), good)

    def test_failed_cleanup_aborts_without_opposite_cut(self):
        empty = Mock(healthState='healthy')
        empty.deleteMe.return_value = False
        self.extrudes.add.side_effect = None
        self.extrudes.add.return_value = empty
        with self.assertRaisesRegex(RuntimeError, 'Could not remove'):
            self.cut()
        self.assertEqual(self.extrudes.add.call_count, 1)

    def test_setup_failure_also_tries_opposite_direction(self):
        self.extrudes.createInput.side_effect = [RuntimeError('setup failure'), Mock()]
        self.assertIs(self.cut(), self.extrudes.add.return_value)
        self.assertEqual(self.extrudes.createInput.call_count, 2)

    def test_command_failure_is_marked_and_logged(self):
        self.ns.update(_execute_holes=Mock(side_effect=RuntimeError('API failure')),
                       tr=lambda key: key, futil=Mock())
        args = NS()
        self.ns['command_execute'](args)
        self.assertTrue(args.executeFailed)
        self.assertEqual(args.executeFailedMessage, 'msg_creation_failed')
        self.ns['futil'].handle_error.assert_called_once()

    def test_error_traceback_reaches_console_with_debug_disabled(self):
        logger = Mock()
        ns = load_functions(
            'fusion_addin/InsertWizard/lib/fusionAddInUtils/general_utils.py', {'handle_error'},
            {'log': logger, 'adsk': NS(core=NS(LogLevels=NS(ErrorLogLevel=2))),
             'traceback': NS(format_exc=lambda: 'API traceback')}
        )
        ns['handle_error']('InsertWizard')
        self.assertEqual(logger.call_count, 2)
        for call in logger.call_args_list:
            self.assertTrue(call.kwargs['force_console'])
        self.assertIn('API traceback', logger.call_args.args[0])

    def test_face_reference_is_read_before_sketch_and_resolved_after_restore(self):
        timeline = NS(markerPosition=12)
        historical = NS(entityToken='face-token')
        current = object()
        def roll(before):
            self.assertTrue(before)
            timeline.markerPosition = 3
            return True
        class Sketch:
            isParametric = True
            timelineObject = NS(rollTo=roll)
            @property
            def referencePlane(self):
                if timeline.markerPosition != 3:
                    raise RuntimeError('referencePlane is a BRefFace - need to roll timeline back before sketch')
                return historical
        def resolve(token):
            self.assertEqual(timeline.markerPosition, 12)
            self.assertEqual(token, 'face-token')
            return [current]
        design = NS(timeline=timeline, findEntityByToken=resolve)
        self.assertIs(self.ns['_get_reference_plane'](Sketch(), design), current)
        self.assertEqual(timeline.markerPosition, 12)

    def test_timeline_restored_when_reference_read_fails(self):
        timeline = NS(markerPosition=12)
        def roll(before):
            timeline.markerPosition = 3
            return True
        class Sketch:
            isParametric = True
            timelineObject = NS(rollTo=roll)
            @property
            def referencePlane(self):
                raise RuntimeError('unavailable reference')
        with self.assertRaisesRegex(RuntimeError, 'unavailable reference'):
            self.ns['_get_reference_plane'](Sketch(), NS(timeline=timeline))
        self.assertEqual(timeline.markerPosition, 12)

    def test_construction_plane_does_not_move_timeline(self):
        plane = object()
        self.assertIs(self.ns['_get_reference_plane'](NS(referencePlane=plane), None), plane)


class HoleSketchTests(unittest.TestCase):
    def test_four_positions_have_independent_profiles_without_projected_edges(self):
        create = load_functions(
            'fusion_addin/InsertWizard/commands/commandDialog/entry.py',
            {'_create_hole_sketch'}, {}
        )['_create_hole_sketch']
        sketches = []
        def add(plane):
            sketch = Mock()
            sketches.append(sketch)
            return sketch
        component = Mock()
        component.sketches.addWithoutEdges.side_effect = add
        plane = object()
        for index, position in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)], 1):
            for kind, radius in [('insert', 0.2), ('screw', 0.16)]:
                name = f'ruthex_M3-{index}-{kind}-sketch'
                sketch, circle = create(component, plane, position, radius, name)
                self.assertEqual(sketch.name, name)
                self.assertFalse(sketch.isVisible)
                sketch.modelToSketchSpace.assert_called_once_with(position)
                sketch.sketchCurves.sketchCircles.addByCenterRadius.assert_called_once_with(
                    sketch.modelToSketchSpace.return_value, radius)
        self.assertEqual(len(sketches), 8)
        self.assertEqual(len({sketch.name for sketch in sketches}), 8)
        component.sketches.add.assert_not_called()


class ChamferEdgeTests(unittest.TestCase):
    def setUp(self):
        import math
        class Point:
            def __init__(self, x, y, z):
                self.xyz = (x, y, z)
            def distanceTo(self, other):
                return math.dist(self.xyz, other.xyz)
        self.point = Point
        self.api = NS(core=NS(
            Circle3D=NS(cast=lambda g: g if g.kind == 'circle' else None),
            Arc3D=NS(cast=lambda g: g if g.kind == 'arc' else None)
        ))
        self.find = load_functions(
            'fusion_addin/InsertWizard/commands/commandDialog/entry.py',
            {'_find_circle_edge'}, {'adsk': self.api}
        )['_find_circle_edge']
        self.circle = NS(nativeObject=None, worldGeometry=NS(
            radius=0.2, center=Point(1, 2, 3)))

    def edge(self, center=(1, 2, 3), radius=0.2, kind='circle'):
        return NS(geometry=NS(center=self.point(*center), radius=radius, kind=kind))

    def test_entrance_selected_instead_of_bottom_or_screw_edge(self):
        entrance = self.edge()
        body = NS(nativeObject=None, edges=[
            self.edge(center=(1, 2, 2)), self.edge(radius=0.16), entrance])
        self.assertIs(self.find(self.circle, [body]), entrance)

    def test_assembly_translation_does_not_change_match(self):
        entrance = self.edge()
        circle_proxy = NS(nativeObject=self.circle, worldGeometry=NS(
            radius=0.2, center=self.point(101, 202, 303)))
        body_proxy = NS(nativeObject=NS(edges=[entrance]))
        self.assertIs(self.find(circle_proxy, [body_proxy]), entrance)

    def test_split_circular_edge_is_recognized(self):
        entrance = self.edge(kind='arc')
        self.assertIs(self.find(self.circle, [NS(nativeObject=None, edges=[entrance])]), entrance)

    def test_no_match_does_not_pick_nearby_hole(self):
        body = NS(nativeObject=None, edges=[self.edge(center=(1.01, 2, 3))])
        self.assertIsNone(self.find(self.circle, [body]))


if __name__ == '__main__':
    unittest.main()
