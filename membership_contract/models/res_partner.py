# -*- coding: utf-8 -*-
# Copyright 2017-2020 Therp BV <https://therp.nl>.
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

# Correct members that have no direct or associate membership.
MEMBERSHIP_SHOULD_NOT_HAVE_STATEMENT = """\
UPDATE res_partner SET membership = false
 WHERE not direct_member AND associate_member IS NULL AND membership
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
-- Partner with current contract should be direct member.
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
-- Partner without current contract should NOT be direct member.
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
        records_todo = len(self)
        new_member_count = 0
        removed_member_count = 0
        if records_todo > 0:
            _logger.info(_("Recomputing membership for %d partners"), records_todo)
        for this in self:
            _logger.debug(_("Recomputing membership for %s"), this.display_name)
            vals = {}
            membership = this._is_member(vals)
            if membership != this.membership:
                if membership:
                    new_member_count += 1
                    _logger.info(_("%s is now a member"), this.display_name)
                else:
                    removed_member_count += 1
                    _logger.info(_("%s is no longer a member"), this.display_name)
                vals["membership"] = membership
            if vals:
                this.write(vals)
                if "membership" in vals:
                    this.membership_change_trigger()
        if records_todo > 0:
            _logger.info(
                _("Recomputing membership added %d members, removed %d"),
                new_member_count,
                removed_member_count,
            )

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
        self._recompute_membership()

    @api.model
    def _recompute_membership(self):
        """Recompute membership for all direct members.

        We create a separate cursor to commit each step separately.
        """
        # Make our own cursor
        new_cr = registry(self._cr.dbname).cursor()
        # Start off by getting rid of NULL values
        new_cr.execute(NO_NULL_MEMBERSHIP_STATEMENT)
        new_cr.commit()
        new_cr.execute(NO_NULL_DIRECT_MEMBER_STATEMENT)
        new_cr.commit()
        # Members that are not direct_member, and not through associate,
        # should not be member.
        new_cr.execute(MEMBERSHIP_SHOULD_NOT_HAVE_STATEMENT)
        new_cr.commit()
        new_cr.close()
        # Now handle those that should be direct member
        self.env.cr.execute(DIRECT_MEMBER_SHOULD_BE_STATEMENT)
        self._recompute_partners_from_cursor()
        # Now handle those that should no longer be direct member
        self.env.cr.execute(DIRECT_MEMBER_SHOULD_NOT_BE_STATEMENT)
        self._recompute_partners_from_cursor()

    @api.model
    def _recompute_partners_from_cursor(self):
        """Recompute membership for all direct members."""
        max_recompute = 256
        cr = self.env.cr
        query = cr.query  # Save as logging translation will result in new queries.
        partner_ids = [rec[0] for rec in cr.fetchall()]
        if not partner_ids:
            _logger.debug(
                _("Found no records for recompute membership for query:\n%s."), query
            )
            return
        records_found = len(partner_ids)
        if records_found > max_recompute:
            _logger.info(
                _(
                    "Found %d records for recompute membership for query:\n%s."
                    "WIll recompute %d records."
                ),
                records_found,
                query,
                max_recompute,
            )
        else:
            _logger.debug(
                _("Found %d records for recompute membership for query:\n%s."),
                records_found,
                query,
            )
        self._recompute_partners_one_by_one(partner_ids[:max_recompute])

    @api.model
    def _recompute_partners_one_by_one(self, partner_ids):
        """Recompute members one by one, in separate cursor.

        Recomputing partners one by one will prevent problems where the whole
        update is cancelled and rolled back, because of problems with a single
        partner having been changed in another job/thread, or because of a locking
        problem on a single partner.
        to prevent a problem on
        """
        new_cr = registry(self._cr.dbname).cursor()
        new_self = self.with_env(self.env(cr=new_cr))
        errors = 0
        for partner_id in partner_ids:
            partner = new_self.browse([partner_id])
            try:
                partner._compute_membership()
                new_cr.commit()
            except Exception:  # pylint: disable=broad-except
                _logger.exception(
                    _("Error updating membership voor partner %s with id %d."),
                    partner.display_name,
                    partner_id,
                )
                new_cr.rollback()
                errors += 1
                if errors >= 16:
                    _logger.error(
                        _("Too many errors in updating partners, cancelling operation")
                    )
                    break
        new_cr.close()
