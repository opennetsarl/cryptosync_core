from odoo import api, fields, models


class CryptoCurrencyManagerWizard(models.TransientModel):
    _name = "crypto.currency.manager.wizard"
    _description = "Currency Manager"

    name = fields.Char("Search")
    previous_name = fields.Char("Previous Search")
    currency_id = fields.Many2one("res.currency", string="Currency", required=True)
    provider_id = fields.Many2one("crypto.provider", string="Provider", required=True)

    suggestion_ids = fields.One2many(
        "crypto.currency.manager.wizard.suggestion", compute="_compute_suggestion_ids", string="Suggestions"
    )

    def _prepare_suggestions(self):
        return []

    @api.depends("name")
    def _compute_suggestion_ids(self):
        if self.name != self.previous_name:
            data = self._prepare_suggestions()
            self.suggestion_ids = self.env["crypto.currency.manager.wizard.suggestion"].create(data) if data else False
        else:
            self.suggestion_ids = self.suggestion_ids or False
        self.previous_name = self.name


class CryptoCurrencyManagerWizardSuggestion(models.TransientModel):
    _name = "crypto.currency.manager.wizard.suggestion"
    _description = "Currency Manager Suggestion"

    currency_id = fields.Many2one("res.currency", string="Currency", required=True)
    name = fields.Char("Name", required=True)
    full_name = fields.Char("Full Name")
    is_crypto = fields.Boolean("Cryptocurrency?")

    def _prepare_data(self):
        return {
            field: getattr(self, field)
            for field in (
                "name",
                "full_name",
                "is_crypto",
            )
            if getattr(self, field)
        }

    def action_choose(self):
        data = self._prepare_data()
        for key in list(data):
            if getattr(self.currency_id, key):
                # do not overwrite existing fields
                del data[key]
        self.currency_id.write(data)
