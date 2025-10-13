# -*- coding: utf-8 -*-
{
    "name": "CryptoSync",
    "version": "19.0.1.0.0",
    "description": """
Cryptocurrency base module for Odoo

""",
    "author": "Yannis Burkhalter",
    "website": "https://www.open-net.ch/innovation/crypto",
    "license": "AGPL-3",
    "category": "Accounting",
    "depends": ["account"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "data/cron.xml",
        "views/account_journal.xml",
        "views/crypto_account_rule.xml",
        "views/crypto_api_key.xml",
        "views/crypto_provider.xml",
        "views/crypto_transaction.xml",
        "views/crypto_transaction_line.xml",
        "views/res_config_settings.xml",
        "views/res_currency.xml",
        "views/res_partner_bank.xml",
        "wizard/crypto_currency_manager_wizard.xml",
        "wizard/crypto_currency_rate_wizard.xml",
        "wizard/crypto_generate_statements_wizard.xml",
        "wizard/crypto_import_transactions_wizard.xml",
        "views/menu.xml",
        "data/provider_menu_template.xml",
    ],
    "application": True,
}
