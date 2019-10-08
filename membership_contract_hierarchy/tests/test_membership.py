# -*- coding: utf-8 -*-
# Copyright 2018-2019 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# pylint: disable=protected-access
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
        partner_model = cls.env["res.partner"]
        cls.partner_groningen_club = partner_model.create(
            {"name": "The Club in Groningen", "city": "Groningen", "is_company": True}
        )
        # Create a hierarchical relation between clubs and state clubs.
        relation_type_model = cls.env["res.partner.relation.type"]
        branch_type = relation_type_model.create(
            {
                "name": "has branch",
                "name_inverse": "is branch of",
                "contact_type_left": "c",
                "contact_type_right": "c",
                "hierarchy": "left",
            }
        )
        # Make the state club for Groningen a branch of the national club.
        relation_model = cls.env["res.partner.relation"]
        relation_model.create(
            {
                "type_id": branch_type.id,
                "left_partner_id": cls.partner_club.id,
                "right_partner_id": cls.partner_groningen_club.id,
            }
        )

    def test_contract(self):
        """Test creation of contract line for membership."""
        self.product_club_membership.write({"membership": True})
        # first test direct partner.
        self.assertTrue(self.line_club_membership.membership)
        self.assertEqual(
            self.partner_club.membership_line_ids[0], self.line_club_membership
        )
        self.partner_club._compute_membership()
        self.assertTrue(self.partner_club.membership)
        # Check wether hierarchy properly created.
        self.assertEqual(
            self.partner_club,
            self.partner_groningen_club.partner_above_ids[0].partner_above_id,
        )
        # then test underlying partner.
        self.assertTrue(self.partner_groningen_club.membership)
        self.assertEqual(
            self.partner_groningen_club.associate_member, self.partner_club
        )

    def test_product_change(self):
        """Test change of product to membership product."""
        # First change product to not imply membership.
        self.product_club_membership.write({"membership": False})
        self.assertFalse(self.line_club_membership.membership)
        self.partner_club._compute_membership()
        self.assertFalse(self.partner_club.membership)
        self.assertFalse(self.partner_groningen_club.membership)
        # And back to membership.
        self.product_club_membership.write({"membership": True})
        self.assertTrue(self.line_club_membership.membership)
        self.partner_club._compute_membership()
        self.assertTrue(self.partner_club.membership)
        self.assertTrue(self.partner_groningen_club.membership)

    def test_contract_expiration(self):
        """Test loss of membership, if contract expires."""
        self.contract_club.write({"date_end": "2017-12-31"})
        self.assertEqual(self.line_club_membership.date_end, "2017-12-31")
        self.partner_club._compute_membership()
        self.assertFalse(self.partner_club.membership)
        self.assertFalse(self.partner_groningen_club.membership)

    def test_hierarchy_changes(self):
        """Test changes in hierarchy."""
        # Setup two new partners and an at first equal relationship.
        partner_model = self.env["res.partner"]
        relation_type_model = self.env["res.partner.relation.type"]
        relation_model = self.env["res.partner.relation"]
        contract_model = self.env["account.analytic.account"]
        line_model = self.env["account.analytic.invoice.line"]
        # Create a press organisation.
        partner_odoo_times = partner_model.create(
            {"name": "The Odoo Times", "city": "Grand Rosier", "is_company": True}
        )
        # Create a journalist.
        partner_flying_reporter = partner_model.create(
            {"name": "The flying reporter", "city": "Brussels", "is_company": False}
        )
        #  Club product is changed to membership:
        self.product_club_membership.write({"membership": True})
        # Create contract for club_membership.
        contract_club = contract_model.create(
            {
                "name": "Test Contract Odoo Times",
                "partner_id": partner_odoo_times.id,
                "recurring_invoices": True,
                "date_start": "2019-02-15",
                "recurring_next_date": "2020-02-01",
            }
        )
        line_model.create(
            {
                "analytic_account_id": contract_club.id,
                "product_id": self.product_club_membership.id,
                "name": "Club membership",
                "quantity": 1,
                "uom_id": self.product_club_membership.uom_id.id,
                "price_unit": 3025.0,
                "discount": 10.0,
            }
        )
        # Create equal relation between press org, and journo.
        journalist_type = relation_type_model.create(
            {
                "name": "has journalist",
                "name_inverse": "is journalist for",
                "handle_invalid_onchange": "delete",
                "contact_type_left": "c",
                "contact_type_right": "p",
                "hierarchy": "equal",
            }
        )
        # Let the flying reporter work for the Odoo times.
        relation_model.create(
            {
                "type_id": journalist_type.id,
                "left_partner_id": partner_odoo_times.id,
                "right_partner_id": partner_flying_reporter.id,
            }
        )
        # Now odoo times should be member, but journalist not.
        self.assertTrue(partner_odoo_times.membership)
        self.assertFalse(partner_flying_reporter.membership)
        # Change relation type to hierarchical, journalist should be member.
        journalist_type.write({"hierarchy": "left"})
        self.assertTrue(partner_flying_reporter.membership)
        # Change relation type back, journalist no longer member.
        journalist_type.write({"hierarchy": "equal"})
        self.assertFalse(partner_flying_reporter.membership)
        # Change relation type to hierarchical, journalist should be member.
        journalist_type.write({"hierarchy": "left"})
        self.assertTrue(partner_flying_reporter.membership)
        # Delete relation type, journalist no longer member.
        journalist_type.unlink()
        self.assertFalse(partner_flying_reporter.membership)
