from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    etherscan_api_key_id = fields.Many2one("crypto.api.key", string="Etherscan API Key")
