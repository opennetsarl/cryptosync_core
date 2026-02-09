import logging

import requests
from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = "res.currency"

    coingecko_api_code = fields.Char("CoinGecko API ID")

    def get_crypto_currency_rate(self, rate_date=False):
        super().get_crypto_currency_rate(rate_date)

        rate_date = rate_date or fields.Date.today()

        for currency in self.filtered(lambda x: x.crypto_rate_provider_id.code == "coingecko"):
            if not currency.coingecko_api_code:
                raise UserError(_("Unable to get rates without the CoinGecko API ID. Please fill it."))

            api_key = self.env.company.coingecko_api_key_id.sudo().name
            if api_key:
                url = "https://pro-api.coingecko.com/api/v3/coins/{}/history?date={}&x_cg_pro_api_key={}"
            else:
                url = "https://api.coingecko.com/api/v3/coins/{}/history?date={}"
            url = url.format(currency.coingecko_api_code, rate_date.strftime("%d-%m-%Y"), api_key)
            _logger.info("GET " + url)
            data = requests.get(url).json()

            if "status" in data:
                raise UserError(
                    _("An error {error_code} was returned by the CoinGecko API:\n{error_message}").format(
                        **data["status"]
                    )
                )

            all_rates = data["market_data"]["current_price"]
            code = self.env.company.currency_id.name.lower()
            if code not in all_rates:
                raise UserError(
                    _("CoinGecko does not provide value in {ccy}. Please contact us.").format(ccy=code.upper())
                )
            inverse_rate = all_rates[code]
            if inverse_rate == 0:
                raise UserError(_("The rate provided by CoinGecko is 0. Please contact us."))

            self.env["res.currency.rate"].with_context(fix_crypto_units=True).create(
                {
                    "name": rate_date,
                    "currency_id": currency.id,
                    "inverse_company_rate": inverse_rate,
                }
            )

    def open_coingecko(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "https://www.coingecko.com/coins/" + self.coingecko_api_code,
            "target": "new",
        }
