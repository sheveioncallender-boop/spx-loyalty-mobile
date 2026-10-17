"""Database-free regression for the Odoo 19 pre-upgrade read boundary.

Import after odoo.init and configuration of the core and connector addons paths.
Uses Odoo's actual field-selection methods; only database fetching is simulated.
This does not replace an installation/upgrade test against PostgreSQL.
"""
from types import SimpleNamespace
from unittest import TestCase

from psycopg2.errors import UndefinedColumn
from odoo import fields
from odoo.orm.models import BaseModel
from odoo.addons.spx_loyalty_mobile.models import onboarding


class LegacySchemaProbe:
    def __init__(self, definition, native_field):
        self.env = SimpleNamespace(context={})
        self._fields = {
            name: field for name, field in vars(definition).items()
            if isinstance(field, fields.Field)
        }
        self.absent_columns = set(self._fields)
        self._fields[native_field] = SimpleNamespace(name=native_field, prefetch=True)
        self.requested = []

    def _has_field_access(self, field, operation):
        # The reported failure occurs for an administrator with field access.
        return True

    def fetch(self, names):
        self.requested = list(names)
        if self.absent_columns.intersection(names):
            raise UndefinedColumn('The signup columns have not been migrated yet')


class TestOnboardingPrefetch(TestCase):
    def test_native_user_partner_read_survives_pending_schema_upgrade(self):
        probe = LegacySchemaProbe(onboarding.Users, 'partner_id')
        BaseModel._fetch_field(probe, probe._fields['partner_id'])
        self.assertEqual(probe.requested, ['partner_id'])

    def test_native_partner_name_read_survives_pending_schema_upgrade(self):
        probe = LegacySchemaProbe(onboarding.Partner, 'name')
        BaseModel._fetch_field(probe, probe._fields['name'])
        self.assertEqual(probe.requested, ['name'])

    def test_native_website_read_survives_pending_schema_upgrade(self):
        probe = LegacySchemaProbe(onboarding.Website, 'company_id')
        BaseModel._fetch_field(probe, probe._fields['company_id'])
        self.assertEqual(probe.requested, ['company_id'])

    def test_default_search_fetch_excludes_unrequested_signup_columns(self):
        for definition in (onboarding.Users, onboarding.Partner, onboarding.Website):
            with self.subTest(model=definition._name):
                probe = LegacySchemaProbe(definition, 'name')
                selected = BaseModel._determine_fields_to_fetch(probe, None)
                probe.fetch([field.name for field in selected])
                self.assertEqual(probe.requested, ['name'])

    def test_explicit_signup_read_still_requires_real_database_columns(self):
        probe = LegacySchemaProbe(onboarding.Users, 'partner_id')
        with self.assertRaises(UndefinedColumn):
            BaseModel._fetch_field(probe, probe._fields['spx_mobile_verified_email'])

    def test_migrated_signup_fields_remain_readable(self):
        probe = LegacySchemaProbe(onboarding.Users, 'partner_id')
        probe.absent_columns.clear()
        BaseModel._fetch_field(probe, probe._fields['spx_mobile_verified_email'])
        self.assertIn('spx_mobile_verified_email', probe.requested)
