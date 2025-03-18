from odoo import fields, models


class CryptoImportExchangeWizard(models.TransientModel):
    _inherit = "crypto.import.exchange.wizard"

    kraken_api_key_id = fields.Many2one(
        "crypto.api.key", string="Kraken API Key", related="wallet_id.kraken_api_key_id", readonly=False
    )
    kraken_api_sec_id = fields.Many2one(
        "crypto.api.key", string="Kraken Private Key", related="wallet_id.kraken_api_sec_id", readonly=False
    )
