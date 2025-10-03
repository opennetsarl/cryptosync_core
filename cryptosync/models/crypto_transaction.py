import logging
from collections import defaultdict
from decimal import Decimal

from odoo import _, api, fields, models
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)


class CryptoTransaction(models.Model):
    _name = "crypto.transaction"
    _description = "Cryptocurrency Transaction"
    _order = "wallet_id,name,id"

    name = fields.Char("Transaction Identifier", readonly=True)
    ref = fields.Char("Reference", readonly=True)
    wallet_id = fields.Many2one("res.partner.bank", string="Wallet", readonly=True, ondelete="restrict")
    explorer_link = fields.Char("Explorer Link", compute="_compute_explorer_link")

    state = fields.Selection(
        [
            ("waiting", "Waiting"),  # transaction not complete, more sync calls needed
            ("draft", "Draft"),  # transaction just created, needs to be processed
            ("ignored", "Ignored"),  # transaction created, but manually ignored
            ("error", "Error"),  # transaction failed to be processed
            ("ready", "Ready"),  # 1-n transaction.s available for statement generation
            ("partially", "Partially Done"),  # some transactions imported in statements
            ("done", "Done"),  # all transactions imported or ignored
        ],
        string="State",
        default="waiting",
        readonly=True,
    )
    raw = fields.Json("JSON", readonly=True)
    from_csv = fields.Boolean("From CSV", readonly=True)
    output_ids = fields.One2many("crypto.transaction.line", "transaction_id", string="Output", readonly=True)
    error = fields.Text("Error Description", readonly=True)
    has_ignored_line = fields.Boolean("Has Ignored Lines", compute="_compute_has_ignored_lines")

    def reset(self):  # output: [draft]
        self = self.filtered(lambda x: x.state in ("draft", "error", "ready"))
        self.output_ids.unlink()
        self.error = False
        self.state = "draft"

    def process(self):  # output: [ready|error]
        self = self.filtered(lambda x: x.state in ("draft", "error", "ready"))
        self.reset()
        self._process()

    def _process(self):
        # to inherit
        return self

    def ignore(self):  # output: [ignored]
        self = self.filtered(lambda x: x.state in ("draft", "error", "ready"))
        self.error = False
        self.state = "ignored"
        self.output_ids.state = "ignored"

    def revert_ignore(self):  # output: [draft]
        self = self.filtered(lambda x: x.state == "ignored")
        self.state = "draft"
        self.output_ids.unlink()

    def ignore_rest(self):  # output: [done]
        self.filtered(lambda x: x.state in ("ready", "partially")).output_ids.filtered(
            lambda x: x.state == "ready"
        ).state = "ignored"

    def revert_ignore_rest(self):  # output: [ready|partially]
        self.filtered(lambda x: x.state == "done").output_ids.filtered(lambda x: x.state == "ignored").state = "ready"

    def _compute_has_ignored_lines(self):
        for tx in self:
            tx.has_ignored_line = bool(tx.output_ids.filtered(lambda x: x.state == "ignored"))

    def _recompute_state(self):  # output: [ready|partially|done]
        self = self.filtered(lambda x: x.state in ("ready", "partially", "done"))
        for tx in self:
            nb_ready = len(tx.output_ids.filtered(lambda x: x.state == "ready"))
            if nb_ready == len(tx.output_ids):
                tx.state = "ready"
            elif nb_ready == 0:
                tx.state = "done"
            else:
                tx.state = "partially"

    def unlink(self):
        self = self.filtered(lambda x: x.state in ("waiting", "draft", "ignored", "error", "ready"))
        return super(CryptoTransaction, self).unlink()

    def generate_moves(self, journal_id=False):
        with Registry(self.env.cr.dbname).cursor() as new_cr:
            # Create a new env, so we can use cr.commit() safely
            self = self.with_env(api.Environment(new_cr, self.env.uid, self.env.context))

            self = self.filtered(lambda x: x.wallet_id.crypto_output_type == "move" and x.state == "ready")
            jid = journal_id.id if journal_id else False
            if journal_id:
                self = self.filtered("wallet_id.crypto_default_move_journal_id")
            self.output_ids._compute_account_id()
            self.output_ids._compute_journal_id()
            moves = []
            for tx in self:
                move = {
                    # "name": "/",
                    "ref": tx.ref or tx.name,
                    "journal_id": jid or tx.wallet_id.crypto_default_move_journal_id.id,
                    "crypto_transaction_id": tx.id,
                    "line_ids": [],
                }
                names_count = defaultdict(int)
                for output in tx.output_ids:
                    names_count[output.name] += 1
                for output in tx.output_ids:
                    if not output.account_id or not output.journal_id.default_account_id:
                        # raise UserError(_("No account matching! Please check your crypto account rules."))
                        break
                    move["date"] = max(move["date"], output.date) if "date" in move else output.date
                    line = {
                        "name": output.name,
                        "amount_currency": output.value,
                        "amount_currency_str": output.value_str,
                        "debit": abs(output.get_fiat_value()) if output.value > 0 else 0,
                        "credit": abs(output.get_fiat_value()) if output.value < 0 else 0,
                        "currency_id": output.currency_id.id,
                        "account_id": output.journal_id.default_account_id.id,
                        "crypto_transaction_id": output.id,
                    }
                    move["line_ids"].append((0, 0, line))
                    if (output.name.startswith("BUY") and output.value > 0) or (
                        output.name.startswith("SELL") and output.value < 0
                    ):
                        # TODO: move this condition
                        move["currency_id"] = output.currency_id.id
                    if names_count[output.name] == 1:
                        line_2 = line.copy()
                        line_2["debit"], line_2["credit"] = line_2["credit"], line_2["debit"]
                        line_2["amount_currency"] *= -1
                        line_2["amount_currency_str"] = str(-Decimal(output.value_str))
                        line_2["account_id"] = output.account_id.id
                        move["line_ids"].append((0, 0, line_2))
                else:  # only executed if the previous loop did NOT break
                    delta = sum(line[2]["debit"] - line[2]["credit"] for line in move["line_ids"])
                    if delta:
                        line = {
                            "name": _("Delta"),
                            "debit": -min(delta, 0),
                            "credit": max(delta, 0),
                            "account_id": self.env.company.income_currency_exchange_account_id.id
                            if delta > 0
                            else self.env.company.expense_currency_exchange_account_id.id,
                        }
                        move["line_ids"].append((0, 0, line))
                    moves.append(move)

            n = int(self.env["ir.config_parameter"].sudo().get_param("cryptosync.account_move_batch_size", 100))
            batches = [moves[i : i + n] for i in range(0, len(moves), n)]
            all_ids = []
            i, j = 0, len(batches)
            for moves in batches:
                records = self.env["account.move"].create(moves)
                records.line_ids.crypto_transaction_id.state = "done"
                all_ids += records.ids
                new_cr.commit()
                i += 1
                _logger.info(f"Batch {i}/{j} imported")
        return {
            "type": "ir.actions.act_window",
            "name": _("Generated Moves"),
            "res_model": "account.move",
            "domain": [("id", "in", all_ids)],
            "view_mode": "list,form",
        }

    def get_action_return(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Imported Transactions"),
            "res_model": "crypto.transaction",
            "domain": [("id", "in", self.ids)],
            "view_mode": "list,form",
        }

    def _compute_explorer_link(self):
        self.filtered(lambda x: not x.explorer_link).explorer_link = False

    def open_on_explorer(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.explorer_link,
            "target": "new",
        }
