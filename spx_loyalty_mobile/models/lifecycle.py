"""Administrator-only lifecycle controls; native records are never deleted."""
import base64
import json
from urllib.parse import urlsplit

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


def connection_origin(value):
    """Accept an HTTPS origin, including IPv6 and custom TLS ports."""
    raw = (value or '').strip()
    try:
        url = urlsplit(raw)
        port = url.port
    except ValueError as error:
        raise UserError(_('Enter a valid HTTPS address.')) from error
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.path not in ('', '/') or url.query or url.fragment
            or any(char.isspace() or ord(char) < 32 for char in raw)
            or '\\' in raw or port == 0):
        raise UserError(_('Enter the HTTPS origin only, for example https://jennys.example. Leave out /odoo, paths and credentials.'))
    return raw.rstrip('/')


class AppRemoval(models.TransientModel):
    _name = 'spx.mobile.removal'
    _description = 'Customer app uninstall options'

    mode = fields.Selection([
        ('keep', 'Keep app data for reinstall (recommended)'),
        ('remove', 'Remove app settings and history'),
    ], default='keep', required=True)
    confirm_remove = fields.Boolean('I understand that app settings and history cannot be restored after removal')

    def action_continue(self):
        self.ensure_one()
        if not self.env.is_system():
            raise AccessError(_('Only an administrator can remove the customer app.'))
        if self.mode == 'remove' and not self.confirm_remove:
            raise UserError(_('Confirm removal of app settings and history to continue.'))
        name = 'spx_loyalty_mobile_data' if self.mode == 'remove' else 'spx_loyalty_mobile'
        module = self.env['ir.module.module'].search([('name', '=', name)], limit=1)
        if module.state not in ('installed', 'to upgrade'):
            raise UserError(_('This module is not installed. Refresh the page.'))
        # Open the native impact preview. Nothing is uninstalled by this method.
        return module.button_uninstall_wizard()


class AppConnection(models.TransientModel):
    _name = 'spx.mobile.connection'
    _description = 'Customer app connection configuration'

    website_id = fields.Many2one('website', required=True)
    origin = fields.Char('Odoo HTTPS address', required=True)
    database = fields.Char(compute='_compute_database', string='Database', readonly=True)
    config_file = fields.Binary(compute='_compute_config_file', string='App connection file')
    config_filename = fields.Char(default='jennys-connection.json', readonly=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        website_id = values.get('website_id') or self.env.context.get('default_website_id')
        website = self.env['website'].browse(website_id).exists() if website_id else self.env['website'].search([], limit=1)
        if website:
            values.update(website_id=website.id, origin=website.spx_mobile_account_origin or website.domain or '')
        return values

    @api.onchange('website_id')
    def _onchange_website_id(self):
        if self.website_id:
            self.origin = self.website_id.spx_mobile_account_origin or self.website_id.domain or ''

    @api.depends_context('uid')
    def _compute_database(self):
        for record in self:
            record.database = self.env.cr.dbname

    @api.depends('origin')
    def _compute_config_file(self):
        for record in self:
            record.config_file = False
            if not record.origin:
                continue
            try:
                origin = connection_origin(record.origin)
            except UserError:
                continue
            record.config_file = base64.b64encode(json.dumps({
                'JENNYS_API_URL': origin,
                'JENNYS_DATABASE': self.env.cr.dbname,
            }, indent=2).encode())

    def action_apply(self):
        self.ensure_one()
        if not self.env.is_system():
            raise AccessError(_('Only an administrator can configure the customer app.'))
        origin = connection_origin(self.origin)
        self.website_id.write({'spx_mobile_account_origin': origin})
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'title': _('Connection details saved'),
            'message': _('Use the downloaded connection file for the Android/iOS build. Existing APKs keep their built-in address.'),
            'type': 'success', 'sticky': True,
        }}
