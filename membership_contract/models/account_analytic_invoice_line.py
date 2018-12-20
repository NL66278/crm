# -*- coding: utf-8 -*-
# Copyright 2017-2018 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountAnalyticInvoiceLine(models.Model):
    _inherit = 'account.analytic.invoice.line'

    membership = fields.Boolean(string='Membership product line')

    @api.multi
    def set_membership(self):
        """Set membership in line according to product_id.

        Make sure membership correctly set on partner.
        """
        for this in self:
            if this.membership != this.product_id.membership:
                super(AccountAnalyticInvoiceLine, this).write(
                    {'membership': this.product_id.membership})

    @api.model
    def create(self, vals):
        result = super(AccountAnalyticInvoiceLine, self).create(vals)
        result.set_membership()  # pylint: disable=no-member
        return result

    @api.multi
    def write(self, vals):
        result = super(AccountAnalyticInvoiceLine, self).write(vals)
        self.set_membership()
        return result
