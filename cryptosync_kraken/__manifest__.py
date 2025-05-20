# -*- coding: utf-8 -*-
{
    "name": "CryptoSync Kraken",
    "version": "18.0.1.0.0",
    "description": """
Sync transactions from the [Kraken](https://www.kraken.com/) exchange

""",
    "author": "Yannis Burkhalter",
    "website": "https://www.open-net.ch/innovation/crypto",
    "license": "AGPL-3",
    "category": "Accounting",
    "depends": ["cryptosync"],
    "data": [
        "data/crypto_provider.xml",
        "views/res_currency.xml",
        "views/res_partner_bank.xml",
    ],
}
