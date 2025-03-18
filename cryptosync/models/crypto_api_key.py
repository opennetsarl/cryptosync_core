from odoo import fields, models


class CryptoApiKey(models.Model):
    _name = "crypto.api.key"
    _description = "Crypto API Key"
    _rec_name = "description"

    name = fields.Char("API Key", required=True)
    description = fields.Char("Description", required=True)
