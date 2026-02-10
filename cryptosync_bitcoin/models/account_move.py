from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    btc_payment_address = fields.Char("Bitcoin Payment Address", copy=False, readonly=True)

    def generate_qr_code(self):
        return super(AccountMove, self.with_context(ons_move_id=self.id)).generate_qr_code()
