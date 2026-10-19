"""Member benefits and announcements; native loyalty.card owns money and expiry.

No overrides of POS, sale payment, accounting, or reward calculation.
"""


import math
from zoneinfo import ZoneInfo
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


def birthday_in_year(birthday, year):
    # February 29 members celebrate on February 28 in a non-leap year.
    try:
        return birthday.replace(year=year)
    except ValueError:
        return birthday.replace(year=year, day=28)


class Website(models.Model):
    _inherit = 'website'

    def _spx_today(self):
        self.ensure_one()
        return fields.Datetime.now().replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo(self.spx_member_timezone or 'America/Port_of_Spain')).date()

    def _spx_members(self):
        self.ensure_one()
        cards = self.env['loyalty.card'].sudo().search([
            ('program_id', 'in', self.spx_mobile_program_ids.ids), ('partner_id', '!=', False)])
        return cards.partner_id.filtered(lambda p: p.active and not p.is_company and any(
            u.active and u.share and u.has_group('base.group_portal') and u._mobile_verified_access()
            for u in p.user_ids))

    @api.constrains('spx_birthday_enabled', 'spx_birthday_program_id', 'spx_birthday_amount',
                    'spx_birthday_days', 'spx_birthday_message', 'spx_member_timezone',
                    'spx_gift_program_ids', 'spx_gift_product_ids', 'company_id')
    def _check_engagement(self):
        for w in self:
            try:
                ZoneInfo(w.spx_member_timezone or 'America/Port_of_Spain')
            except (KeyError, ValueError) as error:
                raise ValidationError(_('Choose a valid timezone, for example America/Port_of_Spain.')) from error
            for p in w.spx_gift_program_ids | w.spx_birthday_program_id:
                if p.program_type != 'gift_card' or (p.company_id and p.company_id != w.company_id) or (p.website_id and p.website_id != w):
                    raise ValidationError(_('Choose native gift card programs for this website and company.'))
            for p in w.spx_gift_program_ids | w.spx_birthday_program_id:
                rewards = p.reward_ids.filtered('active')
                if len(rewards) != 1 or rewards.reward_type != 'discount' or rewards.discount_mode != 'per_point' or rewards.discount != 1 or rewards.discount_applicability != 'order':
                    raise ValidationError(_('Use the native gift-card reward: 1 currency unit per point, applied to the whole order.'))
            if w.spx_birthday_program_id and w.spx_birthday_program_id in w.spx_gift_program_ids:
                raise ValidationError(_('Birthday promotional credit must use a separate program from purchased gift cards.'))
            if w.spx_birthday_enabled and w.spx_birthday_program_id.trigger_product_ids:
                raise ValidationError(_('Remove sale trigger products from the dedicated birthday credit program.'))
            if w.spx_birthday_enabled and (not w.spx_birthday_program_id or not w.spx_birthday_program_id.active or not w.spx_birthday_message
                    or not math.isfinite(w.spx_birthday_amount) or w.spx_birthday_amount <= 0
                    or not 1 <= w.spx_birthday_days <= 366
                    or w.spx_birthday_program_id.currency_id != w.currency_id):
                raise ValidationError(_('Set an active birthday program in the website currency, a positive amount, greeting and validity.'))
            for product in w.spx_gift_product_ids:
                if (product.company_id and product.company_id != w.company_id) or not any(
                        v in w.spx_gift_program_ids.trigger_product_ids for v in product.product_variant_ids):
                    raise ValidationError(_('Every gift product must trigger one of the selected native gift-card programs.'))


class BirthdayAward(models.Model):
    _inherit = 'spx.mobile.birthday.award'

    @api.model
    def _cron_birthdays(self):
        websites = self.env['website'].sudo().search([('spx_mobile_enabled', '=', True), ('spx_birthday_enabled', '=', True)])
        for w in websites:
            w._check_engagement()
            today = w._spx_today()
            # Serialize across websites in one company; the unique constraint is a final safeguard.
            self.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', (739401, w.company_id.id))
            issued = self.sudo().search([('company_id', '=', w.company_id.id), ('year', '=', today.year)]).partner_id
            customers = w._spx_birthday_customers()
            if w.spx_birthday_audience != 'customers':
                customers &= w._spx_members()
            for partner in customers - issued:
                birth = w._spx_birth_date(partner)
                if not birth or birth >= today or birthday_in_year(birth, today.year) != today:
                    continue
                # Respect cards already issued directly in the native program.
                if any(w._spx_birthday_card_year(c) == today.year for c in w._spx_birthday_cards(partner)):
                    continue
                self._issue_credit(w, partner, w.spx_birthday_amount, w.spx_birthday_days,
                                   _('Birthday credit %s') % today.year)


class Announcement(models.Model):
    _inherit = 'spx.mobile.announcement'

    def _lock(self):
        self.env.cr.execute('SELECT id FROM spx_mobile_announcement WHERE id IN %s FOR UPDATE', (tuple(self.ids),))
        self.invalidate_recordset()

    def write(self, vals):
        if any(k in vals for k in ('name', 'body', 'website_id', 'audience', 'partner_ids', 'scheduled_at')) and any(r.state != 'draft' for r in self):
            raise UserError(_('Published or scheduled announcements cannot be edited. Create a new draft.'))
        return super().write(vals)

    def action_schedule(self):
        self.check_access('write')
        self._lock()
        for r in self:
            if r.state != 'draft' or not r.scheduled_at or r.scheduled_at <= fields.Datetime.now():
                raise UserError(_('Choose a future publication time on a draft announcement.'))
            r.state = 'scheduled'

    def action_cancel(self):
        self.check_access('write')
        self._lock()
        self.filtered(lambda r: r.state in ('draft', 'scheduled')).write({'state': 'cancelled'})

    def action_publish(self):
        self.check_access('write')
        self._lock()
        self._publish()

    def _publish(self):
        for r in self.filtered(lambda a: a.state in ('draft', 'scheduled')):
            if not r.website_id.spx_mobile_enabled:
                raise UserError(_('Enable the customer app before publishing.'))
            audience = r.website_id._spx_members().filtered('spx_member_announcements')
            if r.audience == 'selected':
                audience &= r.partner_ids
            self.env['spx.mobile.message'].sudo().create([{'name': r.name, 'body': r.body,
                'website_id': r.website_id.id, 'partner_id': p.id, 'announcement_id': r.id} for p in audience])
            r.write({'state': 'published', 'published_at': fields.Datetime.now()})

    @api.model
    def _cron_announcements(self):
        for r in self.sudo().search([('state', '=', 'scheduled'), ('scheduled_at', '<=', fields.Datetime.now())], limit=20):
            r._lock()
            r._publish()
