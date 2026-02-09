from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    coingecko_api_key_id = fields.Many2one(
        "crypto.api.key", string="CoinGecko API Key", related="company_id.coingecko_api_key_id", readonly=False
    )
