from odoo import _, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    crypto_provider_id = fields.Many2one(
        "crypto.provider", string="Crypto Provider", related="bank_account_id.crypto_provider_id"
    )
    crypto_provider = fields.Char("Provider Code", related="crypto_provider_id.code")
    code = fields.Char(size=8)  # default is 5

    def __get_bank_statements_available_sources(self):
        rslt = super().__get_bank_statements_available_sources()
        rslt.append(("crypto", _("Crypto Provider")))
        return rslt
