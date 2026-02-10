from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    coingecko_api_key_id = fields.Many2one("crypto.api.key", string="CoinGecko API Key")
