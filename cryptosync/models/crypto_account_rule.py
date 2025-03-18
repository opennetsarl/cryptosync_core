from odoo import fields, models


class CryptoAccountRule(models.Model):
    _name = "crypto.account.rule"
    _description = "Crypto Account Rule"
    _order = "sequence,id"

    active = fields.Boolean(default=True)
    sequence = fields.Integer(required=True, default=10)
    name = fields.Char("Name", required=True)
    provider_id = fields.Many2one("crypto.provider", string="Provider", required=True)
    account_id = fields.Many2one("account.account", "Account", required=True)
    domain = fields.Char("Domain", required=True)
