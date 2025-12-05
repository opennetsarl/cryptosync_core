import requests
from odoo import fields, models

SEARCH_URL = "https://api.coingecko.com/api/v3/search?query="
COIN_URL = "https://api.coingecko.com/api/v3/coins/"


class CryptoCurrencyManagerWizard(models.TransientModel):
    _inherit = "crypto.currency.manager.wizard"

    def _prepare_suggestions(self):
        if self.provider_id.code != "coingecko":
            return super()._prepare_suggestions()

        r = requests.get(SEARCH_URL + (self.name or ""))
        data = []
        for coin in r.json().get("coins", []):
            data.append(
                {
                    "currency_id": self.currency_id.id,
                    "name": coin.get("symbol"),
                    "full_name": coin.get("name"),
                    "coingecko_api_code": coin.get("id"),
                    "is_crypto": True,
                }
            )
        return data


class CryptoCurrencyManagerWizardSuggestion(models.TransientModel):
    _inherit = "crypto.currency.manager.wizard.suggestion"

    coingecko_api_code = fields.Char("CoinGecko API ID")

    def _prepare_data(self):
        data = super()._prepare_data()
        if self.coingecko_api_code:
            data["coingecko_api_code"] = self.coingecko_api_code
            if "ethereum_smart_contract" in self.currency_id._fields:
                # cryptosync_ethereum is installed
                if self.coingecko_api_code == "ethereum":
                    data["ethereum_smart_contract"] = "ETH"
                else:
                    r = requests.get(COIN_URL + self.coingecko_api_code)
                    if r.status_code == 200:
                        data["ethereum_smart_contract"] = r.json().get("platforms", {}).get("ethereum")
        return data
