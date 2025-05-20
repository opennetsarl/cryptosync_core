from odoo import fields, models


class CryptoGenerateStatementsWizard(models.TransientModel):
    _name = "crypto.generate.statements.wizard"
    _description = "Generate Cryptocurrency Statements or Moves Wizard"

    company_id = fields.Many2one(
        "res.company", string="Company", required=True, readonly=True, default=lambda self: self.env.company
    )
    company_partner_id = fields.Many2one(
        "res.partner", related="company_id.partner_id", string="Wallet Holder", readonly=True
    )
    journal_ids = fields.Many2many(
        "account.journal",
        string="Journals",
        domain="[('type', '=', 'bank'), ('bank_statements_source', '=', 'crypto'), ('bank_account_id.crypto_output_type', '=', 'statement')]",
    )
    wallet_ids = fields.Many2many(
        "res.partner.bank",
        string="Wallets",
        domain="[('crypto_provider_id', '!=', False), ('partner_id', '=', company_partner_id), ('crypto_output_type', '=', 'move')]",
    )
    output_type = fields.Selection(
        string="Output Type", related="wallet_ids.crypto_output_type"
    )  # don't worry, all wallets should have the same output_type because of the domain, and this wizard is always created with only one wallet
    date_from = fields.Date("From")
    date_to = fields.Date("To")
    group_by = fields.Selection([("week", "By week"), ("month", "By month"), ("year", "By year")], string="Group")
    output_journal_id = fields.Many2one("account.journal", string="Output Journal", domain=[("type", "=", "general")])

    def generate_statements(self):
        domain = [("state", "=", "ready")]
        if self.date_from:
            domain.append(("date", ">=", self.date_from))
        if self.date_to:
            domain.append(("date", "<=", self.date_to))
        if self.journal_ids:
            domain.append(("journal_id", "in", self.journal_ids.ids))
        return self.env["crypto.transaction.line"].search(domain).generate_statements(self.group_by)

    def generate_moves(self):
        domain = [("state", "=", "ready")]
        if self.wallet_ids:
            domain.append(("wallet_id", "in", self.wallet_ids.ids))
        return self.env["crypto.transaction"].search(domain).generate_moves(journal_id=self.output_journal_id)

    def action_generate(self):
        if self.output_type == "statement":
            return self.generate_statements()
        if self.output_type == "move":
            return self.generate_moves()
