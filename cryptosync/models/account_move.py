from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    crypto_transaction_id = fields.Many2one("crypto.transaction", string="Crypto Transaction", readonly=True)
