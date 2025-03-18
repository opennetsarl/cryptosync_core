from ast import literal_eval

from odoo import _, fields, models
from odoo.exceptions import UserError


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    crypto_provider_id = fields.Many2one(
        "crypto.provider", string="Crypto Provider", domain=[("provide_tx", "=", True)]
    )
    crypto_provider = fields.Char("Provider Code", related="crypto_provider_id.code")
    crypto_provider_image = fields.Image("Provider Icon", related="crypto_provider_id.image")
    crypto_output_type = fields.Selection("Output Type", related="crypto_provider_id.output_type")
    crypto_transaction_line_count = fields.Integer(
        "Crypto Transaction Lines Count", compute="_compute_crypto_transaction_line_count"
    )
    explorer_link = fields.Char("Wallet Explorer Link", compute="_compute_explorer_link")

    def _compute_crypto_transaction_line_count(self):
        for wallet in self:
            wallet.crypto_transaction_line_count = self.env["crypto.transaction.line"].search_count(
                [("wallet_id", "=", wallet.id), ("state", "=", "ready")]
            )

    def action_open_crypto_import_exchange_wizard(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("cryptosync.action_crypto_import_exchange_wizard")
        action["context"] = literal_eval(action["context"])
        if "crypto_provider_id" in self.env.context:
            action["context"]["default_provider_id"] = self.env.context["crypto_provider_id"]
        return action

    def action_open_crypto_update_exchange_wizard(self):
        self.ensure_one()
        action = self.action_open_crypto_import_exchange_wizard()
        action["name"] = _("Update the Account")
        # context already eval by action_open_crypto_import_exchange_wizard()
        action["context"]["default_wallet_id"] = self.id
        action["context"]["default_currency_ids"] = self.journal_id.currency_id.ids
        return action

    def action_open_crypto_transactions(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("cryptosync.action_crypto_transaction")
        action["domain"] = [("wallet_id", "in", self.ids)]
        return action

    def action_open_crypto_import_transactions_wizard(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("cryptosync.action_crypto_import_transactions_wizard")
        action["context"] = literal_eval(action["context"])
        action["context"]["default_wallet_ids"] = self.ids
        action["context"]["default_wallet_id"] = self.id
        if self.crypto_provider_id.csv_only:
            action["context"]["default_csv_only"] = True
            action["context"]["default_use_csv"] = True
        return action

    def action_open_crypto_generate_statements_wizard(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("cryptosync.action_crypto_generate_statements_wizard")
        action["context"] = literal_eval(action["context"])
        action["context"]["default_journal_ids"] = self.journal_id.ids
        action["context"]["default_wallet_ids"] = self.ids
        return action

    def get_transactions_from_api(self):
        return self.env["crypto.transaction"]

    def get_transactions_from_csv(self, csv_file):
        raise UserError(_("CSV import not implemented yet! Sorry, please contact us."))

    def _compute_explorer_link(self):
        self.filtered(lambda x: not x.explorer_link).explorer_link = False

    def open_on_explorer(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.explorer_link,
            "target": "new",
        }
