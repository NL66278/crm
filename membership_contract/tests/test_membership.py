# -*- coding: utf-8 -*-
# Copyright 2018 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.tests import common


class TestMembership(common.SavepointCase):

    post_install = True
    at_install = False

    @classmethod
    def setUpClass(cls):
        super(TestMembership, cls).setUpClass()
        # Create some test partners
        partner_model = cls.env['res.partner']
        cls.partner_jan = partner_jan = partner_model.create({
            'name': 'Jan',
            'city': 'Amsterdam'})
        cls.partner_club = partner_club = partner_model.create({
            'name': 'The Club',
            'city': 'Rotterdam',
            'is_company': True})
        # Make sure a sale journal is present for tests
        sequence_model = cls.env['ir.sequence']
        contract_sequence = sequence_model.create({
            'company_id': cls.env.user.company_id.id,
            'code': 'contract',
            'name': 'contract sequence',
            'number_next': 1,
            'implementation': 'standard',
            'padding': 3,
            'number_increment': 1})
        journal_model = cls.env['account.journal']
        journal_model.create({
            'company_id': cls.env.user.company_id.id,
            'code': 'contract',
            'name': 'contract journal',
            'sequence_id': contract_sequence.id,
            'type': 'sale'})
        # Create products:
        cls.uom_unit = cls.env.ref('product.product_uom_unit')
        product_model = cls.env['product.product']
        cls.product_club_membership = \
            product_club_membership = product_model.create({
                'name': 'Test club_membership',
                'type': 'service',
                'uom_id': cls.uom_unit.id,
                'uom_po_id': cls.uom_unit.id})
        cls.product_personal_membership = \
            product_personal_membership = product_model.create({
                'name': 'Test personal_membership',
                'type': 'service',
                'membership': True,
                'uom_id': cls.uom_unit.id,
                'uom_po_id': cls.uom_unit.id})
        cls.product_odoo_book = product_model.create({
            'name': 'Odoo for dummies',
            'type': 'product',
            'list_price': 75.0,
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id})
        # Create contract that will be membership from the beginning:
        contract_model = cls.env['account.analytic.account']
        line_model = cls.env['account.analytic.invoice.line']
        cls.contract_jan = contract_jan = contract_model.create({
            'name': 'Test Contract Jan',
            'partner_id': partner_jan.id,
            'recurring_invoices': True,
            'date_start': '2016-02-15',
            'recurring_next_date': '2016-02-29'})
        cls.line_personal_membership = line_model.create({
            'analytic_account_id': contract_jan.id,
            'product_id': product_personal_membership.id,
            'name': 'Personal membership',
            'quantity': 1,
            'uom_id': product_personal_membership.uom_id.id,
            'price_unit': 25.0,
            'discount': 50.0})
        # Create contract for club_membership.
        #  Product will be changed to membership:
        cls.contract_club = contract_club = contract_model.create({
            'name': 'Test Contract Club',
            'partner_id': partner_club.id,
            'recurring_invoices': True,
            'date_start': '2016-02-15',
            'recurring_next_date': '2016-02-29'})
        cls.line_club_membership = line_model.create({
            'analytic_account_id': contract_club.id,
            'product_id': product_club_membership.id,
            'name': 'Club membership',
            'quantity': 1,
            'uom_id': product_club_membership.uom_id.id,
            'price_unit': 3025.0,
            'discount': 10.0})

    def test_contract(self):
        """Test creation of contract line for membership."""
        self.assertTrue(self.line_personal_membership.membership)
        self.assertEqual(
            self.partner_jan.membership_line_ids[0],
            self.line_personal_membership)
        self.assertTrue(self.partner_jan.membership)

    def test_product_change(self):
        """Test change of product to membership product."""
        # Test initial condition of no membership
        self.assertFalse(self.line_club_membership.membership)
        self.assertFalse(bool(self.partner_club.membership_line_ids))
        # Change product to give membership
        self.product_club_membership.write({'membership': True})
        self.assertTrue(self.line_club_membership.membership)
        self.assertEqual(
            self.partner_club.membership_line_ids[0],
            self.line_club_membership)
        # Change back to False.
        self.product_club_membership.write({'membership': False})
        self.assertFalse(self.line_club_membership.membership)
        self.assertFalse(self.partner_club.membership)

    def test_contract_expiration(self):
        """Test loss of membership, if contract expires."""
        self.contract_jan.write({'date_end': '2017-12-31'})
        self.assertEqual(
            self.line_personal_membership.date_end, '2017-12-31')
        self.assertFalse(self.partner_jan.membership)
