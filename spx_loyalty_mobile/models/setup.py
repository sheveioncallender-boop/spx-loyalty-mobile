"""Administrator setup using existing native records; no automatic business data."""
from markupsafe import Markup

from odoo import _, api, fields, models, Command
from odoo.exceptions import AccessError, UserError

from .lifecycle import connection_origin


class Website(models.Model):
    _inherit = 'website'

    spx_mobile_setup_status = fields.Html(
        string='Setup checklist', compute='_compute_mobile_setup_status',
        groups='base.group_system', sanitize=True)

    def _mobile_setup_admin(self):
        if not self.env.is_system():
            raise AccessError(_('Only an administrator can configure the customer app.'))
        self.check_access('write')

    def _mobile_program_domain(self):
        self.ensure_one()
        return [('program_type', '=', 'loyalty'), ('active', '=', True),
                ('company_id', 'in', [False, self.company_id.id]),
                ('website_id', 'in', [False, self._origin.id])]

    def _mobile_origin_candidate(self):
        self.ensure_one()
        # Never infer one website's host from another website on a shared database.
        candidates = [self.spx_mobile_account_origin, self.domain]
        if self.env['website'].search_count([]) == 1:
            candidates.append(self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
        for value in candidates:
            if value:
                try:
                    return connection_origin(value)
                except UserError:
                    pass
        return False

    def _mobile_setup_rows(self):
        self.ensure_one()
        rows = []
        try:
            connection_origin(self.spx_mobile_account_origin)
            origin_ok = True
        except UserError:
            origin_ok = False
        rows.append((_('App connection'),
                     _('Configured') if self.spx_mobile_enabled and origin_ok else _('Needs setup'),
                     _('Publisher must verify the matching app build and website routing.')
                     if self.spx_mobile_enabled and origin_ok else
                     _('Enter the public HTTPS address and enable the customer app.')))
        compatible = self.env['loyalty.program'].search(self._mobile_program_domain())
        selected = self.spx_mobile_program_ids
        loyalty_ok = bool(selected) and not (selected - compatible)
        rows.append((_('Loyalty'), _('Configured') if loyalty_ok else _('Needs setup'),
                     _('Selected programs remain managed by native Odoo earning and reward rules.')
                     if loyalty_ok else _('Choose an existing compatible loyalty program. If none exists, use Manage loyalty programs to create its earning and reward rules.')))
        signup_issues = self._mobile_signup_setup_issues()
        rows.append((_('Member signup'), _('Enabled') if self.spx_mobile_signup_enabled and not signup_issues else _('Not ready') if signup_issues else _('Off'),
                     '\n'.join(signup_issues) if signup_issues else
                     _('Customer signup is configured. Verify email delivery before release.') if self.spx_mobile_signup_enabled else
                     _('Enable verified signup when you want new members to register.')))
        config = self.spx_mobile_pos_config_id
        valid_pos = bool(config and config.active and config.module_pos_restaurant and config.company_id == self.company_id)
        if not valid_pos:
            rows.append((_('Dine-in ordering'), _('Optional — not configured'), _('Select this website’s restaurant POS to offer ordering.')))
        else:
            # Same native availability and publication filters as the app catalog.
            domain = self.env['product.template']._load_pos_data_domain({}, config) + [
                ('active', '=', True), ('is_published', '=', True),
                ('website_id', 'in', [False, self._origin.id]),
                ('company_id', 'in', [False, self.company_id.id]),
            ]
            menu_exists = bool(self.env['product.template'].search(domain, limit=1))
            opened = config.current_session_id.state == 'opened'
            notes = []
            if not menu_exists:
                notes.append(_('Publish the menu products that are available in this POS.'))
            if not opened:
                notes.append(_('Open the POS register when staff are ready to accept orders.'))
            notes.append(_('Verify products, prices, taxes and kitchen routing with a test order.'))
            rows.append((_('Dine-in ordering'), _('Ready for order testing') if menu_exists and opened else _('Needs attention'), ' '.join(notes)))
        has_mail_server = bool(self.env['ir.mail_server'].search([], limit=1))
        rows.append((_('Email delivery'), _('Delivery test required'),
                     _('An outgoing mail server is configured. Verify sender authorization and delivery.') if has_mail_server else
                     _('No outgoing mail server is configured in Odoo. Configure one, or confirm your host provides mail delivery.')))
        rows.append((_('Birthday credit and gift cards'), _('Optional'),
                     _('Configure these in Optional features only if required. They do not block basic loyalty setup.')))
        return rows

    @api.depends('spx_mobile_enabled', 'spx_mobile_account_origin', 'spx_mobile_program_ids',
                 'spx_mobile_pos_config_id', 'company_id', 'spx_mobile_signup_enabled',
                 'spx_mobile_signup_program_id', 'spx_mobile_mail_from',
                 'spx_mobile_terms', 'spx_mobile_privacy', 'spx_mobile_policy_version')
    def _compute_mobile_setup_status(self):
        row = Markup('<tr><th scope="row">%s</th><td><strong>%s</strong></td><td>%s</td></tr>')
        for website in self:
            website.spx_mobile_setup_status = Markup(
                '<table class="table table-sm"><thead><tr><th>Feature</th><th>Status</th>'
                '<th>Next step</th></tr></thead><tbody>%s</tbody></table>'
            ) % Markup('').join(row % values for values in website._mobile_setup_rows())

    @api.model
    def action_mobile_setup(self):
        self._mobile_setup_admin()
        websites = self.search([('company_id', 'in', self.env.companies.ids)])
        form = self.env.ref('spx_loyalty_mobile.website_app_setup_form')
        action = {'type': 'ir.actions.act_window', 'name': _('App setup'), 'res_model': 'website',
                  'views': [(False, 'list'), (form.id, 'form')],
                  'domain': [('id', 'in', websites.ids)], 'context': {'create': False}}
        if len(websites) == 1:
            return websites.action_mobile_setup_wizard()
        return action

    def _mobile_setup_status_action(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('App setup'), 'res_model': 'website',
                'res_id': self.id, 'views': [(self.env.ref('spx_loyalty_mobile.website_app_setup_form').id, 'form')]}

    def action_mobile_setup_wizard(self):
        self.ensure_one()
        self._mobile_setup_admin()
        if self.company_id not in self.env.companies:
            raise AccessError(_('Select this website’s company first.'))
        pos = self.spx_mobile_pos_config_id
        if not pos:
            candidates = self.env['pos.config'].search([
                ('active', '=', True), ('module_pos_restaurant', '=', True),
                ('company_id', '=', self.company_id.id)], limit=2)
            pos = candidates if len(candidates) == 1 else pos
        programs = self.spx_mobile_program_ids
        wizard = self.env['spx.mobile.setup.wizard'].create({
            'website_id': self.id, 'source_revision': self.write_date.isoformat(),
            'origin': self.spx_mobile_account_origin or self._mobile_origin_candidate(),
            'brand': self.spx_mobile_brand or self.name,
            'enable_app': self.spx_mobile_enabled or not (self.spx_mobile_account_origin or programs),
            'pos_config_id': pos.id, 'loyalty_mode': 'existing' if programs else 'template',
            'loyalty_program_ids': [Command.set(programs.ids)],
            'gift_program_ids': [Command.set(self.spx_gift_program_ids.ids)],
            'gift_product_ids': [Command.set(self.spx_gift_product_ids.ids)],
            'birthday_program_id': self.spx_birthday_program_id.id,
            'birthday_enabled': self.spx_birthday_enabled,
            'birthday_amount': self.spx_birthday_amount or 50,
            'birthday_days': self.spx_birthday_days or 21,
            'signup_enabled': self.spx_mobile_signup_enabled,
            'signup_program_id': self.spx_mobile_signup_program_id.id or (programs.id if len(programs) == 1 else False),
            'mail_from': self.spx_mobile_mail_from, 'policy_version': self.spx_mobile_policy_version or '1',
            'terms': self.spx_mobile_terms, 'privacy': self.spx_mobile_privacy,
        })
        return wizard._window()

    def action_mobile_detect_settings(self):
        self.ensure_one()
        self._mobile_setup_admin()
        values = {}
        if not self.spx_mobile_account_origin:
            origin = self._mobile_origin_candidate()
            if origin:
                values['spx_mobile_account_origin'] = origin
        programs = self.spx_mobile_program_ids
        if not programs:
            candidates = self.env['loyalty.program'].search(self._mobile_program_domain(), limit=2)
            if len(candidates) == 1:
                programs = candidates
                values['spx_mobile_program_ids'] = [Command.set(programs.ids)]
        if not self.spx_mobile_signup_program_id and len(programs) == 1:
            if programs in self.env['loyalty.program'].search(self._mobile_program_domain()):
                values['spx_mobile_signup_program_id'] = programs.id
        if not self.spx_mobile_pos_config_id:
            configs = self.env['pos.config'].search([
                ('active', '=', True), ('module_pos_restaurant', '=', True),
                ('company_id', '=', self.company_id.id)], limit=2)
            if len(configs) == 1:
                values['spx_mobile_pos_config_id'] = configs.id
        if values:
            self.write(values)
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'title': _('Detected settings saved') if values else _('No unambiguous settings to fill'),
            'message': _('Only empty fields with one compatible choice are filled. Review the checklist and complete the remaining choices.'),
            'type': 'info', 'sticky': False,
            'next': {'type': 'ir.actions.act_window', 'name': _('App setup'), 'res_model': 'website',
                     'res_id': self.id, 'views': [(self.env.ref('spx_loyalty_mobile.website_app_setup_form').id, 'form')]},
        }}

    def action_mobile_programs(self):
        self.ensure_one()
        self._mobile_setup_admin()
        return {'type': 'ir.actions.act_window', 'name': _('Loyalty programs'),
                'res_model': 'loyalty.program', 'view_mode': 'list,form',
                'domain': self._mobile_program_domain(),
                'context': {'default_program_type': 'loyalty', 'default_company_id': self.company_id.id,
                            'default_website_id': self.id}}

    def action_mobile_connection(self):
        self.ensure_one()
        self._mobile_setup_admin()
        action = self.env['ir.actions.actions']._for_xml_id('spx_loyalty_mobile.mobile_connection_action')
        action['context'] = {'default_website_id': self.id}
        return action

    def action_mobile_optional_features(self):
        self.ensure_one()
        self._mobile_setup_admin()
        return {'type': 'ir.actions.act_window', 'name': _('Optional features and advanced settings'),
                'res_model': 'website', 'res_id': self.id,
                'views': [(self.env.ref('website.view_website_form').id, 'form')]}

    def action_mobile_email_settings(self):
        self.ensure_one()
        self._mobile_setup_admin()
        return {'type': 'ir.actions.act_window', 'name': _('Outgoing mail servers'),
                'res_model': 'ir.mail_server', 'view_mode': 'list,form'}
