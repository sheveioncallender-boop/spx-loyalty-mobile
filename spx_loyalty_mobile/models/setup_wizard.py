"""Four-step administrator setup. Business records are created only on Apply."""
import math
from decimal import Decimal, InvalidOperation

from markupsafe import Markup
from odoo import _, api, fields, models, Command
from odoo.exceptions import AccessError, UserError

from .lifecycle import connection_origin
from .onboarding import email_value


TEMPLATE_PREFIX = 'spx_mobile.setup_template.'
STEPS = [('connect', '1. Connect'), ('benefits', '2. Benefits'),
         ('customers', '3. Customers'), ('review', '4. Review')]


def gift_amounts(value):
    """A short, deterministic list; reject NaN, overflow and ambiguous input."""
    try:
        amounts = [Decimal(part.strip()) for part in (value or '').split(',')]
    except (InvalidOperation, ValueError):
        raise UserError(_('Enter gift amounts separated by commas, for example 50, 100, 200.')) from None
    if not 1 <= len(amounts) <= 10 or any(
            not amount.is_finite() or amount <= 0 or amount > 1000000 for amount in amounts):
        raise UserError(_('Enter between 1 and 10 positive gift amounts, each no greater than 1,000,000.'))
    if len(set(amounts)) != len(amounts):
        raise UserError(_('Each gift amount should appear only once.'))
    converted = [float(amount) for amount in amounts]
    if any(amount <= 0 for amount in converted):
        raise UserError(_('Gift amounts must be greater than zero in the website currency.'))
    return converted


