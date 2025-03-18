import json
import logging
import traceback
from datetime import datetime
from decimal import Decimal

from odoo import models

_logger = logging.getLogger(__name__)


class CryptoTransaction(models.Model):
    _inherit = "crypto.transaction"

    def process(self):
        super().process()
        transactions = self.filtered(lambda x: x.wallet_id.crypto_provider == "kraken")
        if not transactions:
            return

        currencies = {
            cur.kraken_api_code: cur for cur in self.env["res.currency"].search([("kraken_api_code", "!=", False)])
        }
        for transaction in transactions:
            try:
                tx = json.loads(transaction.raw)
                entry = tx["ledger_entry"]
                outputs = [
                    {
                        "transaction_id": transaction.id,
                        "name": tx["ledger_id"],
                        "date": datetime.fromtimestamp(float(entry["time"])),
                        "currency_id": currencies[entry["asset"]].id,
                        "value": float(entry["amount"]),
                        "value_str": entry["amount"],
                    }
                ]

                fee = -Decimal(entry["fee"])
                if fee:
                    outputs.append(
                        {
                            "transaction_id": transaction.id,
                            "name": "Fee: " + tx["ledger_id"],
                            "date": datetime.fromtimestamp(float(entry["time"])),
                            "currency_id": currencies[entry["asset"]].id,
                            "value": float(fee),
                            "value_str": str(fee),
                        }
                    )
                self.env["crypto.transaction.line"].with_context(fix_crypto_units=True).create(outputs)
                transaction.state = "ready"
            except Exception:
                error = traceback.format_exc()
                transaction.error = error
                transaction.state = "error"
                _logger.error(error)
