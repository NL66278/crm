# -*- coding: utf-8 -*-
# Copyright 2017-2018 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=protected-access
from odoo import api, models


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
    def _is_member(self):
        """Check associate membership.

        Can exist alongside personal membership.
        """
        self.ensure_one()
        self.env.invalidate_all()  # Prevent stale partner_above_ids.
        super_member = super(ResPartner, self)._is_member()
        # Check all partners above us for membership.
        for partner_above in self.partner_above_ids:
            associate = partner_above.partner_above_id
            if not associate.membership:
                continue
            # We have a member above us, so we are member too.
            # Only write real changes
            if not self.membership or self.associate_member != associate:
                super(ResPartner, self).write(
                    {"membership": True, "associate_member": associate.id}
                )
            return True
        # If we get here, we are not member through hierarchy.
        super(ResPartner, self).write({"associate_member": False})
        return super_member
