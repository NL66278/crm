# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# pylint: disable=protected-access
from odoo import api, models


class ResPartnerRelationType(models.Model):
    """Deals with changes in membership, because of changes in hierarchy.

    1. If a relationship becomes equal, existing members through an
       association might loose their membership.
    2. If a relationship becomes hierarchical, partners might become
       members through association.
    Creating a new relationship.type can not have an effect on existing
    relations, therefore no action on create() is needed.
    """

    _inherit = "res.partner.relation.type"

    @api.multi
    def write(self, vals):
        """Membership only changes when hierarchy changes."""
        recompute_membership = False
        for this in self:
            if "hierarchy" in vals and vals["hierarchy"] != this.hierarchy:
                recompute_membership = True
        result = super(ResPartnerRelationType, self).write(vals)
        if recompute_membership:
            self.env["res.partner"].cron_compute_membership()
        return result

    @api.multi
    def unlink(self):
        """Unlink might mean loss of associated membership."""
        recompute_membership = False
        for this in self:
            if this.hierarchy in ("left", "right"):
                recompute_membership = True
        result = super(ResPartnerRelationType, self).unlink()
        if recompute_membership:
            self.env["res.partner"].cron_compute_membership()
        return result
