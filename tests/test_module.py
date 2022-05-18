
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from trytond.modules.sale_shop.tests import SaleShopCompanyTestMixin
from trytond.tests.test_tryton import ModuleTestCase


class SaleRuleTestCase(SaleShopCompanyTestMixin, ModuleTestCase):
    'Test SaleRule module'
    module = 'sale_rule'
    extras = ['sale_pos', 'sale_discount']


del ModuleTestCase
