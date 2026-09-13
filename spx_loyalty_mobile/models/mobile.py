from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class Website(models.Model):
    _inherit = 'website'

    spx_mobile_enabled = fields.Boolean(string='Enable customer app', groups='base.group_system')
    spx_mobile_brand = fields.Char(string='App brand', default="Jenny’s on the Boulevard")
    spx_mobile_program_ids = fields.Many2many(
        'loyalty.program', 'spx_mobile_website_program_rel', 'website_id', 'program_id',
        string='Visible loyalty programs', groups='base.group_system',
        domain="[('program_type', '=', 'loyalty')]",
    )

    @api.constrains('spx_mobile_program_ids', 'company_id')
    def _check_mobile_programs(self):
        for website in self:
            for program in website.spx_mobile_program_ids:
                if program.program_type != 'loyalty' or (
                    program.company_id and program.company_id != website.company_id
                ) or (program.website_id and program.website_id != website):
                    raise ValidationError(_('Choose loyalty programs for this website and company.'))


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

    def action_email(self):
        """Queue through Odoo mail; explicit opt-in for these promotional messages."""
        self.check_access('write')
        for message in self:
            if message.email_queued:
                continue
            partner = message.partner_id
            if not partner.spx_mobile_email or not partner.email:
                raise UserError(_('The customer must opt in to promotional email and have an email address.'))
            mail = self.env['mail.mail'].sudo().create({
                'subject': message.name,
                'body_html': Markup('<p>%s</p>') % escape(message.body).replace('\n', Markup('<br/>')),
                'email_from': message.company_id.partner_id.email_formatted or self.env.user.email_formatted,
                'recipient_ids': [(4, partner.id)],
                'auto_delete': False,
            })
            message.write({'mail_id': mail.id, 'email_queued': True})


class MobileOperation(models.Model):
    _name = 'spx.mobile.operation'
    _description = 'Mobile cart request deduplication'

    key = fields.Char(required=True, index=True)
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    website_id = fields.Many2one('website', required=True, ondelete='cascade')
    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    _key_unique = models.Constraint(
        'UNIQUE(partner_id, website_id, key)', 'This request has already been processed. Refresh your cart.')
