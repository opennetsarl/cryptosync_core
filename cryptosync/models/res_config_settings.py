from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Modules Core AGPL
    module_cryptosync_coingecko = fields.Boolean()
    module_cryptosync_bitcoin = fields.Boolean()
    module_cryptosync_ethereum = fields.Boolean()
    module_cryptosync_cosmos = fields.Boolean(readonly=True)
    module_cryptosync_kraken = fields.Boolean()
    module_cryptosync_okx = fields.Boolean(readonly=True)

    # Modules Premium OPL
    module_cryptosync_binance = fields.Boolean()
    module_cryptosync_swissquote = fields.Boolean()

    # Modules On-demand OPL
    module_cryptosync_alephium = fields.Boolean(readonly=True)
    module_cryptosync_bybit = fields.Boolean(readonly=True)
    module_cryptosync_coinbase = fields.Boolean(readonly=True)
    module_cryptosync_gateio = fields.Boolean(readonly=True)
    module_cryptosync_icp = fields.Boolean(readonly=True)
    module_cryptosync_kucoin = fields.Boolean(readonly=True)
    module_cryptosync_mexc = fields.Boolean(readonly=True)
    module_cryptosync_solana = fields.Boolean(readonly=True)
