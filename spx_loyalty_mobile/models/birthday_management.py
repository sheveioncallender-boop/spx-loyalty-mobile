"""Staff management for birthdays. Native loyalty cards own all usable value."""
import math
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from .engagement import birthday_in_year


def require_admin(env):
    if not env.user.has_group('base.group_system'):
        raise AccessError(_('Only an administrator can manage birthday credits.'))


def next_birthday(birthday, today):
    upcoming = birthday_in_year(birthday, today.year)
    return upcoming if upcoming >= today else birthday_in_year(birthday, today.year + 1)


class Website(models.Model):
    _inherit = 'website'

    @api.constrains('spx_birthday_field_id')
    def _check_birthday_field(self):
        for w in self:
            f = w.spx_birthday_field_id
            if f and (f.model != 'res.partner' or f.ttype != 'date' or not f.store
                      or f.name not in self.env['res.partner']._fields):
                raise ValidationError(_('Select a stored Date field on customer contacts.'))

    def _spx_birth_date(self, partner):
        self.ensure_one()
        source = self.spx_birthday_field_id
        return (partner[source.name] if source else False) or partner.spx_mobile_birthday

    def _spx_birthday_customers(self):
        self.ensure_one()
        domain = [('active', '=', True), ('is_company', '=', False), ('parent_id', '=', False),
                  ('company_id', 'in', [False, self.company_id.id])]
        source = self.spx_birthday_field_id
        if source and source.name != 'spx_mobile_birthday':
            domain += ['|', (source.name, '!=', False), ('spx_mobile_birthday', '!=', False)]
        else:
            domain += [('spx_mobile_birthday', '!=', False)]
        return self.env['res.partner'].search(domain).filtered(lambda p: not any(not u.share for u in p.user_ids))

    def _spx_birthday_cards(self, partners):
        self.ensure_one()
        # Include earlier awarded programs if the default program has since changed.
        awards = self.env['spx.mobile.birthday.award'].sudo().search([
            ('website_id', '=', self.id), ('partner_id', 'in', partners.ids)])
        return self.env['loyalty.card'].sudo().search([
            ('partner_id', 'in', partners.ids), ('program_type', '=', 'gift_card'),
            '|', ('program_id', '=', self.spx_birthday_program_id.id), ('id', 'in', awards.card_id.ids),
        ]).filtered(lambda c: (not c.company_id or c.company_id == self.company_id)
                   and (not c.program_id.website_id or c.program_id.website_id == self))

    def _spx_check_birthday_admin(self):
        require_admin(self.env)
        self.ensure_one()
        self.check_access('read')
        if self.company_id not in self.env.companies:
            raise AccessError(_('Select this website’s company first.'))

    def _spx_birthday_card_year(self, card):
        self.ensure_one()
        return fields.Datetime.context_timestamp(
            self.with_context(tz=self.spx_member_timezone or 'America/Port_of_Spain'), card.create_date).year

    @api.model
    def action_spx_birthday_overview(self):
        require_admin(self.env)
        websites = self.search([('spx_mobile_enabled', '=', True), ('company_id', 'in', self.env.companies.ids)])
        if len(websites) == 1:
            return websites.action_spx_birthday_customers()
        return self.env['ir.actions.actions']._for_xml_id('spx_loyalty_mobile.birthday_settings_action')

    def action_spx_birthday_customers(self):
        self._spx_check_birthday_admin()
        return {'type': 'ir.actions.act_window', 'name': _('Customer birthdays — %s') % self.name,
                'res_model': 'res.partner', 'view_mode': 'list,form',
                'views': [(self.env.ref('spx_loyalty_mobile.birthday_customer_list').id, 'list'), (False, 'form')],
                'search_view_id': self.env.ref('spx_loyalty_mobile.birthday_customer_search').id,
                'domain': [('id', 'in', self._spx_birthday_customers().ids)],
                'context': dict(self.env.context, spx_birthday_website_id=self.id)}

    def action_spx_issue_birthday(self):
        self._spx_check_birthday_admin()
        return {'type': 'ir.actions.act_window', 'name': _('Issue birthday credit'),
                'res_model': 'spx.mobile.birthday.issue', 'view_mode': 'form', 'target': 'new',
                'context': dict(self.env.context, default_website_id=self.id)}

    def action_spx_birthday_history(self):
        self._spx_check_birthday_admin()
        action = self.env['ir.actions.actions']._for_xml_id('spx_loyalty_mobile.birthday_action')
        action['domain'] = [('website_id', '=', self.id)]
        return action


