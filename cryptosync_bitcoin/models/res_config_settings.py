from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bitcoin_api_url = fields.Char("Bitcoin API URL", related="company_id.bitcoin_api_url", readonly=False)
    # Docs are available here:
    # - https://mempool.space/docs/api/rest
    # - https://github.com/Blockstream/esplora/blob/master/API.md

    bitcoin_hd_gap_limit = fields.Integer(
        "Bitcoin Address Gap Limit", related="company_id.bitcoin_hd_gap_limit", readonly=False
    )
