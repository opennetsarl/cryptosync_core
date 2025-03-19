import base64
import json
import logging

from odoo import fields, models
from odoo.addons.cryptosync_kraken.utils.kraken import kraken_request

_logger = logging.getLogger(__name__)


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    kraken_api_key_id = fields.Many2one("crypto.api.key", string="Kraken API Key")
    kraken_api_sec_id = fields.Many2one("crypto.api.key", string="Kraken Private Key")

    kraken_ledger_start = fields.Char("Kraken Ledger Start", readonly=True)
    kraken_ledger_end = fields.Char("Kraken Ledger End", readonly=True)
    kraken_ledger_ofs = fields.Integer("Kraken Ledger Offset", readonly=True)

    def get_transactions_from_api(self):
        all_transactions = super().get_transactions_from_api()
        kraken_accounts = self.filtered(lambda x: x.crypto_provider == "kraken")

        if kraken_accounts:
            transactions_data = []

            for kraken_account in kraken_accounts:
                params = {"ofs": kraken_account.kraken_ledger_ofs}
                if kraken_account.kraken_ledger_start:
                    params["start"] = kraken_account.kraken_ledger_start
                if kraken_account.kraken_ledger_end:
                    params["end"] = kraken_account.kraken_ledger_end

                kraken_data = kraken_request(
                    "/0/private/Ledgers",
                    params,
                    kraken_account.kraken_api_key_id.sudo().name,
                    kraken_account.kraken_api_sec_id.sudo().name,
                ).json()
                ledger = list(kraken_data["result"]["ledger"].items())

                if not ledger:
                    continue

                for ledger_id, ledger_entry in ledger:
                    if self.env["crypto.transaction"].search(
                        [("name", "=", ledger_id), ("wallet_id", "=", kraken_account.id)], limit=1
                    ):
                        _logger.info("Kraken transaction {ledger_id} already exists and was skipped.")
                        continue  # Already exists
                    transactions_data.append(
                        {
                            "name": ledger_id,
                            "wallet_id": kraken_account.id,
                            "raw": base64.b64encode(
                                json.dumps(
                                    {
                                        "ledger_id": ledger_id,
                                        "ledger_entry": ledger_entry,
                                        "provider_source": "ledger",
                                    }
                                ).encode()
                            ),
                            "state": "draft",
                        }
                    )

                if kraken_account.kraken_ledger_ofs == 0:
                    kraken_account.kraken_ledger_end = ledger[0][0]

                kraken_account.kraken_ledger_ofs += len(ledger)
                if kraken_account.kraken_ledger_ofs >= kraken_data["result"]["count"]:
                    kraken_account.kraken_ledger_start = kraken_account.kraken_ledger_end
                    kraken_account.kraken_ledger_end = False
                    kraken_account.kraken_ledger_ofs = 0

            all_transactions |= self.env["crypto.transaction"].create(transactions_data)
        return all_transactions

    def kraken_reset(self):
        self.kraken_ledger_start = False
        self.kraken_ledger_end = False
        self.kraken_ledger_ofs = 0