class AppSetupWizard(models.TransientModel):
    _name = 'spx.mobile.setup.wizard'
    _description = 'Guided customer app setup'

    website_id = fields.Many2one('website', required=True, readonly=True)
    company_id = fields.Many2one(related='website_id.company_id')
    currency_id = fields.Many2one(related='website_id.currency_id')
    step = fields.Selection(STEPS, default='connect', required=True)
    source_revision = fields.Char(readonly=True)
    applied = fields.Boolean(readonly=True)
    confirmed = fields.Boolean('I have reviewed these settings and approve applying them')
    progress = fields.Html(compute='_compute_progress', sanitize=True)
    review = fields.Html(compute='_compute_review', sanitize=True)

    origin = fields.Char('Public HTTPS address')
    brand = fields.Char('App name')
    enable_app = fields.Boolean('Enable the customer app')
    pos_config_id = fields.Many2one('pos.config', string='Restaurant POS')

    loyalty_mode = fields.Selection([
        ('template', 'Start with a template'), ('existing', 'Use my own program'),
    ], default='template', required=True, string='Loyalty')
    loyalty_program_ids = fields.Many2many('loyalty.program',
        'spx_setup_wizard_loyalty_rel', string='Loyalty programs')
    loyalty_template = fields.Selection([
        ('percent', 'Points for a percentage discount'),
        ('per_order', 'Points for a fixed discount'),
    ], default='percent', required=True, string='Reward style')
    earn_points = fields.Float('Points per currency unit spent', default=1)
    redeem_points = fields.Float('Points needed for a reward', default=100)
    reward_value = fields.Float('Discount value', default=10)

    gift_mode = fields.Selection([
        ('keep', 'Keep current / set up later'), ('template', 'Start with a template'),
        ('existing', 'Use my own program'),
    ], default='keep', required=True, string='Gift cards')
    gift_program_ids = fields.Many2many('loyalty.program',
        'spx_setup_wizard_gift_rel', string='Gift card programs')
    gift_product_ids = fields.Many2many('product.template', string='Gift card products')
    gift_values = fields.Char('Gift card amounts', default='50, 100, 200')

    birthday_mode = fields.Selection([
        ('keep', 'Keep current / set up later'), ('template', 'Start with a template'),
        ('existing', 'Use my own program'),
    ], default='keep', required=True, string='Birthday reward')
    birthday_program_id = fields.Many2one('loyalty.program', string='Birthday program')
    birthday_enabled = fields.Boolean('Enable automatic birthday credit')
    birthday_amount = fields.Monetary('Birthday credit', default=50)
    birthday_days = fields.Integer('Valid for (days)', default=21)
    birthday_audience = fields.Selection(related='website_id.spx_birthday_audience', string='Eligible customers')

    signup_enabled = fields.Boolean('Allow new members to sign up')
    signup_program_id = fields.Many2one('loyalty.program', string='New member program')
    mail_from = fields.Char('Account email sender')
    policy_version = fields.Char('Policy version', default='1')
    terms = fields.Text('Account and rewards terms')
    privacy = fields.Text('Privacy policy')
    policies_confirmed = fields.Boolean('These are the approved customer policies')

    cached_loyalty_id = fields.Many2one('loyalty.program', compute='_compute_cached')
    cached_gift_id = fields.Many2one('loyalty.program', compute='_compute_cached')
    cached_birthday_id = fields.Many2one('loyalty.program', compute='_compute_cached')

    def _admin(self):
        self.ensure_one()
        if not self.env.is_system():
            raise AccessError(_('Only an administrator can configure the customer app.'))
        self.check_access('write')
        self.website_id._mobile_setup_admin()
        if self.website_id.company_id not in self.env.companies:
            raise AccessError(_('Select this website’s company first.'))

    def _template_key(self, kind):
        return '%s%s.%s' % (TEMPLATE_PREFIX, self.website_id.id, kind)

    def _cached_program(self, kind):
        value = self.env['ir.config_parameter'].sudo().get_param(self._template_key(kind), '')
        if not value.isdecimal():
            return self.env['loyalty.program']
        return self.env['loyalty.program'].with_context(active_test=False).browse(int(value)).exists()

    @api.depends('website_id')
    def _compute_cached(self):
        for wizard in self:
            for kind in ('loyalty', 'gift', 'birthday'):
                wizard['cached_%s_id' % kind] = wizard._cached_program(kind) if wizard.website_id else False

    @api.depends('step')
    def _compute_progress(self):
        for wizard in self:
            wizard.progress = Markup('<ol class="jr-setup-progress" aria-label="Setup progress">%s</ol>') % Markup('').join(
                Markup('<li class="%s" aria-current="%s">%s</li>') % (
                    'is-current' if key == wizard.step else '',
                    'step' if key == wizard.step else 'false', label)
                for key, label in STEPS)

    @api.onchange('birthday_mode')
    def _onchange_birthday_mode(self):
        if self.birthday_mode == 'template':
            self.birthday_enabled = True

    @api.onchange('loyalty_program_ids')
    def _onchange_loyalty_programs(self):
        if self.signup_program_id not in self.loyalty_program_ids:
            self.signup_program_id = self.loyalty_program_ids if len(self.loyalty_program_ids) == 1 else False

    def _check_programs(self, programs, kind):
        w = self.website_id
        for program in programs:
            program.check_access('read')
            if (not program.active or program.program_type != kind
                    or (program.company_id and program.company_id != w.company_id)
                    or (program.website_id and program.website_id != w)
                    or program.currency_id != w.currency_id):
                raise UserError(_('“%s” must be active and match this website, company and currency. Choose a compatible program or edit it in Odoo.') % program.name)
            if kind == 'gift_card':
                rewards = program.reward_ids.filtered('active')
                if (len(rewards) != 1 or rewards.reward_type != 'discount'
                        or rewards.discount_mode != 'per_point' or rewards.discount != 1
                        or rewards.discount_applicability != 'order'):
                    raise UserError(_('“%s” must use the native gift-card reward: one currency unit per point, for the whole order.') % program.name)

    def _validate_connect(self):
        connection_origin(self.origin)
        if not (self.brand or '').strip():
            raise UserError(_('Enter the app name.'))

    def _validate_benefits(self):
        if self.loyalty_mode == 'existing':
            if not self.loyalty_program_ids:
                raise UserError(_('Choose your loyalty program or start with a template.'))
            self._check_programs(self.loyalty_program_ids, 'loyalty')
        else:
            cached = self._cached_program('loyalty')
            if cached:
                self._check_programs(cached, 'loyalty')
            elif (not all(math.isfinite(v) and v > 0 for v in (
                    self.earn_points, self.redeem_points, self.reward_value))
                    or self.loyalty_template == 'percent' and self.reward_value > 100):
                raise UserError(_('Enter positive earning and redemption values. A percentage discount cannot exceed 100.'))
        if self.gift_mode == 'existing':
            if not self.gift_program_ids:
                raise UserError(_('Choose a gift-card program or select Set up later.'))
            self._check_programs(self.gift_program_ids, 'gift_card')
            for product in self.gift_product_ids:
                if (not product.active or not product.sale_ok
                        or (product.company_id and product.company_id != self.company_id)
                        or (product.website_id and product.website_id != self.website_id)
                        or not (product.product_variant_ids & self.gift_program_ids.trigger_product_ids)):
                    raise UserError(_('Choose active gift products that belong to the selected programs and website.'))
        elif self.gift_mode == 'template':
            cached = self._cached_program('gift')
            if cached:
                self._check_programs(cached, 'gift_card')
            else:
                amounts = gift_amounts(self.gift_values)
                if self.currency_id != self.company_id.currency_id:
                    raise UserError(_('For a different website currency, choose your existing gift products and pricelist.'))
                if any(abs(self.currency_id.round(v) - v) > 0.0000001 for v in amounts):
                    raise UserError(_('Use gift amounts supported by this currency’s rounding.'))
        if self.birthday_mode != 'keep':
            program = self.birthday_program_id if self.birthday_mode == 'existing' else self._cached_program('birthday')
            if self.birthday_mode == 'existing' and not program:
                raise UserError(_('Choose a dedicated birthday program or start with a template.'))
            self._check_programs(program, 'gift_card')
            gift_programs = self.gift_program_ids if self.gift_mode == 'existing' else self._cached_program('gift') if self.gift_mode == 'template' else self.website_id.spx_gift_program_ids
            if program and (program.trigger_product_ids or program in gift_programs):
                raise UserError(_('Use a separate birthday program with no sale trigger products.'))
            if (not math.isfinite(self.birthday_amount) or self.birthday_amount <= 0
                    or not 1 <= self.birthday_days <= 366):
                raise UserError(_('Enter a positive birthday credit and 1 to 366 days of validity.'))

    def _validate_customers(self):
        if self.pos_config_id and (not self.pos_config_id.active
                or not self.pos_config_id.module_pos_restaurant
                or self.pos_config_id.company_id != self.company_id):
            raise UserError(_('Choose an active restaurant POS for this company.'))
        if self.signup_enabled:
            if not self.enable_app:
                raise UserError(_('Enable the customer app in step 1 before enabling signup.'))
            if self.loyalty_mode == 'existing' and self.signup_program_id not in self.loyalty_program_ids:
                raise UserError(_('Choose a new member program from your selected loyalty programs.'))
            email_value(self.mail_from)
            if not all((value or '').strip() for value in (self.terms, self.privacy, self.policy_version)):
                raise UserError(_('Add the approved terms, privacy policy and policy version, or leave signup off for now.'))
            if not self.policies_confirmed:
                raise UserError(_('Confirm that these are the approved customer policies.'))

    def _window(self):
        return {'type': 'ir.actions.act_window', 'name': _('Set up your app'),
                'res_model': self._name, 'res_id': self.id, 'view_mode': 'form',
                'views': [(self.env.ref('spx_loyalty_mobile.app_setup_wizard_form').id, 'form')],
                'target': 'new'}

    def action_next(self):
        self._admin()
        if self.applied:
            return self.website_id._mobile_setup_status_action()
        validators = {'connect': self._validate_connect, 'benefits': self._validate_benefits,
                      'customers': self._validate_customers}
        if self.step in validators:
            validators[self.step]()
            self.write({'step': STEPS[[key for key, label in STEPS].index(self.step) + 1][0], 'confirmed': False})
        return self._window()

    def action_back(self):
        self._admin()
        index = [key for key, label in STEPS].index(self.step)
        self.write({'step': STEPS[max(0, index - 1)][0], 'confirmed': False})
        return self._window()

    def _review_rows(self):
        rows = [(_('App'), _('%s — %s') % (self.brand or '', _('On') if self.enable_app else _('Off'))),
                (_('Address'), self.origin or '')]
        for kind, title, mode, programs in (
                ('loyalty', _('Loyalty'), self.loyalty_mode, self.loyalty_program_ids),
                ('gift', _('Gift cards'), self.gift_mode, self.gift_program_ids),
                ('birthday', _('Birthday reward'), self.birthday_mode, self.birthday_program_id)):
            cached = self._cached_program(kind) if mode == 'template' else False
            if mode == 'keep':
                if kind == 'gift':
                    detail = _('Keep current: %s') % (', '.join(self.website_id.spx_gift_program_ids.mapped('name')) or _('not configured'))
                else:
                    detail = _('Keep current birthday settings: %s') % (_('On') if self.website_id.spx_birthday_enabled else _('Off'))
            elif mode == 'existing' or cached:
                detail = _('Use %s; existing earning and reward rules stay unchanged.') % ', '.join((cached or programs).mapped('name'))
            elif kind == 'loyalty':
                unit = '%' if self.loyalty_template == 'percent' else self.currency_id.name
                detail = _('Create: %(earn)s points per %(currency)s 1 spent; %(points)s points redeem %(value)s %(unit)s off the order.') % {
                    'earn': self.earn_points, 'currency': self.currency_id.name,
                    'points': self.redeem_points, 'value': self.reward_value, 'unit': unit}
            elif kind == 'gift':
                detail = _('Create and publish gift products: %s %s. Native product taxes and checkout apply; verify them before selling.') % (self.currency_id.name, self.gift_values or '')
            else:
                detail = _('Create a separate birthday credit program.')
            if kind == 'birthday' and mode != 'keep':
                detail += ' ' + _('%(amount)s %(currency)s, valid %(days)s days. Automatic birthday credit: %(enabled)s.') % {
                    'amount': self.birthday_amount, 'currency': self.currency_id.name,
                    'days': self.birthday_days, 'enabled': _('On') if self.birthday_enabled else _('Off')}
                detail += ' ' + (_('Audience: existing customers with a birthday.')
                    if self.birthday_audience == 'customers' else _('Audience: verified app members.'))
            rows.append((title, detail))
        rows += [(_('New member signup'), _('On — verify email delivery before release') if self.signup_enabled else _('Off')),
                 (_('Ordering'), self.pos_config_id.name or _('Not configured'))]
        if any(mode == 'template' and not self._cached_program(kind) for kind, mode in (
                ('loyalty', self.loyalty_mode), ('gift', self.gift_mode), ('birthday', self.birthday_mode))):
            rows.append((_('New program availability'),
                _('This website and company; POS: %s. Native Sales and website checkout are enabled.') % (self.pos_config_id.name or _('off'))))
        return rows

    @api.depends('step', 'origin', 'brand', 'enable_app', 'loyalty_mode', 'loyalty_program_ids',
                 'loyalty_template', 'earn_points', 'redeem_points', 'reward_value', 'gift_mode',
                 'gift_values', 'gift_program_ids', 'birthday_mode', 'birthday_program_id',
                 'birthday_enabled', 'birthday_amount', 'birthday_days', 'signup_enabled', 'pos_config_id')
    def _compute_review(self):
        for wizard in self:
            wizard.review = Markup('<dl class="jr-setup-review">%s</dl>') % Markup('').join(
                Markup('<div><dt>%s</dt><dd>%s</dd></div>') % row for row in wizard._review_rows())

    def _create_template(self, kind):
        # Website row is locked by Apply. The retained key survives connector uninstall.
        existing = self._cached_program(kind)
        if existing:
            self._check_programs(existing, 'loyalty' if kind == 'loyalty' else 'gift_card')
            return existing
        names = {'loyalty': _('Loyalty rewards'), 'gift': _('Gift cards'), 'birthday': _('Birthday credit')}
        values = {
            'name': '%s — %s' % (self.brand.strip(), names[kind]),
            'program_type': 'loyalty' if kind == 'loyalty' else 'gift_card',
            'company_id': self.company_id.id, 'website_id': self.website_id.id,
            'currency_id': self.currency_id.id, 'active': True,
            'applies_on': 'both' if kind == 'loyalty' else 'future', 'trigger': 'auto',
            'portal_visible': True, 'portal_point_name': _('Points') if kind == 'loyalty' else self.currency_id.symbol,
            'sale_ok': True, 'ecommerce_ok': True, 'pos_ok': bool(self.pos_config_id),
            'pos_config_ids': [Command.set(self.pos_config_id.ids)],
            'communication_plan_ids': [Command.clear()],
            'rule_ids': [Command.clear()],
            'reward_ids': [Command.clear(), Command.create({
                'reward_type': 'discount', 'discount_applicability': 'order',
                'discount_mode': self.loyalty_template if kind == 'loyalty' else 'per_point',
                'discount': self.reward_value if kind == 'loyalty' else 1,
                'required_points': self.redeem_points if kind == 'loyalty' else 1,
            })],
        }
        if kind == 'loyalty':
            values['rule_ids'].append(Command.create({
                'reward_point_mode': 'money', 'reward_point_amount': self.earn_points,
                'minimum_qty': 0, 'minimum_amount': 0,
            }))
        elif kind == 'gift':
            products = self.env['product.product'].with_company(self.company_id).create([{
                'name': _('%(brand)s gift card — %(amount)s %(currency)s') % {
                    'brand': self.brand.strip(), 'amount': amount, 'currency': self.currency_id.name},
                'type': 'service', 'purchase_ok': False, 'sale_ok': True,
                'list_price': amount, 'company_id': self.company_id.id,
                'website_id': self.website_id.id, 'is_published': True,
                'available_in_pos': bool(self.pos_config_id),
            } for amount in gift_amounts(self.gift_values)])
            values['rule_ids'].append(Command.create({
                'reward_point_mode': 'money', 'reward_point_amount': 1,
                'reward_point_split': True, 'minimum_qty': 0,
                'product_ids': [Command.set(products.ids)],
            }))
            template = self.env.ref('loyalty.mail_template_gift_card', raise_if_not_found=False)
            if template:
                values['communication_plan_ids'].append(Command.create({
                    'trigger': 'create', 'mail_template_id': template.id}))
        program = self.env['loyalty.program'].with_company(self.company_id).create(values)
        self.env['ir.config_parameter'].sudo().set_param(self._template_key(kind), str(program.id))
        return program

    def action_apply(self):
        self._admin()
        w = self.website_id
        # Serialize retries and separate browser tabs; reject stale settings before creating records.
        self.env.cr.execute('SELECT id FROM website WHERE id = %s FOR UPDATE', (w.id,))
        w.invalidate_recordset()
        self.invalidate_recordset(['applied'])
        if self.applied:
            return w._mobile_setup_status_action()
        if self.step != 'review' or not self.confirmed:
            raise UserError(_('Review the setup and confirm your choices before applying.'))
        if self.source_revision != w.write_date.isoformat():
            raise UserError(_('These settings changed in another session. Close this guide and reopen it to load the current settings.'))
        self._validate_connect()
        self._validate_benefits()
        self._validate_customers()
        programs = self.loyalty_program_ids if self.loyalty_mode == 'existing' else self._create_template('loyalty')
        values = {
            'spx_mobile_account_origin': connection_origin(self.origin), 'spx_mobile_brand': self.brand.strip(),
            'spx_mobile_enabled': self.enable_app, 'spx_mobile_program_ids': [Command.set(programs.ids)],
            'spx_mobile_pos_config_id': self.pos_config_id.id,
            'spx_mobile_signup_enabled': self.signup_enabled,
        }
        if self.signup_enabled:
            values.update(spx_mobile_signup_program_id=(programs.id if self.loyalty_mode == 'template' else self.signup_program_id.id),
                          spx_mobile_mail_from=self.mail_from, spx_mobile_policy_version=self.policy_version.strip(),
                          spx_mobile_terms=self.terms, spx_mobile_privacy=self.privacy)
        if self.gift_mode != 'keep':
            gifts = self.gift_program_ids if self.gift_mode == 'existing' else self._create_template('gift')
            products = self.gift_product_ids if self.gift_mode == 'existing' else gifts.trigger_product_ids.product_tmpl_id
            values.update(spx_gift_program_ids=[Command.set(gifts.ids)], spx_gift_product_ids=[Command.set(products.ids)])
        if self.birthday_mode != 'keep':
            birthday = self.birthday_program_id if self.birthday_mode == 'existing' else self._create_template('birthday')
            values.update(spx_birthday_program_id=birthday.id, spx_birthday_enabled=self.birthday_enabled,
                          spx_birthday_amount=self.birthday_amount, spx_birthday_days=self.birthday_days)
            if not w.spx_birthday_message:
                values['spx_birthday_message'] = _('Happy birthday! Your birthday reward is ready in the app.')
        w.write(values)
        self.applied = True
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'title': _('Setup saved'), 'message': _('Your choices are saved. Review the remaining checks before customer release.'),
            'type': 'success', 'sticky': False, 'next': w._mobile_setup_status_action()}}
