"""Offline regression checks. These do not replace the real Odoo lifecycle test.

Compares the split with the last reviewed connector commit so accidentally
omitted fields, changed business methods, and active code in retained storage
fail before a database is touched. Run from the repository root.
"""
import ast
import csv
import io
from pathlib import Path
import subprocess
import unittest

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '436c265e587c9980073daa659ea51b85e09a3256'
FILES = ('mobile.py', 'onboarding.py', 'engagement.py', 'gifts.py', 'birthday_management.py')


def classes(source):
    return [n for n in ast.parse(source).body if isinstance(n, ast.ClassDef)]


def assignments(cls):
    return {n.targets[0].id: n.value for n in cls.body
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}


def model_name(cls):
    values = assignments(cls)
    definition = values.get('_name', values.get('_inherit'))
    return ast.literal_eval(definition) if definition else cls.name


def declared_fields(source):
    result = {}
    for cls in classes(source):
        for name, value in assignments(cls).items():
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name) and value.func.value.id == 'fields':
                result[model_name(cls), name] = ast.dump(value)
    return result


class LifecycleStructure(unittest.TestCase):
    def test_every_original_field_is_preserved_exactly_once(self):
        before, after = {}, {}
        for name in FILES:
            original = subprocess.check_output(['git', 'show', f'{BASELINE}:spx_loyalty_mobile/models/{name}'], cwd=ROOT, text=True)
            before.update(declared_fields(original))
            for addon in ('spx_loyalty_mobile', 'spx_loyalty_mobile_data'):
                current = declared_fields((ROOT / addon / 'models' / name).read_text())
                self.assertFalse(after.keys() & current.keys(), 'Duplicate field ownership')
                after.update(current)
        self.assertEqual(before, after)

    def test_business_methods_are_unchanged_and_remain_in_connector(self):
        for name in FILES:
            before = subprocess.check_output(['git', 'show', f'{BASELINE}:spx_loyalty_mobile/models/{name}'], cwd=ROOT, text=True)
            after = (ROOT / 'spx_loyalty_mobile/models' / name).read_text()
            def methods(source):
                return {(model_name(c), n.name): ast.dump(n) for c in classes(source)
                        for n in c.body if isinstance(n, ast.FunctionDef)}
            self.assertEqual(methods(before), methods(after), name)

    def test_retained_schema_has_no_business_methods_or_native_field_overrides(self):
        for path in (ROOT / 'spx_loyalty_mobile_data/models').glob('*.py'):
            for cls in classes(path.read_text()):
                self.assertFalse(any(isinstance(n, ast.FunctionDef) for n in cls.body), path)
                if not model_name(cls).startswith('spx.mobile.'):
                    self.assertTrue(all(name.startswith('spx_') for model, name in declared_fields(ast.unparse(cls))))
        manifest = ast.literal_eval((ROOT / 'spx_loyalty_mobile_data/__manifest__.py').read_text())
        self.assertTrue(all(name.startswith('security/') for name in manifest['data']))
        self.assertFalse((ROOT / 'spx_loyalty_mobile_data/controllers').exists())

    def test_schema_manifest_matches_retained_fields(self):
        namespace = {}
        exec((ROOT / 'spx_loyalty_mobile_data/schema.py').read_text(), namespace)
        actual = set()
        for path in (ROOT / 'spx_loyalty_mobile_data/models').glob('*.py'):
            actual.update(declared_fields(path.read_text()))
        self.assertEqual(actual, set(namespace['PERSISTENT_FIELDS']))

    def test_xml_and_acl_references_resolve(self):
        known = set()
        references = []
        for addon in ('spx_loyalty_mobile', 'spx_loyalty_mobile_data'):
            root = ROOT / addon
            for path in root.rglob('*.py'):
                for cls in classes(path.read_text()):
                    known.add(addon + '.model_' + model_name(cls).replace('.', '_'))
            for path in root.rglob('*.xml'):
                tree = etree.parse(str(path))
                for node in tree.iter():
                    if node.get('id'):
                        known.add(addon + '.' + node.get('id'))
                    if node.get('ref'):
                        ref = node.get('ref')
                        references.append(ref if '.' in ref else addon + '.' + ref)
            for path in root.rglob('ir.model.access.csv'):
                for row in csv.DictReader(io.StringIO(path.read_text())):
                    ref = row['model_id:id']
                    references.append(ref if '.' in ref else addon + '.' + ref)
        for ref in references:
            if ref.startswith('spx_loyalty_mobile'):
                self.assertIn(ref, known)


if __name__ == '__main__':
    unittest.main(verbosity=2)
