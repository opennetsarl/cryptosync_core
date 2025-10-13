from odoo import api, fields, models


class CryptoEthSpamcoin(models.Model):
    _name = "crypto.eth.spamcoin"
    _description = "Ethereum Blacklist"
    _order = "name"

    name = fields.Char("Address", required=True)
    note = fields.Text("Note")

    _sql_unique_name = models.Constraint("UNIQUE(name)", "Address must be unique.")

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for spamcoin in res:
            tx = self.env["crypto.transaction"].search(
                [
                    ("ethereum_spamcoin", "=", spamcoin.name),
                    ("state", "=", "error"),
                    ("wallet_id.crypto_provider", "=", "ethereum"),
                ]
            )
            tx.process()
        return res
