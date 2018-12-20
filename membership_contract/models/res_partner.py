# -*- coding: utf-8 -*-
# Copyright 2017-2019 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=protected-access
import logging
from odoo import _, api, fields, models


MEMBERSHIP_ANALYSIS_STATEMENT = """\
WITH membership_analysis AS (
SELECT
     rp.id as id,
     associate_member,
     COALESCE(rp.membership, false) AS is_member,
     COALESCE(cl.membership, false) AS should_be_member
 FROM
     res_partner rp
 LEFT OUTER JOIN
     account_analytic_account c ON rp.id = c.partner_id
 LEFT OUTER JOIN
     account_analytic_invoice_line cl ON c.id = cl.analytic_account_id AND
     cl.membership
 WHERE
     (c.date_start IS NULL OR c.date_start <= CURRENT_DATE) AND
     (c.date_end IS NULL OR c.date_end >= CURRENT_DATE)
 )
 SELECT id FROM membership_analysis
 WHERE is_member <> should_be_member AND associate_member IS NULL
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
