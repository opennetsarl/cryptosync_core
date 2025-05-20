from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    bitcoin_api_url = fields.Char("Bitcoin API URL", default="https://mempool.space")
    bitcoin_hd_gap_limit = fields.Integer("Bitcoin Address Gap Limit", default=20)
