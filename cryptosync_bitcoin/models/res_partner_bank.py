import json
import logging
import time
import urllib.parse

import requests
from btclib.bip32 import bip32, slip132
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    bt_address_format = fields.Selection(
        [
            ("P2PK", "Public Key (obsolete)"),  # Pay-to-Public-Key
            ("P2PKH", "PubKey Hash"),  # Pay-to-Public-Key-Hash
            ("P2SH", "Script Hash"),  # Pay-to-Script-Hash
            ("P2WPKH", "PubKey Hash (SegWit)"),  # Pay-to-Witness-Public-Key-Hash
            ("P2WSH", "Script Hash (SegWit)"),  # Pay-to-Witness-Script-Hash
            ("P2TR", "Taproot"),  # Pay-to-Taproot
            ("xpub", "xPubKey"),  # -> P2PKH
            ("ypub", "yPubKey"),  # -> P2SH-P2WPKH
            ("zpub", "zPubKey"),  # -> P2WPKH
            ("vpub", "vPubKey"),  # -> P2TR
        ],
        string="Bitcoin Address Format",
        compute="_compute_bt_address_format",
        store=True,
    )
    bt_child_ids = fields.One2many("crypto.btc.address", "hd_wallet_id", string="Child Addresses")
    bt_derivation_path = fields.Char("Derivation Path")

    @api.depends("acc_number", "crypto_provider")
    def _compute_bt_address_format(self):
        self.bt_address_format = False
        for address in self.filtered(lambda x: x.crypto_provider == "bitcoin" and x.acc_number):
            address.bt_address_format = self.env["crypto.btc.address"]._get_address_type(address.acc_number)

    def action_generate_bitcoin_addresses(self):
        self._ensure_derivation_path()
        GAP_LIMIT = self.env.company.bitcoin_hd_gap_limit or 20
        created_addresses = self.env["crypto.btc.address"]

        for wallet in self.filtered(
            lambda x: x.crypto_provider == "bitcoin" and x.bt_address_format in ("xpub", "ypub", "zpub", "vpub")
        ):
            wallet.bt_child_ids._compute_is_empty()  # Force recompute
            for ttype in (0, 1):  # receiving / change
                i = 0
                empty_count = 0
                while empty_count < GAP_LIMIT:
                    der_path = wallet.bt_derivation_path.format(ttype, i)  # "m/44'/0'/0'/{}/{}"

                    new_key = bip32.derive(wallet.acc_number, der_path)
                    new_address = slip132.address_from_xpub(new_key)

                    address = self.env["crypto.btc.address"].search(
                        [("name", "=", new_address), ("hd_wallet_id", "=", wallet.id)], limit=1
                    )
                    if not address:
                        address = self.env["crypto.btc.address"].create(
                            {
                                "name": new_address,
                                "hd_wallet_id": wallet.id,
                                "derivation_path": der_path,
                            }
                        )
                        created_addresses |= address
                    if address.is_empty:
                        empty_count += 1
                    else:
                        empty_count = 0
                    i += 1
        return created_addresses

    def action_open_child_bitcoin_addresses(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Child Address of ") + self.acc_number,
            "res_model": "crypto.btc.address",
            "domain": [("hd_wallet_id", "=", self.id)],
            "context": {"active_test": False},
            "view_mode": "list",
        }

    def get_transactions_from_api(self):
        all_transactions = super().get_transactions_from_api()
        btc_wallets = self.filtered(lambda x: x.crypto_provider == "bitcoin")

        fetched_addresses = set()
        hd_wallets = btc_wallets.filtered(lambda x: x.bt_address_format in ("xpub", "ypub", "zpub", "vpub"))

        timeout = 1

        while 1:
            transactions_data = dict()
            for btc_wallet in btc_wallets:
                if btc_wallet in hd_wallets:
                    addresses = btc_wallet.bt_child_ids.mapped("name")
                else:
                    addresses = [btc_wallet.acc_number]
                for address in addresses:
                    if address in fetched_addresses:
                        continue
                    url = f"{self.env.company.bitcoin_api_url}/api/address/{address}/txs"
                    _logger.info("GET " + url)
                    r = requests.get(url)

                    while r.status_code == 429:  # Too Many Requests
                        timeout *= 2
                        _logger.error(f"Error 429 Too Many Requests: Retrying in {timeout}s...")
                        time.sleep(timeout)
                        r = requests.get(url)

                    for tx in r.json():
                        tx_hash = tx["txid"]

                        if existing_tx := self.env["crypto.transaction"].search(
                            [("name", "=", tx_hash), ("wallet_id", "=", btc_wallet.id)], limit=1
                        ):
                            if address not in existing_tx.btc_addresses:
                                existing_tx.btc_addresses += "," + address
                            continue  # Transaction already exists

                        elif tx_hash in transactions_data:
                            if tx_hash not in transactions_data[tx_hash]["btc_addresses"]:
                                transactions_data[tx_hash]["btc_addresses"] += "," + address
                            continue  # Transaction don't exist but will be created in this batch

                        transactions_data[tx_hash] = {
                            "name": tx_hash,
                            "wallet_id": btc_wallet.id,
                            "raw": json.dumps(tx),
                            "state": "draft",
                            "btc_addresses": address,
                        }
                    fetched_addresses.add(address)
            all_transactions |= self.env["crypto.transaction"].create(transactions_data.values())
            if not hd_wallets.action_generate_bitcoin_addresses():
                _logger.info(f"Fetched BTC addresses: {fetched_addresses}")
                break
        return all_transactions

    def _compute_explorer_link(self):
        super()._compute_explorer_link()
        for wallet in self.filtered(
            lambda x: x.crypto_provider == "bitcoin" and x.bt_address_format not in ("xpub", "ypub", "zpub", "vpub")
        ):
            wallet.explorer_link = f"{self.env.company.bitcoin_api_url}/address/{wallet.acc_number}"

    def _ensure_derivation_path(self):
        for wallet in self.filtered(
            lambda x: x.crypto_provider == "bitcoin" and x.bt_address_format in ("xpub", "ypub", "zpub", "vpub")
        ):
            if not wallet.bt_derivation_path:
                raise UserError(
                    _(
                        "To use a xPubKey, you need to specify its derivation path "
                        "(something like m/{}/{} or m/44'/0'/0'/{}/{})"
                    )
                )

    #
    # Native QR-related methods inherit
    # VVV

    def _btc_get_qr_vals(self, amount, currency, debtor_partner, free_communication, structured_communication):
        # cf. BIP21 (https://github.com/bitcoin/bips/blob/master/bip-0021.mediawiki)
        # bitcoin:<address>[?amount=<amount>][?label=<label>][?message=<message>]
        address = False
        move = False
        if self.env.context.get("active_model") == "account.move" and self.env.context.get("active_id"):
            # Not the best practice to get the move, but hey
            move = self.env["account.move"].browse(self.env.context["active_id"])
            address = move.btc_payment_address
        if not address:
            if self.bt_address_format in ("xpub", "ypub", "zpub", "vpub"):
                self._ensure_derivation_path()
                der_path = self.bt_derivation_path.format(0, "%")
                while not address:
                    candidates = self.env["crypto.btc.address"].search(
                        [("hd_wallet_id", "=", self.id), ("derivation_path", "=like", der_path)]
                    )
                    for i in range(len(candidates)):
                        der_path = self.bt_derivation_path.format(0, i)
                        choice = candidates.filtered(lambda x: x.derivation_path == der_path and x.is_empty)
                        if choice:
                            address = choice[0].name
                            break
                    else:
                        # Loop did NOT break
                        self.action_generate_bitcoin_addresses()
            else:
                address = self.acc_number
        if move:
            move.btc_payment_address = address
        params = dict()
        if currency.name == "BTC":
            # Specify amount only if it's in BTC
            # otherwise rate may vary and it's up to the customer to set the correct equivalent
            params["amount"] = amount
        params["label"] = (self.acc_holder_name or self.partner_id.name,)
        if msg := free_communication or structured_communication:
            params["message"] = msg
        uri = f"bitcoin:{address}?{urllib.parse.urlencode(params)}"
        return uri

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == "btc":
            return self._btc_get_qr_vals(amount, currency, debtor_partner, free_communication, structured_communication)
        return super()._get_qr_vals(
            qr_method, amount, currency, debtor_partner, free_communication, structured_communication
        )

    def _get_qr_code_generation_params(
        self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication
    ):
        if qr_method == "btc":
            return {
                "barcode_type": "QR",
                "width": 128,
                "height": 128,
                "value": self._get_qr_vals(
                    qr_method, amount, currency, debtor_partner, free_communication, structured_communication
                ),
            }
        return super()._get_qr_code_generation_params(
            qr_method, amount, currency, debtor_partner, free_communication, structured_communication
        )

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        if qr_method == "btc":
            if self.crypto_provider != "bitcoin":
                return _("The account is not a Bitcoin wallet.")
            if not self.bt_address_format:
                return _("The Bitcoin address format is not recognized.")
            return None
        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _check_for_qr_code_errors(
        self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication
    ):
        if qr_method == "btc":
            return None
        return super()._check_for_qr_code_errors(
            qr_method, amount, currency, debtor_partner, free_communication, structured_communication
        )

    @api.model
    def _get_available_qr_methods(self):
        rslt = super()._get_available_qr_methods()
        rslt.append(("btc", _("Bitcoin QR"), 100))
        return rslt
