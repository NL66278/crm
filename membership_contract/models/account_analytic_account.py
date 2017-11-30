# -*- coding: utf-8 -*-
# Copyright 2018 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    @api.multi
    def write(self, vals):
        result = super(AccountAnalyticAccount, self).write(vals)
        if 'date_start' in vals or 'date_end' in vals:
            for this in self:
                this.partner_id._compute_membership()
        return result

    @api.multi
    def unlink(self):
        """Unlinking might effect membership, first unlink lines."""
        for this in self:
            this.recurring_invoice_line_ids.unlink()
            this.partner_id._compute_membership()
        return super(AccountAnalyticAccount, self).unlink()
