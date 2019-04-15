# -*- coding: utf-8 -*-
# Copyright 2017-2019 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=protected-access
import logging
from odoo import _, api, fields, models


MEMBERSHIP_ANALYSIS_STATEMENT = """\
WITH contract_members AS (
 SELECT
     aaa.partner_id, aail.membership
 FROM account_analytic_account aaa
 INNER JOIN account_analytic_invoice_line aail
     ON aaa.id = aail.analytic_account_id
    AND aail.membership
 WHERE
     (aaa.date_start IS NULL OR aaa.date_start <= CURRENT_DATE) AND
     (aaa.date_end IS NULL OR aaa.date_end >= CURRENT_DATE)
),
 direct_members AS (
 SELECT rp.id as partner_id, rp.membership
 FROM res_partner rp
 WHERE rp.membership AND associate_member IS NULL
)
 SELECT
     COALESCE(cm.partner_id, dm.partner_id) AS partner_id
 FROM contract_members cm
 FULL OUTER JOIN direct_members dm
     ON cm.partner_id = dm.partner_id
 WHERE (cm.membership IS NULL AND NOT dm.membership IS NULL)
    OR (dm.membership IS NULL AND NOT cm.membership IS NULL)
"""

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


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
        today = fields.Date.today()
        for this in self:
            save_membership = this.membership
            membership = False
            for line in this.membership_line_ids:
                # Check wether line belongs to active contract
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
            if membership != save_membership:
                if save_membership:
                    _logger.info(
                        _('%s is no longer a member'), this.display_name)
                else:
                    _logger.info(_('%s is now a member'), this.display_name)
                this.write(vals)
                this.membership_change_trigger()

    @api.multi
    def write(self, vals):
        result = super(ResPartner, self).write(vals)
        if 'membership' in vals:
            self.membership_change_trigger()
        return result

    @api.model
    def cron_compute_membership(self):
        """Recompute membership for all direct members.

        We use an SQL query to select the records that should be updated.

        Associate members are automatically updated when updating the direct
        membership.
        """
        self.env.cr.execute(MEMBERSHIP_ANALYSIS_STATEMENT)
        data = self.env.cr.fetchall()
        partner_ids = [rec[0] for rec in data]
        partners = self.browse(partner_ids)
        return partners._compute_membership()
