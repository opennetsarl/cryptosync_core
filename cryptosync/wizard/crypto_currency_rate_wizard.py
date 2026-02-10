import time

from dateutil.rrule import DAILY, rrule
from odoo import fields, models


class CryptoCurrencyRateWizard(models.TransientModel):
    _name = "crypto.currency.rate.wizard"
    _description = "Get Cryptocurrency Rates Wizard"

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        domain=[("crypto_rate_provider_id", "!=", False)],
    )
    use_range = fields.Boolean("Use Range")
    rate_date = fields.Date(
        "Date",
        required=True,
        default=fields.Date.today,
    )
    rate_date_to = fields.Date(
        "Date To",
        default=fields.Date.today,
    )

    def get_crypto_currency_rate(self):
        if self.use_range:
            all_rates = self.env["res.currency.rate"].search([("currency_id", "=", self.currency_id.id)]).mapped("name")
            for dt in rrule(DAILY, dtstart=self.rate_date, until=self.rate_date_to):
                d = dt.date()
                if d in all_rates:
                    continue
                time.sleep(1)
                self.currency_id.get_crypto_currency_rate(d)
        else:
            self.currency_id.get_crypto_currency_rate(self.rate_date)
