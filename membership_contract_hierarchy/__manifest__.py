# -*- coding: utf-8 -*-
# Copyright 2017 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Membership contract hierarchy',
    'version': '10.0.1.0.0',
    'category': 'Customer Relationship Management',
    'author': 'Therp BV, '
              'Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'summary': 'Partner will be a member if higher up partner is member.',
    'depends': [
        'membership_contract',
        'partner_multi_relation_hierarchy',
    ],
    'data': [],
    'auto_install': True,
    'installable': True,
}
