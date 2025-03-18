import json
import logging
import time

import requests
from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DELAY = 5


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    def get_transactions_from_api(self):
        all_transactions = super().get_transactions_from_api()
        eth_wallets = self.filtered(lambda x: x.crypto_provider == "ethereum")

        if eth_wallets:
            transactions_data = {}
            for eth_wallet in eth_wallets:
                for source in ("txlist", "txlistinternal", "tokentx"):
                    eth_data = self._etherscan_request(
                        {
                            "action": source,
                            "address": eth_wallet.acc_number.lower(),
                            "apikey": self.env.company.etherscan_api_key_id.sudo().name or "",
                        }
                    )

                    for tx in eth_data:
                        tx_hash = tx["hash"]
                        if self.env["crypto.transaction"].search_count(
                            [("name", "=", tx_hash), ("wallet_id", "=", eth_wallet.id)], limit=1
                        ):
                            # If the main transaction already exists, we have to not create the children
                            # because all children are created in the same time, so all of them already exist
                            continue
                        if tx_hash not in transactions_data:
                            transactions_data[tx_hash] = {
                                "name": tx_hash,
                                "wallet_id": eth_wallet.id,
                                "raw": [],
                                "state": "draft",
                            }
                        transactions_data[tx_hash]["raw"].append(
                            {
                                "source": source,
                                "data": tx,
                            }
                        )

            transactions_data = [{**rec, "raw": json.dumps(rec["raw"])} for rec in transactions_data.values()]
            all_transactions |= self.env["crypto.transaction"].create(transactions_data)
            # eth_wallets.crypto_sync_done = True
        return all_transactions

    @api.model
    def _etherscan_request(self, params):
        url = "https://api.etherscan.io/api?module=account&action={action}&address={address}"
        if params.get("apikey"):
            url += "&apikey={apikey}"
        else:
            # Without API key, we have a maximum rate of 5 calls/second
            last_call = float(
                self.env["ir.config_parameter"].sudo().get_param("crypto_sync_etherscan.last_call_timestamp", 0)
            )
            s = max(0, DELAY - (time.time() - last_call))
            if s:
                _logger.info("Waiting {:.1f} s".format(s))
                time.sleep(s)

        url = url.format(**params)

        _logger.info("GET " + url)
        data = requests.get(url).json()

        self.env["ir.config_parameter"].sudo().set_param("crypto_sync_etherscan.last_call_timestamp", time.time())

        if data["status"] == "0":
            if data["message"] == "No transactions found":
                return []
            raise UserError(_("An error was returned by the Etherscan API:\n{result}").format(**data))
        return data["result"]

    def _compute_explorer_link(self):
        super()._compute_explorer_link()
        for wallet in self.filtered(lambda x: x.crypto_provider == "ethereum"):
            wallet.explorer_link = "https://etherscan.io/address/" + wallet.acc_number
            wallet.explorer_link = "https://etherscan.io/address/" + wallet.acc_number
