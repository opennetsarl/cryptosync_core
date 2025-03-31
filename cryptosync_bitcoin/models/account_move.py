from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    btc_payment_address = fields.Char("Bitcoin Payment Address", copy=False, readonly=True)
