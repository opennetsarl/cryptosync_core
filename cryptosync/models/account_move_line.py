from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    crypto_transaction_id = fields.Many2one("crypto.transaction.line", string="Crypto Transaction", readonly=True)
    amount_currency_str = fields.Char("Amount in Currency (raw)")
    crypto_rate = fields.Char("Used Rate")

    def unlink(self):
        self.crypto_transaction_id.state = "ready"
        return super().unlink()
