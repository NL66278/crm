# -*- coding: utf-8 -*-
# Copyright 2017-2018 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    membership = fields.Boolean(
        string='Is member?',
        readonly=True)
    associate_member = fields.Many2one(  # no _id to be compatible with std.
        comodel_name='res.partner',
        string='Member via partner',
        readonly=True,
        index=True)
    membership_line_ids = fields.One2many(
        comodel_name='account.analytic.invoice.line',
        inverse_name='partner_id',
        domain=[('membership', '=', True)],
        string='Membership contract lines')

    @api.multi
    def membership_change_trigger(self):
        """Allows other models to react on change in membership state.

        This method is meant to be overridden in other modules.
        """
        pass

    @api.multi
    def _compute_membership(self):
        """Compute wether partner is a direct member.

        Dependent modules might compute membership through association
        with members determined here. Therefore membership will not be
        updated if member through association.
        """
        for this in self:
            save_membership = this.membership
            membership = False
            # membership_line_ids not updated at this point!!
            line_model = self.env['account.analytic.invoice.line']
            lines = line_model.search([
                ('partner_id', '=', this.id),
                ('membership', '=', True)])
            for line in lines:
                # Check wether line belongs to active contract
                today = fields.Date.today()
                contract = line.analytic_account_id
                if ((contract.date_start and contract.date_start > today) or
                        (contract.date_end and contract.date_end < today)):
                    continue  # not active contract
                membership = True
                break
            if not membership and this.associate_member:
                # Leave membership through association alone.
                continue
            if membership != save_membership:
                vals = {'membership': membership}
                if membership:
                    # clear associate membership, if now direct member.
                    vals['associate_member'] = False
                super(ResPartner, this).write(vals)
                this.membership_change_trigger()

    @api.multi
    def write(self, vals):
        result = super(ResPartner, self).write(vals)
        if 'membership' in vals:
            self.membership_change_trigger()
        return result
