from uuid import uuid4
from markupsafe import Markup, escape
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class Website(models.Model):
    _inherit = 'website'

    @api.constrains('spx_mobile_pos_config_id', 'company_id')
    def _check_mobile_pos(self):
        for website in self:
            config = website.spx_mobile_pos_config_id
            if config and (config.company_id != website.company_id or not config.module_pos_restaurant):
                raise ValidationError(_('Choose a restaurant Point of Sale belonging to this website’s company.'))

    @api.constrains('spx_mobile_program_ids', 'company_id')
    def _check_mobile_programs(self):
        for website in self:
            for program in website.spx_mobile_program_ids:
                if program.program_type != 'loyalty' or (
                    program.company_id and program.company_id != website.company_id
                ) or (program.website_id and program.website_id != website):
                    raise ValidationError(_('Choose loyalty programs for this website and company.'))


class MobileMessage(models.Model):
    _inherit = 'spx.mobile.message'

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
