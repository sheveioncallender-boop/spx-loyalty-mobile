"""Transfer schema ownership in place. No customer export, copy, or backup."""
from .schema import EXTENDED_MODELS, PERSISTENT_FIELDS, PERSISTENT_MODELS

SOURCE = 'spx_loyalty_mobile'
TARGET = 'spx_loyalty_mobile_data'


def adopt_existing_data(env):
    """Run before this new dependency is initialized on an existing database.

    The tables, columns, record IDs and balances remain untouched. Transfer
    their XML IDs and relational ownership before upgrading the connector, so
    Odoo's removal of obsolete connector metadata cannot drop customer data.
    A partial/conflicting ownership move fails instead of deleting records.
    On a fresh instance there is simply no old metadata to move.
    """
    # Only persistent schema moves. Computed UI fields and the birthday wizard
    # stay with the connector and must disappear when it is uninstalled.
    env.cr.execute("""
        SELECT id FROM ir_model_fields
        WHERE (model, name) IN %s
           OR (model IN %s AND name IN ('id', 'create_uid', 'create_date', 'write_uid', 'write_date', 'display_name'))
    """, (PERSISTENT_FIELDS, PERSISTENT_MODELS))
    field_ids = [row[0] for row in env.cr.fetchall()]
    env.cr.execute("""
        UPDATE ir_model_data d SET module = %s
        WHERE d.module = %s AND (
            (d.model = 'ir.model' AND d.res_id IN
                (SELECT id FROM ir_model WHERE model IN %s))
            OR (d.model = 'ir.model.fields' AND d.res_id = ANY(%s))
            OR (d.model = 'ir.model.fields.selection' AND d.res_id IN
                (SELECT id FROM ir_model_fields_selection WHERE field_id = ANY(%s)))
            OR (d.model = 'ir.model.constraint' AND d.res_id IN
                (SELECT c.id FROM ir_model_constraint c JOIN ir_model m ON m.id=c.model
                 WHERE m.model IN %s))
            OR (d.model = 'ir.rule')
            OR (d.model = 'ir.model.access' AND d.name != 'access_spx_birthday_issue_admin')
        )
    """, (TARGET, SOURCE, EXTENDED_MODELS, field_ids, field_ids, EXTENDED_MODELS))
    env.cr.execute("""
        UPDATE ir_model_constraint SET module = target.id
        FROM ir_module_module source, ir_module_module target
        WHERE ir_model_constraint.module = source.id
          AND source.name = %s AND target.name = %s
          AND ir_model_constraint.model IN (SELECT id FROM ir_model WHERE model IN %s)
    """, (SOURCE, TARGET, EXTENDED_MODELS))
    env.cr.execute("""
        UPDATE ir_model_relation SET module = target.id
        FROM ir_module_module source, ir_module_module target
        WHERE ir_model_relation.module = source.id
          AND source.name = %s AND target.name = %s
          AND ir_model_relation.model IN (SELECT id FROM ir_model WHERE model IN %s)
    """, (SOURCE, TARGET, EXTENDED_MODELS))
    env.invalidate_all()
    env.registry.clear_cache()


def detach_mail_references(env):
    """Keep sent native mail history readable after explicit app-data removal."""
    # These keys only remember which native programs the setup guide created.
    # Ordinary connector uninstall retains them; full data removal clears them.
    # The native programs, products, cards and balances are never removed here.
    env['ir.config_parameter'].sudo().search([
        ('key', '=like', 'spx_mobile.setup_template.%'),
    ]).filtered(lambda parameter: parameter.key.startswith('spx_mobile.setup_template.')).unlink()
    mail = env['mail.mail'].sudo().search([('model', '=like', 'spx.mobile.%')])
    mail |= env['spx.mobile.message'].sudo().search([]).mail_id
    mail.filtered(lambda m: m.state in ('outgoing', 'exception')).write({'state': 'cancel'})
    env['mail.message'].sudo().search([('model', '=like', 'spx.mobile.%')]).write({
        'model': False, 'res_id': 0,
    })
