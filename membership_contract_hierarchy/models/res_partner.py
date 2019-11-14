# -*- coding: utf-8 -*-
# Copyright 2017-2019 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=protected-access
from odoo import api, models


# Statement to determine wether partner should be associate member.
DETERMINE_ASSOCIATE_MEMBERSHIP_STATEMENT = """\
SELECT partner_above_id
 FROM res_partner_relation_hierarchy h
 JOIN res_partner above ON h.partner_above_id = above.id
 WHERE h.partner_below_id = %(partner_id)s
   AND above.direct_member
"""


MEMBERSHIP_SHOULD_HAVE_STATEMENT = """\
-- Should be member according to hierarchy
SELECT
    h.partner_below_id
 FROM res_partner_relation_hierarchy h
 JOIN res_partner above ON h.partner_above_id = above.id
 JOIN res_partner below ON h.partner_below_id = below.id
 WHERE above.membership
   AND (below.associate_member IS NULL OR NOT below.membership)
"""


MEMBERSHIP_SHOULD_NOT_HAVE_STATEMENT = """\
-- Should not be member according to hierarchy
WITH members_above AS (
 SELECT
    h.partner_above_id
 FROM res_partner_relation_hierarchy h
 JOIN res_partner above ON h.partner_above_id = above.id
 WHERE above.membership
)
SELECT p.id
 FROM res_partner p
 WHERE NOT p.associate_member IS NULL
   AND p.associate_member NOT IN (SELECT partner_above_id FROM members_above)
"""


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.multi
    def membership_change_trigger(self):
        """Compute membership for members immediately below this one."""
        super(ResPartner, self).membership_change_trigger()
        hierarchy_model = self.env["res.partner.relation.hierarchy"]
        for this in self:
            partners_below = hierarchy_model.search(
                [("partner_above_id", "=", this.id), ("level", "=", 1)]
            )
            for partner_below in partners_below:
                partner_below.partner_below_id._compute_membership()

    @api.multi
    def _is_member(self, vals):
        """Check associate membership.

        Can exist alongside personal membership.
        """
        self.ensure_one()
        super_member = super(ResPartner, self)._is_member(vals)
        self.env.cr.execute(
            DETERMINE_ASSOCIATE_MEMBERSHIP_STATEMENT, {"partner_id": self.id}
        )
        # resultset should contain zero rows (no member above) or one.
        try:
            row = self.env.cr.fetchone()
            associate_member_id = row[0] if row else False
        except Exception:  # pylint: disable=broad-except
            associate_member_id = False
        # Only write real changes
        if associate_member_id != self.associate_member.id:
            vals["associate_member"] = associate_member_id
        if associate_member_id:
            return True
        # If we get here, we are not member through hierarchy.
        return super_member

    @api.model
    def cron_compute_membership(self):
        """Recompute membership also for associate members."""
        # First recompute direct members.
        super(ResPartner, self).cron_compute_membership()
        # Check for new associate members.
        self.env.cr.execute(MEMBERSHIP_SHOULD_HAVE_STATEMENT)
        self.recompute_partners_from_cursor()
        # Check for deprecated associate members.
        self.env.cr.execute(MEMBERSHIP_SHOULD_NOT_HAVE_STATEMENT)
        self.recompute_partners_from_cursor()
