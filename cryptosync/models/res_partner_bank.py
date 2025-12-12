from ast import literal_eval

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    crypto_provider_id = fields.Many2one(
        "crypto.provider", string="Crypto Provider", domain=[("provide_tx", "=", True)]
    )
    crypto_provider = fields.Char("Provider Code", related="crypto_provider_id.code")
    crypto_provider_image = fields.Image("Provider Icon", related="crypto_provider_id.image")
    crypto_currency_ids = fields.Many2many("res.currency", string="Currencies")
    crypto_no_api = fields.Boolean("Don't use API connection")
    crypto_output_type = fields.Selection(string="Output Type", related="crypto_provider_id.output_type")
    crypto_default_move_journal_id = fields.Many2one(
        "account.journal",
        string="Default Entry Journal",
        domain=[("type", "=", "general")],
        help="The journal where entries will be created",
    )
    crypto_transaction_count = fields.Integer("Crypto Transactions Count", compute="_compute_crypto_transaction_count")
    crypto_transaction_line_count = fields.Integer(
        "Crypto Transaction Lines Count", compute="_compute_crypto_transaction_count"
    )
    explorer_link = fields.Char("Wallet Explorer Link", compute="_compute_explorer_link")

    def _compute_crypto_transaction_count(self):
        for wallet in self:
            wallet.crypto_transaction_count = self.env["crypto.transaction"].search_count(
                [("wallet_id", "=", wallet.id), ("state", "in", ("draft", "error"))]
            )
            wallet.crypto_transaction_line_count = self.env["crypto.transaction.line"].search_count(
                [("wallet_id", "=", wallet.id), ("state", "=", "ready")]
            )

    def action_open_crypto_transactions(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("cryptosync.action_crypto_transaction")
        action["domain"] = [("wallet_id", "in", self.ids)]
        return action

    def action_open_crypto_transaction_lines(self):
        action = self.env["ir.actions.act_window"]._for_xml_id("cryptosync.action_crypto_transaction_line")
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
        action["context"]["default_output_journal_id"] = self.crypto_default_move_journal_id.id
        return action

    def _prepare_crypto_journal_values(self):
        self.ensure_one()
        data = []
        all_codes = self.env["account.journal"].search([("code", "!=", False)]).mapped("code")
        for currency in self.crypto_currency_ids:
            if currency in self.journal_id.currency_id:
                continue

            i = 0
            while True:
                code = f"{self.crypto_provider_id.prefix or ''}{i or ''}{currency.name}"[:8]
                if code not in all_codes:
                    break
                i += 1

            data.append(
                {
                    "company_id": self.company_id.id,
                    "name": f"{self.crypto_provider_id.name} {currency.name}",
                    "type": "bank",
                    "currency_id": currency.id,
                    "bank_statements_source": "crypto",
                    "bank_account_id": self.id,
                    "code": code,
                }
            )
        return data

    def create_crypto_journals(self):
        wallets = self.filtered(lambda x: x.crypto_provider_id and x.crypto_currency_ids and x.active)
        if not wallets:
            return
        all_journals = self.env["account.journal"]
        for wallet in wallets:
            data = wallet._prepare_crypto_journal_values()
            all_journals |= self.env["account.journal"].create(data)
        self.env["crypto.transaction.line"].search(
            [("journal_id", "=", False), ("state", "=", "ready")]
        )._compute_journal_id()
        return {
            "type": "ir.actions.act_window",
            "name": _("Check new Journals"),
            "res_model": "account.journal",
            "views": [
                [self.env.ref("cryptosync.view_account_journal_tree_crypto").id, "list"],
                [False, "form"],
            ],
            "target": "current",
            "domain": [("id", "in", all_journals.ids)],
        }

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.create_crypto_journals()
        return res

    def write(self, vals):
        res = super().write(vals)
        if "crypto_currency_ids" in vals:
            self.create_crypto_journals()
        return res

    def get_transactions_from_api(self):
        return self.env["crypto.transaction"]

    def get_transactions_from_csv(self, csv_file):
        raise UserError(_("CSV import not implemented yet! Sorry, please contact us."))

    @api.model
    def _cron_crypto_sync(self):
        wallets = self.env.company.bank_ids.filtered_domain(
            [("crypto_provider", "!=", False), ("crypto_no_api", "!=", True)]
        )
        # TODO: add something like last_sync to allow hourly sync
        wallets.get_transactions_from_api()

    def _compute_explorer_link(self):
        self.filtered(lambda x: not x.explorer_link).explorer_link = False

    def open_on_explorer(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.explorer_link,
            "target": "new",
        }
