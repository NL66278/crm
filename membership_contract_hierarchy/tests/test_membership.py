# -*- coding: utf-8 -*-
# Copyright 2018 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.membership_contract.tests import test_membership


class TestMembershipHierarchy(test_membership.TestMembership):
    """Test membership through hierarchy.

    Use the same methods as in test for direct membership, but now test
    membership in underlying partner.
    """

    post_install = True
    at_install = False

    @classmethod
    def setUpClass(cls):
        super(TestMembershipHierarchy, cls).setUpClass()
        # Create a state branch for the club partner.
        partner_model = cls.env['res.partner']
        cls.partner_groningen_club = partner_model.create({
            'name': 'The Club in Groningen',
            'city': 'Groningen',
            'is_company': True})
        # Create a hierarchical relation between clubs and state clubs.
        relation_type_model = cls.env['res.partner.relation.type']
        branch_type = relation_type_model.create({
            'name': 'has branch',
            'name_inverse': 'is branch of',
            'contact_type_left': 'c',
            'contact_type_right': 'c',
            'hierarchy': 'left'})
        # Make the state club for Groningen a branch of the national club.
        relation_model = cls.env['res.partner.relation']
        relation_model.create({
            'type_id': branch_type.id,
            'left_partner_id': cls.partner_club.id,
            'right_partner_id': cls.partner_groningen_club.id})

    def test_contract(self):
        """Test creation of contract line for membership."""
        self.product_club_membership.write({'membership': True})
        # first test direct partner.
        self.assertTrue(self.line_club_membership.membership)
        self.assertEqual(
            self.partner_club.membership_line_ids[0],
            self.line_club_membership)
        self.assertTrue(self.partner_club.membership)
        # Check wether hierarchy properly created.
        self.assertEqual(
            self.partner_club,
            self.partner_groningen_club.partner_above_ids[0].partner_above_id)
        # then test underlying partner.
        self.assertTrue(self.partner_groningen_club.membership)
        self.assertEqual(
            self.partner_groningen_club.associate_member,
            self.partner_club)

    def test_product_change(self):
        """Test change of product to membership product."""
        # First change product to not imply membership.
        self.product_club_membership.write({'membership': False})
        self.assertFalse(self.line_club_membership.membership)
        self.assertFalse(self.partner_club.membership)
        self.assertFalse(self.partner_groningen_club.membership)
        # And back to membership.
        self.product_club_membership.write({'membership': True})
        self.assertTrue(self.line_club_membership.membership)
        self.assertTrue(self.partner_club.membership)
        self.assertTrue(self.partner_groningen_club.membership)

    def test_contract_expiration(self):
        """Test loss of membership, if contract expires."""
        self.contract_club.write({'date_end': '2017-12-31'})
        self.assertEqual(
            self.line_club_membership.date_end, '2017-12-31')
        self.assertFalse(self.partner_club.membership)
        self.assertFalse(self.partner_groningen_club.membership)
