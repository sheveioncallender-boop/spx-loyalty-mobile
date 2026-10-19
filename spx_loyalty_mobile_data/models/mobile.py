"""Passive customer app fields and tables; no business overrides or jobs."""
from uuid import uuid4
from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    spx_mobile_enabled = fields.Boolean(string='Enable customer app', groups='base.group_system')

    spx_mobile_brand = fields.Char(string='App brand', default="Jenny’s on the Boulevard")

    spx_mobile_pos_config_id = fields.Many2one(
        'pos.config', string='Dine-in Point of Sale', groups='base.group_system',
        domain="[('module_pos_restaurant', '=', True), ('company_id', '=', company_id)]",
        help='App baskets become unpaid native orders in this POS. Staff assign tables, send to the kitchen and take payment.',
    )

    spx_mobile_program_ids = fields.Many2many(
        'loyalty.program', 'spx_mobile_website_program_rel', 'website_id', 'program_id',
        string='Visible loyalty programs', groups='base.group_system',
        domain="[('program_type', '=', 'loyalty')]",
    )


class Partner(models.Model):
    _inherit = 'res.partner'

    spx_mobile_email = fields.Boolean(string='App promotional emails', default=False)


class MobileMessage(models.Model):
    _name = 'spx.mobile.message'

    _description = 'Customer app message'

    _order = 'create_date desc, id desc'

    name = fields.Char(string='Title', required=True)

    body = fields.Text(required=True)

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)

    website_id = fields.Many2one('website', required=True, ondelete='cascade', index=True)

    company_id = fields.Many2one(related='website_id.company_id', store=True, index=True)

    read_at = fields.Datetime(readonly=True)

    mail_id = fields.Many2one('mail.mail', readonly=True, copy=False, ondelete='set null')

    email_queued = fields.Boolean(readonly=True, copy=False)


class MobileOperation(models.Model):
    _name = 'spx.mobile.operation'

    _description = 'Mobile cart request deduplication'

    key = fields.Char(required=True, index=True)

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)

    website_id = fields.Many2one('website', required=True, ondelete='cascade')

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')

    _key_unique = models.Constraint(
        'UNIQUE(partner_id, website_id, key)', 'This request has already been processed. Refresh your cart.')


class MobileBasket(models.Model):
    _name = 'spx.mobile.basket'

    _description = 'Customer app basket before submission'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)

    website_id = fields.Many2one('website', required=True, ondelete='cascade', index=True)

    token = fields.Char(required=True, default=lambda self: str(uuid4()), copy=False)

    items = fields.Json(default=dict)

    _owner_unique = models.Constraint('UNIQUE(partner_id, website_id)', 'One basket per customer and website.')


class MobileSubmission(models.Model):
    _name = 'spx.mobile.submission'

    _description = 'Customer app submission receipt and duplicate protection'

    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)

    website_id = fields.Many2one('website', required=True, ondelete='cascade', index=True)

    key = fields.Char(required=True, index=True)

    quote = fields.Char(required=True)

    order_id = fields.Many2one('pos.order', ondelete='set null', readonly=True)

    receipt = fields.Json(required=True)

    _request_unique = models.Constraint('UNIQUE(partner_id, website_id, key)', 'This order has already been received.')
