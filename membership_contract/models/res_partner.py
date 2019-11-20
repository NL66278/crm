# -*- coding: utf-8 -*-
# Copyright 2017-2019 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=missing-docstring,protected-access,invalid-name
import logging

from odoo import _, api, fields, models, registry


# Statements to get rid of unwanted NULL values
NO_NULL_MEMBERSHIP_STATEMENT = """\
UPDATE res_partner SET membership = false WHERE membership IS NULL
"""
NO_NULL_DIRECT_MEMBER_STATEMENT = """\
UPDATE res_partner SET direct_member = false WHERE direct_member IS NULL
"""


# Mark all members with no associate member as direct member.
DIRECT_MEMBERSHIP_STATEMENT = """\
UPDATE res_partner SET direct_member = true
 WHERE membership AND associate_member IS NULL
"""


# Statement to determine wether a particular partner should be direct member.
DETERMINE_PARTNER_MEMBERSHIP_STATEMENT = """\
SELECT COUNT(*)
 FROM account_analytic_invoice_line l
 JOIN account_analytic_account c ON l.analytic_account_id = c.id
 WHERE l.partner_id = %(partner_id)s
   AND l.membership
   AND (c.date_start IS NULL OR c.date_start <= current_date)
   AND (c.date_end IS NULL OR c.date_end >= current_date)
"""


# Statement to find all partners that should be direct_member, but are not.
DIRECT_MEMBER_SHOULD_BE_STATEMENT = """\
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
)
 SELECT id from res_partner
 WHERE (NOT membership OR NOT direct_member)
   AND id IN (SELECT partner_id FROM contract_members)
"""


# Statement to find all partners that should not be direct_member, but are.
DIRECT_MEMBER_SHOULD_NOT_BE_STATEMENT = """\
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
)
 SELECT id from res_partner
 WHERE (direct_member OR (membership AND associate_member IS NULL))
   AND id NOT IN (SELECT partner_id FROM contract_members)
"""

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class ResPartner(models.Model):
    _inherit = "res.partner"

    membership = fields.Boolean(string="Is member?", readonly=True)
    direct_member = fields.Boolean(string="Is direct member?", readonly=True)
    associate_member = fields.Many2one(  # no _id to be compatible with std.
        comodel_name="res.partner",
        string="Member via partner",
        readonly=True,
        index=True,
    )
    membership_line_ids = fields.One2many(
        comodel_name="account.analytic.invoice.line",
        inverse_name="partner_id",
        domain=[("membership", "=", True)],
        string="Membership contract lines",
    )

    @api.multi
    def membership_change_trigger(self):
        """Allows other models to react on change in membership state.

        This method is meant to be overridden in other modules.
        """
        pass

    @api.multi
    def _compute_membership(self):
        """Compute wether partner is a member.

        Collect all changes needed in vals. This dictionary is also passed
        to underlying methods that will enable those methods to add their
        own content.
        """
        for this in self:
            vals = {}
            membership = this._is_member(vals)
            if membership != this.membership:
                if membership:
                    _logger.info(_("%s is now a member"), this.display_name)
                else:
                    _logger.info(_("%s is no longer a member"), this.display_name)
                vals["membership"] = membership
            if vals:
                this.write(vals)
                if "membership" in vals:
                    this.membership_change_trigger()

    @api.multi
    def _is_member(self, vals):
        """Check personal membership.

        Might be extended for other forms of membership.
        """
        self.ensure_one()
        self.env.cr.execute(
            DETERMINE_PARTNER_MEMBERSHIP_STATEMENT, {"partner_id": self.id}
        )
        # resultset should contain only one row: the line count.
        membership_line_count = self.env.cr.fetchone()[0]
        direct_member = membership_line_count > 0
        if direct_member != self.direct_member:
            vals["direct_member"] = direct_member
        return direct_member

    @api.model
    def cron_compute_membership(self):
        """Recompute membership for all direct members.

        We create a separate cursor to commit each step separately.
        """
        # Prevent recursive call.
        if self.env.context.get("in_cron_compute_membership", False):
            return
        self = self.with_context(in_cron_compute_membership=True)
        self._recompute_membership()

    @api.model
    def _recompute_membership(self):
        """Recompute membership for all direct members.

        We create a separate cursor to commit each step separately.
        """
        # Prevent recursive call.
        if self.env.context.get("in_cron_compute_membership", False):
            return
        self = self.with_context(in_cron_compute_membership=True)
        # Make our own cursor
        new_cr = registry(self._cr.dbname).cursor()
        # Start off by getting rid of NULL values
        new_cr.execute(NO_NULL_MEMBERSHIP_STATEMENT)
        new_cr.commit()
        new_cr.execute(NO_NULL_DIRECT_MEMBER_STATEMENT)
        new_cr.commit()
        # Mark all members with no associate member as direct member.
        new_cr.execute(DIRECT_MEMBERSHIP_STATEMENT)
        new_cr.commit()
        # Now handle those that should be direct member
        self.env.cr.execute(DIRECT_MEMBER_SHOULD_BE_STATEMENT)
        self._recompute_partners_from_cursor()
        # Now handle those that should no longer be direct member
        self.env.cr.execute(DIRECT_MEMBER_SHOULD_NOT_BE_STATEMENT)
        self._recompute_partners_from_cursor()

    @api.model
    def _recompute_partners_from_cursor(self):
        """Recompute membership for all direct members."""
        max_recompute = 512
        cr = self.env.cr
        partner_ids = [rec[0] for rec in cr.fetchall()]
        if not partner_ids:
            _logger.debug(
                _("Found no records for recompute membership for query %s."), cr.query
            )
            return
        records_found = len(partner_ids)
        if records_found > max_recompute:
            _logger.info(
                _(
                    "Found %d records for recompute membership for query %s."
                    "WIll recompute %d records."
                ),
                records_found,
                cr.query,
                max_recompute,
            )
        else:
            _logger.debug(
                _("Found %d records for recompute membership for query %s."),
                records_found,
                cr.query,
            )
        partners = self.browse(partner_ids[:max_recompute])
        partners._compute_membership()