class Partner(models.Model):
    _inherit = 'res.partner'

    spx_birthday_date = fields.Date('Birthday', compute='_compute_birthday_overview', groups='base.group_system')
    spx_birthday_next = fields.Date('Next birthday', compute='_compute_birthday_overview', groups='base.group_system')
    spx_birthday_countdown = fields.Integer('Days until birthday', compute='_compute_birthday_overview',
        search='_search_birthday_countdown', groups='base.group_system')
    spx_birthday_currency_id = fields.Many2one('res.currency', compute='_compute_birthday_overview', groups='base.group_system')
    spx_birthday_balance = fields.Monetary('Available birthday credit', currency_field='spx_birthday_currency_id',
        compute='_compute_birthday_overview', groups='base.group_system')
    spx_birthday_expiry = fields.Date('Next credit expiry', compute='_compute_birthday_overview', groups='base.group_system')
    spx_birthday_remaining = fields.Integer('Days left to use credit', compute='_compute_birthday_overview', groups='base.group_system')
    spx_birthday_issued = fields.Boolean('Issued this year', compute='_compute_birthday_overview', groups='base.group_system')

    def _birthday_website(self):
        require_admin(self.env)
        w = self.env['website'].browse(self.env.context.get('spx_birthday_website_id')).exists()
        if not w:
            return w
        w._spx_check_birthday_admin()
        return w

    @api.depends_context('spx_birthday_website_id', 'company')
    @api.depends('spx_mobile_birthday')
    def _compute_birthday_overview(self):
        w = self._birthday_website()
        today = w._spx_today() if w else fields.Date.context_today(self)
        cards = w._spx_birthday_cards(self) if w else self.env['loyalty.card']
        awards = self.env['spx.mobile.birthday.award'].search([
            ('company_id', '=', w.company_id.id), ('year', '=', today.year), ('partner_id', 'in', self.ids)]) if w else self.env['spx.mobile.birthday.award']
        for p in self:
            birth = w._spx_birth_date(p) if w else p.spx_mobile_birthday
            upcoming = next_birthday(birth, today) if birth and birth < today else False
            owned = cards.filtered(lambda c: c.partner_id == p and c.program_id.active)
            currency = w.currency_id if w else self.env.company.currency_id
            live = owned.filtered(lambda c: c.currency_id == currency and c.points > 0
                                  and (not c.expiration_date or c.expiration_date >= today))
            expiries = live.mapped('expiration_date')
            expiry = min([d for d in expiries if d], default=False)
            p.spx_birthday_date = birth
            p.spx_birthday_next = upcoming
            p.spx_birthday_countdown = (upcoming - today).days if upcoming else 0
            p.spx_birthday_currency_id = currency
            p.spx_birthday_balance = sum(live.mapped('points'))
            p.spx_birthday_expiry = expiry
            p.spx_birthday_remaining = (expiry - today).days + 1 if expiry else 0
            p.spx_birthday_issued = p in awards.partner_id or any(w._spx_birthday_card_year(c) == today.year for c in owned)

    def _search_birthday_countdown(self, operator, value):
        w = self._birthday_website()
        ops = {'=': lambda a, b: a == b, '<=': lambda a, b: a <= b, '>=': lambda a, b: a >= b,
               '<': lambda a, b: a < b, '>': lambda a, b: a > b,
               'in': lambda a, b: a in b, 'not in': lambda a, b: a not in b}
        if operator not in ops:
            return NotImplemented
        if not w:
            return [('id', '=', 0)]
        today = w._spx_today()
        ids = [p.id for p in w._spx_birthday_customers() if w._spx_birth_date(p) < today
               and ops[operator]((next_birthday(w._spx_birth_date(p), today) - today).days, value)]
        return [('id', 'in', ids)]

    def action_spx_issue_birthday(self):
        self.ensure_one()
        self.check_access('read')
        w = self._birthday_website()
        if not w:
            raise UserError(_('Open Customer birthdays from Member Extras first.'))
        action = w.action_spx_issue_birthday()
        action['context']['default_partner_id'] = self.id
        return action

    def action_spx_birthday_cards(self):
        self.ensure_one()
        self.check_access('read')
        w = self._birthday_website()
        if not w:
            raise UserError(_('Open Customer birthdays from Member Extras first.'))
        return {'type': 'ir.actions.act_window', 'name': _('Birthday cards'),
                'res_model': 'loyalty.card', 'view_mode': 'list,form',
                'domain': [('id', 'in', w._spx_birthday_cards(self).ids)]}


