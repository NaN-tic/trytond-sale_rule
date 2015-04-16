# This file is part of the sale_rule module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .sale import *
from .shop import *

def register():
    Pool.register(
        Sale,
        SaleRule,
        SaleRuleAction,
        SaleRuleCondition,
        SaleLine,
        SaleShop,
        module='sale_rule', type_='model')
