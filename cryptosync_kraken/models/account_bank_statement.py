import base64
import json
from decimal import Decimal

from odoo import models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    def recompute_balance(self):
        super().recompute_balance()

        for statement in self:
            if statement.journal_id.crypto_provider != "kraken":
                continue

            min_ts = float("inf")
            max_ts = 0
            for tx in statement.line_ids.crypto_transaction_id.transaction_id:
                data = json.loads(base64.b64decode(tx.raw).decode())["ledger_entry"]
                ts = float(data.get("time", 0))
                if ts < min_ts:
                    min_ts = ts
                    balance_start = (
                        Decimal(data.get("balance", 0)) - Decimal(data.get("amount", 0)) + Decimal(data.get("fee", 0))
                    )
                if ts > max_ts:
                    max_ts = ts
                    balance_end_real = float(data.get("balance", 0))

            statement.write({"balance_start": float(balance_start), "balance_end_real": balance_end_real})
            statement.write({"balance_start": float(balance_start), "balance_end_real": balance_end_real})
