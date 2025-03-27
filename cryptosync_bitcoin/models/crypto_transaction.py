import json
import logging
import traceback

from odoo import models

_logger = logging.getLogger(__name__)


class CryptoTransaction(models.Model):
    _inherit = "crypto.transaction"

    def _process(self):
        super()._process()
        transactions = self.filtered(lambda x: x.wallet_id.crypto_provider == "bitcoin")
        if not transactions:
            return

        for transaction in transactions:
            errors = []
            address = transaction.wallet_id.acc_number.lower()
            BTC = transaction.wallet_id.journal_id.currency_id

            for tx in json.loads(transaction.raw):
                try:
                    data = tx["data"]
                    outputs = []

                    if not errors:
                        self.env["crypto.transaction.line"].with_context(fix_crypto_units=True).create(outputs)

                except Exception:
                    error = traceback.format_exc()
                    _logger.error(error)
                    errors.append(error)
            if errors:
                transaction.state = "error"
                transaction.error = "\n\n".join(errors)
            else:
                transaction.state = "ready"

    def _compute_explorer_link(self):
        super()._compute_explorer_link()
        for tx in self.filtered(lambda x: x.wallet_id.crypto_provider == "bitcoin"):
            tx.explorer_link = f"{self.env.company.bitcoin_api_url}/tx/{tx.name}"
