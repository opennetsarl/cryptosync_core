import logging
import traceback
from ast import literal_eval

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCurrency(models.Model):
    _inherit = "res.currency"

    # Allow more than 3 characters
    name = fields.Char(size=None)

    # Overriding the rounding to support up to 12 decimal numbers
    # Default is (12, 6)
    # We recommend not allowing more than 12 decimal places, as beyond that, the rounding gets weird
    rounding = fields.Float(digits=(24, 12))

    is_crypto = fields.Boolean(string="Cryptocurrency?")

    crypto_rate_provider_id = fields.Many2one(
        "crypto.provider", string="Crypto Provider", domain=[("provide_rate", "=", True)]
    )

    crypto_unit = fields.Selection(
        selection=[
            ("1000000", "M"),
            ("1000", "k"),
            ("0.001", "m"),
            ("0.000001", "μ"),
        ],
        string="Unit",
    )

    def get_crypto_currency_rate(self, rate_date=None):
        rate_date = rate_date or fields.Date.today()
        if rate_date > fields.Date.today():
            raise UserError(_("No rates for future dates."))

        for currency in self.filtered("crypto_rate_provider_id"):
            if self.env["res.currency.rate"].search(
                [("name", "=", rate_date), ("currency_id", "=", currency.id)], limit=1
            ):
                raise UserError(
                    _("A rate already exists for {ccy} on {date}.").format(ccy=currency.name, date=rate_date)
                )

    def _cron_crypto_rate(self):
        existing_rates = self.env["res.currency.rate"].search([("name", "=", fields.Date.today())])
        currencies = self.search(
            [("crypto_rate_provider_id", "!=", False), ("currency_id", "not in", existing_rates.currency_id.ids)]
        )
        for currency in currencies:
            try:
                currency.get_crypto_currency_rate()
            except Exception:
                _logger.error(traceback.format_exc())

    @api.onchange("crypto_unit")
    def onchange_crypto_unit(self):
        selection = dict(self._fields["crypto_unit"].selection)
        for currency in self:
            currency.symbol = selection.get(currency.crypto_unit, "") + (
                currency.currency_unit_label or currency.name or ""
            )

    def action_crypto_currency_rate_wizard(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("cryptosync.action_crypto_currency_rate_wizard")
        action["context"] = literal_eval(action["context"])
        action["context"]["default_currency_id"] = self.id
        return action

    def action_crypto_currency_manager_wizard(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("cryptosync.action_crypto_currency_manager_wizard")
        action["context"] = literal_eval(action["context"])
        action["context"]["default_currency_id"] = self.id
        action["context"]["default_name"] = self.full_name or self.name
        if "crypto_provider" in self.env.context:
            provider = self.env["crypto.provider"].search([("code", "=", self.env.context["crypto_provider"])], limit=1)
            if provider:
                action["context"]["default_provider_id"] = provider.id
        return action