class BirthdayAward(models.Model):
    _inherit = 'spx.mobile.birthday.award'

    reason = fields.Char(readonly=True)
    days_remaining = fields.Integer('Days left to use credit', compute='_compute_remaining')

    def _compute_remaining(self):
        for award in self:
            today = award.website_id._spx_today()
            award.days_remaining = max(0, (award.expires - today).days + 1) if award.expires else 0

    def action_open_native_card(self):
        require_admin(self.env)
        self.ensure_one()
        self.check_access('read')
        self.card_id.check_access('read')
        return {'type': 'ir.actions.act_window', 'name': _('Birthday card'),
                'res_model': 'loyalty.card', 'res_id': self.card_id.id, 'view_mode': 'form'}

    def action_adjust_native_balance(self):
        require_admin(self.env)
        self.ensure_one()
        self.check_access('read')
        self.card_id.check_access('write')
        return self.card_id.action_loyalty_update_balance()

    @api.model
    def _issue_credit(self, w, partner, amount, days, reason):
        # Shared by the cron and the staff wizard; private, not remotely callable.
        w._check_engagement()
        today = w._spx_today()
        if not w.spx_mobile_enabled or not w.spx_birthday_enabled:
            raise UserError(_('Configure and enable birthday credit for this website first.'))
        birth = w._spx_birth_date(partner)
        if (not partner.active or partner.is_company or partner.parent_id or not birth or birth >= today
                or (partner.company_id and partner.company_id != w.company_id)
                or any(not u.share for u in partner.user_ids)):
            raise UserError(_('Select an active individual customer in this company with a valid birthday.'))
        if not math.isfinite(amount) or amount <= 0 or not 1 <= days <= 366:
            raise ValidationError(_('Enter a positive credit amount and 1 to 366 days of validity.'))
        self.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', (739401, w.company_id.id))
        existing = self.sudo().search([('company_id', '=', w.company_id.id), ('partner_id', '=', partner.id), ('year', '=', today.year)], limit=1)
        if existing:
            return existing
        # Native cards issued manually this year must not receive a second award.
        native = w._spx_birthday_cards(partner).filtered(lambda c: w._spx_birthday_card_year(c) == today.year)
        if native:
            raise UserError(_('This customer already has a birthday card issued this year. Open their native card to adjust its balance.'))
        card = self.env['loyalty.card'].sudo().with_context(loyalty_no_mail=True).create({
            'program_id': w.spx_birthday_program_id.id, 'partner_id': partner.id,
            'points': amount, 'expiration_date': today + timedelta(days=days - 1)})
        self.env['loyalty.history'].sudo().create({'card_id': card.id, 'description': reason, 'issued': amount})
        award = self.sudo().create({'partner_id': partner.id, 'website_id': w.id, 'company_id': w.company_id.id,
            'year': today.year, 'issued_on': today, 'card_id': card.id, 'amount': amount, 'reason': reason})
        self.env['spx.mobile.message'].sudo().create({'name': _('Happy birthday!'), 'body': w.spx_birthday_message,
            'partner_id': partner.id, 'website_id': w.id})
        return award


class BirthdayIssue(models.TransientModel):
    _name = 'spx.mobile.birthday.issue'
    _description = 'Issue native birthday credit'

    website_id = fields.Many2one('website', required=True, domain="[('spx_mobile_enabled', '=', True)]")
    partner_id = fields.Many2one('res.partner', string='Customer', required=True,
        domain="[('is_company', '=', False), ('parent_id', '=', False)]")
    currency_id = fields.Many2one(related='website_id.currency_id')
    amount = fields.Monetary(required=True, compute='_compute_defaults', store=True, readonly=False)
    days = fields.Integer('Valid for (days)', required=True, compute='_compute_defaults', store=True, readonly=False)
    reason = fields.Char(required=True, default='Birthday credit issued by staff')

    @api.depends('website_id')
    def _compute_defaults(self):
        for wizard in self:
            wizard.amount = wizard.website_id.spx_birthday_amount
            wizard.days = wizard.website_id.spx_birthday_days or 21

    def action_issue(self):
        require_admin(self.env)
        self.ensure_one()
        self.check_access('write')
        self.website_id._spx_check_birthday_admin()
        self.partner_id.check_access('read')
        if not self.reason or not self.reason.strip():
            raise UserError(_('Enter a reason for this credit.'))
        award = self.env['spx.mobile.birthday.award']._issue_credit(
            self.website_id, self.partner_id, self.amount, self.days, self.reason.strip())
        return award.with_env(self.env).action_open_native_card()
