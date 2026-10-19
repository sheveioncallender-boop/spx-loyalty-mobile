"""Validate the administrator-selected native takeaway preset at use time too."""
from odoo import _, api, models
from odoo.exceptions import ValidationError


class Website(models.Model):
    _inherit = 'website'

    def _spx_takeaway_preset(self):
        self.ensure_one()
        config = self.spx_mobile_pos_config_id
        preset = self.spx_mobile_takeaway_preset_id.exists()
        if (not config or not config.active or not config.use_presets or not preset
                or preset not in config.available_preset_ids or preset == config.default_preset_id
                or preset.is_return or preset.identification == 'address' or preset.use_timing
                or (preset.pricelist_id.company_id and preset.pricelist_id.company_id != self.company_id)
                or (preset.fiscal_position_id.company_id and preset.fiscal_position_id.company_id != self.company_id)):
            return self.env['pos.preset']
        return preset

    @api.constrains('spx_mobile_takeaway_preset_id', 'spx_mobile_pos_config_id', 'company_id')
    def _check_mobile_takeaway(self):
        for website in self:
            if website.spx_mobile_takeaway_preset_id and not website._spx_takeaway_preset():
                raise ValidationError(_(
                    'Choose a non-return, non-delivery, unscheduled Takeaway preset available '
                    'in this restaurant POS. Enable presets and keep a different default for Dine-in.'))
