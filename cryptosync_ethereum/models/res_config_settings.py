from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    etherscan_api_key_id = fields.Many2one(
        "crypto.api.key", string="Etherscan API Key", related="company_id.etherscan_api_key_id", readonly=False
    )
