#This file is part sale_rule module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['SaleShop']


class SaleShop(metaclass=PoolMeta):
    __name__ = 'sale.shop'
    apply_rules = fields.Boolean('Apply Rules',
        help='Apply rules when change draft to quotation.')

    @staticmethod
    def default_apply_rules():
        return True
