# -*- coding: utf-8 -*-
# Copyright 2018 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models


class ResPartnerRelation(models.Model):
    _inherit = 'res.partner.relation'

    @api.multi
    def _get_partners_affected(self, vals=None):
        partner_ids = set()
        vals = vals or {}
        if 'left_partner_id' in vals:
            partner_ids.add(vals['left_partner_id'])
        if 'right_partner_id' in vals:
            partner_ids.add(vals['right_partner_id'])
        for this in self:
            partner_ids.add(this.left_partner_id.id)
            partner_ids.add(this.right_partner_id.id)
        partner_model = self.env['res.partner']
        return partner_model.browse(list(partner_ids))

    @api.model
    def create(self, vals):
        result = super(ResPartnerRelation, self).create(vals)
        partners = result._get_partners_affected()
        for partner in partners:
            partner._compute_membership()
        return result

    @api.multi
    def write(self, vals):
        partners = self._get_partners_affected(vals)
        result = super(ResPartnerRelation, self).write(vals)
        for partner in partners:
            partner._compute_membership()
        return result

    @api.multi
    def unlink(self):
        partners = self._get_partners_affected()
        result = super(ResPartnerRelation, self).unlink()
        for partner in partners:
            partner._compute_membership()
        return result
