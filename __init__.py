# This file is part of the sale_rule module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import sale
from . import shop

def register():
    Pool.register(
        sale.Sale,
        sale.SaleRule,
        sale.SaleRuleAction,
        sale.SaleRuleCondition,
        sale.SaleLine,
        shop.SaleShop,
        module='sale_rule', type_='model')
