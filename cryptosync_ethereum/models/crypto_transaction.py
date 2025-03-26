import json
import logging
import traceback
from datetime import datetime
from decimal import Decimal

from odoo import _, models

_logger = logging.getLogger(__name__)


class CryptoTransaction(models.Model):
    _inherit = "crypto.transaction"

    def _process(self):
        super()._process()
        transactions = self.filtered(lambda x: x.wallet_id.crypto_provider == "ethereum")
        if not transactions:
            return

        currencies = {
            cur.ethereum_smart_contract: cur
            for cur in self.env["res.currency"].search([("ethereum_smart_contract", "!=", False)])
        }
        if "ETH" not in currencies:
            transactions.state = "error"
            transactions.error = _(
                'ETH currency not found. Please, create the ETH currency and set the field "Ethereum Smart Contract" to "ETH".'
            )
            return
        ETH = currencies["ETH"]

        for transaction in transactions:
            errors = []
            address = transaction.wallet_id.acc_number.lower()

            for tx in json.loads(transaction.raw):
                try:
                    data = tx["data"]
                    provider_source = tx["source"]
                    outputs = []

                    if provider_source == "txlistinternal":
                        if data["type"] == "call":
                            pass  # normal case
                        elif data["type"] == "create":
                            continue  # ignore
                        else:
                            errors.append(_("Unknown internal transaction type! Please contact us."))

                    multiplier = -1 if address == data["from"] else 1
                    exp = int(data.get("tokenDecimal", 18))
                    value = multiplier * Decimal(data["value"]) / 10**exp
                    if value:
                        output = {
                            "transaction_id": transaction.id,
                            "name": data["hash"],
                            "date": datetime.fromtimestamp(int(data["timeStamp"])),
                            "address": data["to"] if multiplier == -1 else data["from"],
                            "value": float(value),
                            "value_str": str(value),
                        }
                        if provider_source in ("txlist", "txlistinternal"):
                            output["currency_id"] = ETH.id
                        elif provider_source == "tokentx":
                            if data["contractAddress"] not in currencies:
                                errors.append(
                                    _(
                                        "No currency found with smart contract: {contractAddress}\n"
                                        "Additional infos:\n"
                                        "- Token name: {tokenName}\n"
                                        "- Token symbol: {tokenSymbol}\n"
                                        "If you don't know this token, you should add its contract address on the blacklist.\n"
                                        'Otherwise, you have to create the currency and set the field "Ethereum Smart Contract" to "{contractAddress}".'
                                    ).format(**data)
                                )
                                continue
                            output["currency_id"] = currencies[data["contractAddress"]].id
                        outputs.append(output)

                    if provider_source == "txlist" and multiplier == -1:
                        fee = -Decimal(data.get("gasPrice", 0)) * Decimal(data.get("gasUsed", 0)) / 10**18
                        if fee:
                            outputs.append(
                                {
                                    "transaction_id": transaction.id,
                                    "name": "Fee: " + data["hash"],
                                    "date": datetime.fromtimestamp(int(data["timeStamp"])),
                                    "currency_id": ETH.id,
                                    "value": float(fee),
                                    "value_str": str(fee),
                                }
                            )

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
        for tx in self.filtered(lambda x: x.wallet_id.crypto_provider == "ethereum"):
            tx.explorer_link = "https://etherscan.io/tx/" + tx.name
            tx.explorer_link = "https://etherscan.io/tx/" + tx.name
            tx.explorer_link = "https://etherscan.io/tx/" + tx.name
