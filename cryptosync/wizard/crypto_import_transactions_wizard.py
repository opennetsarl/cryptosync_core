import base64
import csv
import io
import json

from odoo import fields, models


class CryptoImportTransactionsWizard(models.TransientModel):
    _name = "crypto.import.transactions.wizard"
    _description = "Import Cryptocurrency Transactions Wizard"

    company_id = fields.Many2one(
        "res.company", string="Company", required=True, readonly=True, default=lambda self: self.env.company
    )
    company_partner_id = fields.Many2one(
        "res.partner", related="company_id.partner_id", string="Wallet Holder", readonly=True
    )
    wallet_ids = fields.Many2many(
        "res.partner.bank",
        string="Wallets",
        domain="[('crypto_provider_id', '!=', False), ('partner_id', '=', company_partner_id), ('crypto_provider_id.csv_only', '=', False)]",
    )
    wallet_id = fields.Many2one(
        "res.partner.bank",
        string="Wallet",
        domain="[('crypto_provider_id', '!=', False), ('partner_id', '=', company_partner_id)]",
    )
    use_csv = fields.Boolean("Import from a CSV file")
    csv_file = fields.Binary("CSV File")
    csv_filename = fields.Char("CSV Filename")
    csv_only = fields.Boolean("CSV Only", readonly=True)

    def get_transactions_from_api(self):
        return self.wallet_ids.get_transactions_from_api().get_action_return()

    def get_transactions_from_csv(self):
        csv_reader = csv.DictReader(io.StringIO(base64.b64decode(self.csv_file).decode("utf-8-sig")))
        # "utf-8-sig" allows to remove the character \ufeff at the beginning of some CSV files.
        # c.f. https://stackoverflow.com/questions/17912307/u-ufeff-in-python-string

        data = []
        i = 0
        for row in csv_reader:
            i += 1
            data.append(
                {
                    "name": self.csv_filename + ":" + str(i),
                    "wallet_id": self.wallet_id.id,
                    "from_csv": True,
                    "raw": json.dumps(row),
                    "state": "draft",
                }
            )
        transactions = self.env["crypto.transaction"].create(data)
        return transactions.get_action_return()
