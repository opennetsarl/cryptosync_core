# -*- coding: utf-8 -*-
{
    "name": "CryptoSync Bitcoin",
    "version": "18.0.1.0.0",
    "description": """
Sync transactions from [mempool.space](https://mempool.space/) or [blockstream.info](https://blockstream.info/)
""",
    "author": "Yannis Burkhalter",
    "website": "https://www.open-net.ch/innovation/crypto",
    "license": "AGPL-3",
    "category": "Accounting",
    "depends": ["cryptosync"],
    "data": [
        "security/ir.model.access.csv",
        "data/crypto_provider.xml",
        "views/crypto_btc_address.xml",
        "views/res_config_settings.xml",
        "views/res_partner_bank.xml",
    ],
    "external_dependencies": {
        "python": ["btclib"],
    },
}
