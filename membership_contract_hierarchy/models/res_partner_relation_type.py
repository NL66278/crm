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
    def _get_partners_affected(self):
        """Affected partners are those with a changed or unlinked type."""
        self.ensure_one()
        partner_model = self.env["res.partner"]
        return partner_model.search([("relation_all_ids.type_id", "=", self.id)])

    @api.multi
    def write(self, vals):
        """Membership only changes when hierarchy changes."""
        partners = self.env["res.partner"].browse([])
        for this in self:
            if "hierarchy" in vals and vals["hierarchy"] != this.hierarchy:
                partners = partners | this._get_partners_affected()
        result = super(ResPartnerRelationType, self).write(vals)
        for partner in partners:
            partner._compute_membership()
        return result

    @api.multi
    def unlink(self):
        """Unlink might mean loss of associated membership."""
        partners = self.env["res.partner"].browse([])
        for this in self:
            if this.hierarchy in ("left", "right"):
                partners = partners | this._get_partners_affected()
        result = super(ResPartnerRelationType, self).unlink()
        for partner in partners:
            partner._compute_membership()
        return result
