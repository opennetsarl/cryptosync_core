import json
import logging

import requests
from btclib.bip32 import bip32, slip132
from odoo import _, api, fields, models

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
    bt_hd_wallet_id = fields.Many2one("res.partner.bank", string="HD Wallet")
    bt_child_ids = fields.One2many(
        "res.partner.bank", "bt_hd_wallet_id", string="Child Addresses", context={"active_test": False}
    )
    bt_derivation_path = fields.Char("Derivation Path")
    bt_empty = fields.Boolean("Is Empty", compute="_compute_bt_empty")

    @api.depends("acc_number", "crypto_provider")
    def _compute_bt_address_format(self):
        self.bt_address_format = False
        for address in self.filtered(lambda x: x.crypto_provider == "bitcoin" and x.acc_number):
            length = len(address.acc_number)
            if address.acc_number.startswith(("04", "03", "02")):
                address.bt_address_format = "P2PK"
                continue
            if address.acc_number.startswith("1") and 26 <= length <= 34:
                address.bt_address_format = "P2PKH"
                continue
            if address.acc_number.startswith("3") and length == 34:
                address.bt_address_format = "P2SH"
                continue
            if address.acc_number.startswith("bc1q") and length == 42:
                address.bt_address_format = "P2WPKH"
                continue
            if address.acc_number.startswith("bc1q") and length == 62:
                address.bt_address_format = "P2WSH"
                continue
            if address.acc_number.startswith("bc1p") and length == 62:
                address.bt_address_format = "P2TR"
                continue
            if address.acc_number.startswith("xpub"):
                address.bt_address_format = "xpub"
                continue
            if address.acc_number.startswith("ypub"):
                address.bt_address_format = "ypub"
                continue
            if address.acc_number.startswith("zpub"):
                address.bt_address_format = "zpub"
                continue
            if address.acc_number.startswith("vpub"):
                address.bt_address_format = "vpub"
                continue

    def _compute_bt_empty(self):
        self.bt_empty = True
        for address in self.filtered(lambda x: x.crypto_provider == "bitcoin"):
            if self.env["crypto.transaction"].search_count([("wallet_id", "=", address.id)], limit=1):
                address.bt_empty = False

    def action_generate_bitcoin_addresses(self):
        GAP_LIMIT = self.env.company.bitcoin_hd_gap_limit or 20
        bank_accounts = self.env["res.partner.bank"]

        for wallet in self.filtered(
            lambda x: x.crypto_provider == "bitcoin" and x.bt_address_format in ("xpub", "ypub", "zpub", "vpub")
        ):
            for ttype in (0, 1):  # receiving / change
                i = 0
                empty_count = 0
                while empty_count < GAP_LIMIT:
                    der_path = wallet.bt_derivation_path.format(ttype, i)  # "m/44'/0'/0'/{}/{}"

                    new_key = bip32.derive(wallet.acc_number, der_path)
                    new_address = slip132.address_from_xpub(new_key)

                    bank_account = (
                        self.env["res.partner.bank"]
                        .with_context(active_test=False)
                        .search([("acc_number", "=", new_address)], limit=1)
                    )
                    if not bank_account:
                        bank_account = self.env["res.partner.bank"].create(
                            {
                                "acc_number": new_address,
                                "partner_id": wallet.partner_id.id,
                                "bank_id": wallet.bank_id.id,
                                "currency_id": wallet.currency_id.id,
                                "crypto_currency_ids": wallet.crypto_currency_ids.ids,
                                "bt_hd_wallet_id": wallet.id,
                                "bt_derivation_path": der_path,
                                "active": False,
                            }
                        )
                    bank_accounts |= bank_account
                    if bank_account.bt_empty:
                        empty_count += 1
                    else:
                        empty_count = 0
                    i += 1
        return bank_accounts

    def action_open_parent_bitcoin_addresses(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.bt_hd_wallet_id.acc_number,
            "res_model": "res.partner.bank",
            "res_id": self.bt_hd_wallet_id.id,
            "view_mode": "form",
        }

    def action_open_child_bitcoin_addresses(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Child Address of ") + self.acc_number,
            "res_model": "res.partner.bank",
            "domain": [("bt_hd_wallet_id", "=", self.id)],
            "context": {"active_test": False},
            "view_mode": "list,form",
        }

    def action_open_crypto_transactions(self):
        action = super().action_open_crypto_transactions()
        action["domain"] = [("wallet_id", "in", (self | self.bt_child_ids).ids)]
        return action

    def _compute_crypto_transaction_count(self):
        super()._compute_crypto_transaction_count()
        for wallet in self.filtered(
            lambda x: x.crypto_provider == "bitcoin" and x.bt_address_format in ("xpub", "ypub", "zpub", "vpub")
        ):
            wallet.crypto_transaction_count += self.env["crypto.transaction"].search_count(
                [("wallet_id", "in", wallet.bt_child_ids.ids), ("state", "in", ("draft", "error"))]
            )
            wallet.crypto_transaction_line_count += self.env["crypto.transaction.line"].search_count(
                [("wallet_id", "in", wallet.bt_child_ids.ids), ("state", "=", "ready")]
            )

    def get_transactions_from_api(self):
        all_transactions = super().get_transactions_from_api()
        btc_wallets = self.filtered(lambda x: x.crypto_provider == "bitcoin")

        hd_wallets = btc_wallets.filtered(lambda x: x.bt_address_format in ("xpub", "ypub", "zpub", "vpub"))
        btc_wallets -= hd_wallets
        btc_wallets |= hd_wallets.bt_child_ids

        if btc_wallets:
            transactions_data = []
            for btc_wallet in btc_wallets:
                same_wallets = btc_wallet | btc_wallet.bt_hd_wallet_id.bt_child_ids
                url = f"{self.env.company.bitcoin_api_url}/api/address/{btc_wallet.acc_number}/txs"
                _logger.info("GET " + url)
                for tx in requests.get(url).json():
                    tx_hash = tx["txid"]
                    if self.env["crypto.transaction"].search_count(
                        [
                            ("name", "=", tx_hash),
                            ("wallet_id", "in", same_wallets.ids),
                        ],
                        limit=1,
                    ):
                        continue  # Transaction already exists
                    transactions_data.append(
                        {
                            "name": tx_hash,
                            "wallet_id": btc_wallet.id,
                            "raw": json.dumps(tx),
                            "state": "draft",
                        }
                    )
            all_transactions |= self.env["crypto.transaction"].create(transactions_data)
            # btc_wallets.crypto_sync_done = True
        return all_transactions

    def _compute_explorer_link(self):
        super()._compute_explorer_link()
        for wallet in self.filtered(
            lambda x: x.crypto_provider == "bitcoin" and x.bt_address_format not in ("xpub", "ypub", "zpub", "vpub")
        ):
            wallet.explorer_link = f"{self.env.company.bitcoin_api_url}/address/{wallet.acc_number}"
