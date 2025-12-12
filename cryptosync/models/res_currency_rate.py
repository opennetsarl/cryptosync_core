from decimal import Decimal

from odoo import api, fields, models


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    currency_id = fields.Many2one(readonly=False)  # useful for import

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("fix_crypto_units"):
            for vals in vals_list:
                if "currency_id" not in vals:
                    continue
                currency = self.env["res.currency"].browse(vals["currency_id"])
                if "rate" in vals:
                    vals["rate"] = float(Decimal(str(vals["rate"])) / Decimal(currency.crypto_unit or 1))
                if "company_rate" in vals:
                    vals["company_rate"] = float(
                        Decimal(str(vals["company_rate"])) / Decimal(currency.crypto_unit or 1)
                    )
                if "inverse_company_rate" in vals:
                    vals["inverse_company_rate"] = float(
                        Decimal(str(vals["inverse_company_rate"])) * Decimal(currency.crypto_unit or 1)
                    )
        return super().create(vals_list)
