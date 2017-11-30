# -*- coding: utf-8 -*-
# Copyright 2017-2018 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def membership_change_trigger(self):
        """Compute membership for members immediately below this one."""
        hierarchy_model = self.env['res.partner.relation.hierarchy']
        for this in self:
            partners_below = hierarchy_model.search([
                ('partner_above_id', '=', this.id),
                ('level', '=', 1)])
            for partner_below in partners_below:
                partner_below.partner_below_id._compute_membership()

    @api.multi
    def _compute_membership(self):
        # First compute direct membership in super.
        self.env.invalidate_all()  # Prevent stale partner_above_ids.
        super(ResPartner, self)._compute_membership()
        for this in self:
            if this.membership and not this.associate_member:
                # direct member.
                continue
            save_membership = this.membership
            membership = False
            # Might still be member through partner above
            for partner_above in this.partner_above_ids:
                associate = partner_above.partner_above_id
                if not associate.membership:
                    continue
                membership = True
                # Only write real changes
                if not this.membership or \
                        this.associate_member != associate:
                    super(ResPartner, this).write({
                        'membership': True,
                        'associate_member': associate.id})
                    break
            if not membership and this.membership:
                super(ResPartner, this).write({
                    'membership': False,
                    'associate_member': False})
            if membership != save_membership:
                this.membership_change_trigger()
