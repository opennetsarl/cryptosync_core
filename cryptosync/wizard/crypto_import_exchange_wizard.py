from odoo import _, fields, models


class CryptoImportExchangeWizard(models.TransientModel):
    _name = "crypto.import.exchange.wizard"
    _description = "Import Cryptocurrency Exchange Wizard"

    provider_id = fields.Many2one("crypto.provider", string="Provider", domain=[("provide_tx", "=", True)])
    provider = fields.Char("Provider Code", related="provider_id.code")
    company_id = fields.Many2one(
        "res.company", string="Company", required=True, readonly=True, default=lambda self: self.env.company
    )
    company_partner_id = fields.Many2one(
        "res.partner", related="company_id.partner_id", string="Wallet Holder", readonly=True
    )
    wallet_id = fields.Many2one(
        "res.partner.bank",
        string="Wallet",
        required=True,
        check_company=True,
        domain="[('crypto_provider_id', '=', provider_id), ('partner_id', '=', company_partner_id)]",
    )
    currency_ids = fields.Many2many("res.currency", string="Currencies", required=True)
    no_api = fields.Boolean("Don't use API connection")

    def _prepare_journal_values(self, existing_journals=False):
        data = []
        all_codes = self.env["account.journal"].search([("code", "!=", False)]).mapped("code")
        for currency in self.currency_ids:
            if existing_journals and currency in existing_journals.currency_id:
                continue

            i = 0
            while True:
                code = f"{self.provider_id.prefix or ''}{i or ''}{currency.name}"[:8]
                if code not in all_codes:
                    break
                i += 1

            data.append(
                {
                    "company_id": self.company_id.id,
                    "name": f"{self.provider_id.name} {currency.name}",
                    "type": "bank",
                    "currency_id": currency.id,
                    "bank_statements_source": "crypto",
                    "bank_account_id": self.wallet_id.id,
                    "code": code,
                }
            )
        return data

    def action_create(self):
        journals = self.env["account.journal"].search([("bank_account_id", "=", self.wallet_id.id)])
        data = self._prepare_journal_values(existing_journals=journals)
        journals |= self.env["account.journal"].create(data)
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
            "domain": [("id", "in", journals.ids)],
        }
