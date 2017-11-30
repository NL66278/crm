.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===================
membership_contract
===================

This module is an alternative to the standard Odoo membership module. This
module should not be installed at the same time as the Odoo module and
is therefore also incompatible with the oca membership modules in the
vertical-association repository.

Unlike the membership module, this module regards a membership as a kind of
contract. This makes it fully compatible with recurring invoices as
provided by the oca contract module.

By defining membership as an attribute of a product, the normal price
mechanism of Odoo can be used.

An organisation or person can be a member, if it has a running valid
contractline for a membership product. No special handling is needed for the
status of the memebership.

A special feature of this module is that a membership product can be
associated with a pricelist. As long as a customer has a valid contractline
for a membership product, it will consider the prices computed through the
linked pricelist, and apply the special member price, if lower than the
standard price.

Usage
=====

To use this module, you must make sure that the Odoo membership is
uninstalled.

After that install the module in the normal way.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/{repo_id}/{branch}

Known issues / Roadmap
======================

None at present.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/{project_repo}/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Images
------

* Odoo Community Association: `Icon <https://odoo-community.org/logo.png>`_.

Contributors
------------

* Ronald Portier <ronald@therp.nl> (https://therp.nl)

Do not contact contributors directly about support or help with technical issues.

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
