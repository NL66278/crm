# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, fields, models


class CrmClaim(models.Model):
    _inherit = 'crm.claim'

    @api.onchange('delivery_id')
    def clean_selected(self):
        #If you change delivery delete all selected prds
        self.write({'product_selected_ids': [(5)]})

    @api.model
    def get_delivery_pickings(self):
        return self.env['stock.picking.type'].search(
            [('code', '=', 'outgoing')]
        ).ids

    delivery_id = fields.Many2one(
        'stock.picking',
        string='delivery on wich to make the claim',
        domain=lambda self: [(
            'picking_type_id', 'in', self.get_delivery_pickings())]
    )

    product_selected_ids = fields.Many2many(
        'product.template', 'claim_ids',
        string='Products Already in this Claim'
    )
