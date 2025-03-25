from odoo import api, fields, models


class CryptoProvider(models.Model):
    _name = "crypto.provider"
    _description = "Crypto Provider"
    _order = "sequence,name,id"

    active = fields.Boolean(default=True)
    name = fields.Char("Name", required=True)
    code = fields.Char("Code", readonly=True)
    sequence = fields.Integer(required=True, default=10)
    prefix = fields.Char("Prefix")
    provide_tx = fields.Boolean("Provide Transactions", default=True, readonly=True)
    provide_rate = fields.Boolean("Provide Rates", default=False, readonly=True)
    output_type = fields.Selection(
        [
            ("statement", "Statements"),
            ("move", "Entries"),
        ],
        string="Output Type",
    )
    csv_only = fields.Boolean("CSV Only", default=False, readonly=True)
    image = fields.Image(string="Icon")

    def create_menus(self):
        IrModelData = self.env["ir.model.data"]
        Menu = self.env["ir.ui.menu"]
        ActWindow = self.env["ir.actions.act_window"]

        cryptosync_main_menu = self.env.ref("cryptosync.menu_crypto_main")
        for provider in self.filtered("provide_tx"):
            provider_main_menu = Menu.create(
                {
                    "name": provider.name,
                    "parent_id": cryptosync_main_menu.id,
                    "sequence": provider.sequence,
                }
            )
            IrModelData.create(
                {
                    "name": "menu_crypto_" + provider.code,
                    "model": "ir.ui.menu",
                    "module": "cryptosync_xmenu",
                    "res_id": provider_main_menu.id,
                }
            )
            for xmlid in (  # menus
                "menu_crypto_wallet_template",
                "menu_crypto_import_exchange_wizard_template",
                "menu_crypto_transaction_template",
                "menu_crypto_transaction_line_template",
                "menu_crypto_move_template",
                "menu_crypto_statement_template",
                "menu_crypto_statement_line_template",
                "menu_crypto_account_rule_template",
                "menu_crypto_journal_template",
            ):
                template_menu = self.env.ref("cryptosync." + xmlid)
                action = template_menu.action
                action = {
                    field: value
                    for field, value in action.sudo().read()[0].items()
                    if field in action._get_readable_fields()
                }
                action["name"] = (action["name"] or "").replace("Template", provider.name) or False
                action["domain"] = (action["domain"] or "").replace("template", provider.code) or False
                action["context"] = (action["context"] or "").replace("template_id", str(provider.id)) or False
                action["view_ids"] = [
                    (0, 0, {"view_id": view_id, "view_mode": view_mode}) for view_id, view_mode in action["views"]
                ]
                action["view_id"] = action["view_id"][0] if action["view_id"] else False
                action["search_view_id"] = action["search_view_id"][0] if action["search_view_id"] else False
                action_id = ActWindow.create(action)

                active = True  # Disable a menu when output type made it irrelevant
                if provider.output_type != "statement":
                    if xmlid in ("menu_crypto_statement_template", "menu_crypto_statement_line_template"):
                        active = False
                elif provider.output_type != "move":
                    if xmlid in ("menu_crypto_move_template", "menu_crypto_account_rule_template"):
                        active = False

                menu_id = Menu.create(
                    {
                        "name": template_menu.name,
                        "action": f"ir.actions.act_window,{action_id.id}",
                        "parent_id": provider_main_menu.id,
                        "sequence": template_menu.sequence,
                        "active": active,
                    }
                )
                IrModelData.create(
                    [
                        {
                            "name": xmlid.replace("menu", "action").replace("template", provider.code),
                            "model": "ir.actions.act_window",
                            "module": "cryptosync_xmenu",
                            "res_id": action_id.id,
                        },
                        {
                            "name": xmlid.replace("template", provider.code),
                            "model": "ir.ui.menu",
                            "module": "cryptosync_xmenu",
                            "res_id": menu_id.id,
                        },
                    ]
                )

    def update_menus(self):
        for provider in self.filtered("provide_tx"):
            menu = self.env.ref("cryptosync_xmenu.menu_crypto_" + provider.code, raise_if_not_found=False)
            if menu:
                menu.sequence = provider.sequence

    def delete_menus(self):
        for provider in self.filtered("provide_tx"):
            for ir_model_data in self.env["ir.model.data"].search(
                [("module", "=", "cryptosync_xmenu"), ("name", "ilike", provider.code)]
            ):
                self.env[ir_model_data.model].browse(ir_model_data.res_id).unlink()

    def refresh_all_menus(self):
        providers = self.search([])
        providers.delete_menus()
        providers.create_menus()
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.create_menus()
        return res

    def write(self, vals):
        res = super().write(vals)
        if "sequence" in vals:
            self.update_menus()
        elif "active" in vals:
            if vals["active"]:
                self.create_menus()
            else:
                self.delete_menus()
        return res

    def unlink(self):
        self.delete_menus()
        return super().unlink()
