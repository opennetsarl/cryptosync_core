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

    # def _fill_bank_cash_dashboard_data(self, dashboard_data):
    #     super()._fill_bank_cash_dashboard_data(dashboard_data)
    #     for journal_id in dashboard_data:
    #         dashboard_data[journal_id].update(
    #             {
    #                 "crypto_transaction_line_count": self.env["crypto.transaction.line"].search_count(
    #                     [("journal_id", "=", journal_id), ("state", "=", "ready")]
    #                 )
    #             }
    #         )

    # def action_open_crypto_generate_statements_wizard(self):
    #     self.ensure_one()
    #     action = self.env["ir.actions.act_window"]._for_xml_id("cryptosync.action_crypto_generate_statements_wizard")
    #     output_type = self.bank_account_id[0].output_type
    #     action["context"] = {
    #         "default_journal_ids": self.ids,
    #         "default_wallet_ids": self.bank_account_id.filtered(lambda x: x.output_type == output_type).ids,
    #         "default_output_type": output_type,
    #     }
    #     return action
