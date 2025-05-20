from odoo import api, fields, models


class CryptoBtcAddress(models.Model):
    _name = "crypto.btc.address"
    _description = "Bitcoin Address"
    _order = "hd_wallet_id,derivation_path,name"

    name = fields.Char("Address", required=True)
    address_format = fields.Selection(
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
        string="Address Format",
        compute="_compute_address_format",
        store=True,
    )
    hd_wallet_id = fields.Many2one("res.partner.bank", string="HD Wallet", required=True)
    derivation_path = fields.Char("Derivation Path")
    is_empty = fields.Boolean("Is Empty", compute="_compute_is_empty")

    @api.model
    def _get_address_type(self, address):
        length = len(address)
        if address.startswith(("04", "03", "02")):
            return "P2PK"
        if address.startswith("1") and 26 <= length <= 34:
            return "P2PKH"
        if address.startswith("3") and length == 34:
            return "P2SH"
        if address.startswith("bc1q") and length == 42:
            return "P2WPKH"
        if address.startswith("bc1q") and length == 62:
            return "P2WSH"
        if address.startswith("bc1p") and length == 62:
            return "P2TR"
        if address.startswith("xpub"):
            return "xpub"
        if address.startswith("ypub"):
            return "ypub"
        if address.startswith("zpub"):
            return "zpub"
        if address.startswith("vpub"):
            return "vpub"
        return False

    @api.depends("name")
    def _compute_address_format(self):
        self.address_format = False
        for address in self:
            address.address_format = self._get_address_type(address.name)

    def _compute_is_empty(self):
        self.is_empty = True
        for address in self:
            if self.env["crypto.transaction"].search_count(
                [("wallet_id", "=", address.hd_wallet_id.id), ("btc_addresses", "ilike", address.name)], limit=1
            ) or self.env["account.move"].search_count([("btc_payment_address", "ilike", address.name)], limit=1):
                address.is_empty = False

    def action_open_parent_bitcoin_addresses(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.hd_wallet_id.acc_number,
            "res_model": "res.partner.bank",
            "res_id": self.hd_wallet_id.id,
            "view_mode": "form",
        }
