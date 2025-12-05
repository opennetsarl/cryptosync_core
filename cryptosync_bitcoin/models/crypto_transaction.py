import json
import logging
import traceback
from datetime import datetime
from decimal import Decimal

from odoo import _, fields, models

_logger = logging.getLogger(__name__)


class CryptoTransaction(models.Model):
    _inherit = "crypto.transaction"

    btc_addresses = fields.Char("Involved BTC Addresses", readonly=True)

    def btc_to_sats(self, btc) -> Decimal:
        return Decimal(btc) * Decimal(100_000_000)

    def sat_to_btc(self, sats) -> Decimal:
        return Decimal(sats) / Decimal(100_000_000)

    def _process(self):
        super()._process()
        transactions = self.filtered(lambda x: x.wallet_id.crypto_provider == "bitcoin")
        if not transactions:
            return

        for transaction in transactions:
            try:
                BTC = transaction.wallet_id.journal_id.currency_id
                if not BTC:
                    transaction.error = _("No currency is set on the wallet journal. Please set it to BTC.")
                    transaction.state = "error"
                    continue

                tx = json.loads(transaction.raw)
                block_time = datetime.fromtimestamp(tx["status"]["block_time"])
                if transaction.wallet_id.bt_address_format in ("xpub", "ypub", "zpub", "vpub"):
                    my_addresses = set(transaction.wallet_id.bt_child_ids.mapped("name"))
                else:
                    my_addresses = {transaction.wallet_id.acc_number}

                in_addrs = set(vin["prevout"]["scriptpubkey_address"] for vin in tx["vin"])
                # out_addrs = set(vout["scriptpubkey_address"] for vout in tx["vout"])
                outputs = []

                if in_addrs & my_addresses:
                    # We are on the INs: we pay some suppliers
                    # (assuming that all IN addresses are our)
                    for vout in tx["vout"]:
                        address = vout["scriptpubkey_address"]
                        if address in my_addresses:
                            continue  # This is a change address
                        value = -self.sat_to_btc(vout["value"])
                        outputs.append(
                            {
                                "transaction_id": transaction.id,
                                "name": tx["txid"],
                                "date": block_time,
                                "address": address,
                                "value": float(value),
                                "value_str": str(value),
                                "currency_id": BTC.id,
                            }
                        )
                    # Add fees only if they are payed by us
                    fee = -self.sat_to_btc(tx["fee"])
                    outputs.append(
                        {
                            "transaction_id": transaction.id,
                            "name": "Fee: " + tx["txid"],
                            "date": block_time,
                            # "address": ,
                            "value": float(fee),
                            "value_str": str(fee),
                            "currency_id": BTC.id,
                        }
                    )
                else:
                    # We are on the OUTs: we are payed
                    for vout in tx["vout"]:
                        address = vout["scriptpubkey_address"]
                        if not (address == transaction.wallet_id.acc_number or address in my_addresses):
                            # but maybe not only us, so ignore unknown addresses
                            continue
                        value = self.sat_to_btc(vout["value"])
                        outputs.append(
                            {
                                "transaction_id": transaction.id,
                                "name": tx["txid"],
                                "date": block_time,
                                "address": address,
                                "value": float(value),
                                "value_str": str(value),
                                "currency_id": BTC.id,
                            }
                        )

                self.env["crypto.transaction.line"].with_context(fix_crypto_units=True).create(outputs)
                transaction.state = "ready"

            except Exception:
                error = traceback.format_exc()
                transaction.error = error
                transaction.state = "error"
                _logger.error(error)

    def _compute_explorer_link(self):
        super()._compute_explorer_link()
        for tx in self.filtered(lambda x: x.wallet_id.crypto_provider == "bitcoin"):
            tx.explorer_link = f"{self.env.company.bitcoin_api_url}/tx/{tx.name}"
