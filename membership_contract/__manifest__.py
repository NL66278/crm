# -*- coding: utf-8 -*-
# Copyright 2017-2018 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Membership contract',
    'version': '10.0.1.0.0',
    'category': 'Customer Relationship Management',
    'author': 'Therp BV, '
              'Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'summary': 'Maintain membership contracts for your relations.',
    'depends': [
        'partner_noncommercial',
        'contract_line_extended',
        'web_m2x_options',
    ],
    'data': [
        'data/membership_cron.xml',
        'demo/product.xml',
        'views/product_template.xml',
        'views/res_partner.xml',
        'views/menu.xml',
    ],
    'auto_install': False,
    'installable': True,
}
