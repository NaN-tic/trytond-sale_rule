# This file is part of the sale_rule module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime
from trytond.model import ModelView, ModelSQL, DeactivableMixin, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.exceptions import UserError
from trytond.modules.product import price_digits

CRITERIA = [
    ('untaxed_amount', 'Untaxed Amount'),
    ('tax_amount', 'Tax Amount'),
    ('total_amount', 'Total Amount'),
    ('total_products', 'Total Products'),
    ('product', 'Total Product Quantity'),
    ('account_category', 'Product Account Category'),
    ]
COMPARATORS = [
    ('equal', 'equals'),
    ('not_equal', 'not equal to'),
    ('greater_than', 'greater than'),
    ('greater_equal_than', 'greater or equal than'),
    ('less_than', 'less than'),
    ('less_equal_than', 'less or equal than'),
    ('multiple', 'multiple of'),
    ('not_multiple', 'not multiple of'),
    ]
ACTION_TYPES = [
    ('cart_discount_percentage', 'Discount % on Sub Total'),
    ('cart_base_discount_percentage', 'Discount % on Base'),
    ('cart_discount_fixed', 'Fixed amount'),
    ('stop_sale', 'Stop Sale'),
    ('get_product_free', 'Get X Product Free'),
    ]


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'
    add_rules = fields.Boolean('Add Rules', states={
            'readonly': Eval('state') != 'draft',
            }, depends=['state'],
        help='Apply rules when change draft to quotation.')
    coupon = fields.Char('Coupon')

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls._buttons.update({
                'apply_rules': {
                    'invisible': (
                        (Eval('state') != 'draft') | (~Eval('add_rules', False))),
                    },
                })

    @staticmethod
    def default_add_rules():
        User = Pool().get('res.user')
        user = User(Transaction().user)
        return user.shop.apply_rules if user.shop else True

    @fields.depends('_parent_shop.apply_rules')
    def on_change_shop(self):
        super(Sale, self).on_change_shop()
        if self.shop:
            self.add_rules = self.shop.apply_rules

    @classmethod
    def quote(cls, sales):
        cls.apply_rules(sales)
        cls.save(sales)
        super(Sale, cls).quote(sales)

    def apply_rule(self):
        'Apply Rule'
        pool = Pool()
        Rule = pool.get('sale.rule')
        Line = pool.get('sale.line')

        rules = Rule.get_rules(self)
        to_delete = [l for l in self.lines if l.action is not None]
        if to_delete:
            Line.delete(to_delete)

        lines = []
        for rule in rules:
            lines += rule.apply(self)
            if lines and rule.stop_further:
                break
        return lines

    @classmethod
    @ModelView.button
    def apply_rules(cls, sales):
        for sale in sales:
            if not sale.add_rules:
                continue
            sale.apply_rule()


class SaleRule(DeactivableMixin, ModelView, ModelSQL):
    'Sale Rule'
    __name__ = 'sale.rule'
    name = fields.Char('Description', required=True, translate=True)
    from_date = fields.DateTime('From Date')
    to_date = fields.DateTime('To Date')
    sequence = fields.Integer('Sequence')
    stop_further = fields.Boolean('Stop further checks', help='Avoids that '
        'the rest of rules are checked if this rule is applicable.')
    shop = fields.Many2One('sale.shop', 'Shop')
    category = fields.Many2One('party.category', 'Party Category')
    actions = fields.One2Many('sale.rule.action', 'rule', 'Actions')
    conditions = fields.One2Many('sale.rule.condition', 'rule', 'Conditions')
    quantifier = fields.Selection([
            ('all', 'All'),
            ('any', 'Any'),
            ], 'Quantifier',
        help='"All" requires that all conditions are true to apply this rule.'
            '\n"Any" applies this rule if any of the conditions is true.')
    coupon = fields.Char('Coupon')
    max_coupon = fields.Integer('Max Coupon')
    max_party_coupon = fields.Integer('Max Coupon per Party')

    @classmethod
    def __setup__(cls):
        super(SaleRule, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @staticmethod
    def default_quantifier():
        return 'all'

    @classmethod
    def _rules_domain(cls, sale):
        today = datetime.today()

        domain = [
            ['OR',
                ('from_date', '<=', today),
                ('from_date', '=', None),
                ],
            ['OR',
                ('to_date', '>=', today),
                ('to_date', '=', None),
                ],
            ['OR',
                ('shop', '=', sale.shop),
                ('shop', '=', None),
                ],
            ]
        if sale.party:
            domain.append(['OR',
                ('category', 'in', sale.party.categories),
                ('category', '=', None),
                ])
        return domain

    @classmethod
    def get_rules(cls, sale):
        return cls.search(cls._rules_domain(sale))

    def apply_actions(self, sale):
        lines = []
        for action in self.actions:
            l = action.apply(sale)
            if Transaction().context.get('apply_rule', True):
                l.save()
            lines.append(l)
        return lines

    def meet_conditions(self, sale):
        if not self.coupon_valid(sale):
            return False
        if self.quantifier == 'any':
            return any([c.evaluate(sale) for c in self.conditions])
        return all([c.evaluate(sale) for c in self.conditions])

    def coupon_valid(self, sale):
        Sale = Pool().get('sale.sale')

        if self.coupon and self.coupon != sale.coupon:
            return False

        sales = Sale.search([
                ('coupon', '=', self.coupon),
                ])
        if self.max_coupon and self.max_coupon < len(sales):
            return False
        if (self.max_party_coupon
            and self.max_party_coupon < len(
                [s for s in sales if s.party == sale.party])):
            return False
        return True

    def apply(self, sale):
        applicable = self.meet_conditions(sale)
        lines = []
        if applicable:
            lines = self.apply_actions(sale)
        return lines

    def checkout_rules(self, sale):
        if self.meet_conditions(sale):
            return [a.apply(sale) for a in self.actions]


class SaleRuleAction(ModelSQL, ModelView):
    'Sale Rule Action'
    __name__ = 'sale.rule.action'
    rule = fields.Many2One('sale.rule', 'Rule', required=True,
        ondelete='CASCADE')
    sequence = fields.Integer('Sequence')
    action_type = fields.Selection(ACTION_TYPES, 'Action', required=True)
    product = fields.Many2One('product.product', 'Product',
        states={
            'required': Eval('action_type') != 'stop_sale',
            'invisible': Eval('action_type') == 'stop_sale',
            },
        depends=['action_type'])
    quantity = fields.Numeric('Quantity',
        states={
            'required': Eval('action_type') != 'stop_sale',
            'invisible': Eval('action_type') == 'stop_sale',
            },
        digits=price_digits, depends=['action_type'])
    comment = fields.Text('Comment', translate=True)

    @classmethod
    def __setup__(cls):
        super(SaleRuleAction, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    def get_rec_name(self, name):
        for selection in self._fields['action_type'].selection:
            if self.action_type == selection[0]:
                return selection[1]

    def get_default_sale_line(self, sale):
        SaleLine = Pool().get('sale.line')

        line = SaleLine()
        line.sale = sale
        line.unit = self.product.template.default_uom
        line.quantity = 1
        line.product = self.product
        if self.comment:
            line.description = self.comment
        if hasattr(line, 'party'):
            line.party = sale.party
        line.type = 'line'
        line.sequence = 9999
        line.on_change_product()
        line.action = self
        return line

    def apply_stop_sale(self, sale):
        raise UserError(gettext('sale_rule.sale_forbidden',
            message=self.comment))

    def apply_cart_discount_percentage(self, sale):
        line = self.get_default_sale_line(sale)
        line.unit_price = -(sale.total_amount * self.quantity / 100)
        if hasattr(line, 'gross_unit_price'):
            line.gross_unit_price = line.unit_price
        line.amount = line.on_change_with_amount()
        return line

    def apply_cart_base_discount_percentage(self, sale):
        line = self.get_default_sale_line(sale)
        line.unit_price = -(sale.untaxed_amount * self.quantity / 100)
        if hasattr(line, 'gross_unit_price'):
            line.gross_unit_price = line.unit_price
        line.amount = line.on_change_with_amount()
        return line

    def apply_cart_discount_fixed(self, sale):
        line = self.get_default_sale_line(sale)
        line.unit_price = -self.quantity
        if hasattr(line, 'gross_unit_price'):
            line.gross_unit_price = line.unit_price
        line.amount = line.on_change_with_amount()
        return line

    def apply_get_product_free(self, sale):
        line = self.get_default_sale_line(sale)
        line.quantity = self.quantity
        line.unit_price = 0
        if hasattr(line, 'gross_unit_price'):
            line.gross_unit_price = line.unit_price
        line.amount = line.on_change_with_amount()
        return line

    def apply(self, sale):
        return getattr(self, 'apply_%s' % self.action_type)(sale)

class SaleRuleCondition(ModelSQL, ModelView):
    'Sale Rule Condition'
    __name__ = 'sale.rule.condition'
    rule = fields.Many2One('sale.rule', 'Rule', required=True,
        ondelete='CASCADE')
    sequence = fields.Integer('Sequence')
    stop_further = fields.Boolean('Stop further checks')
    criteria = fields.Selection(CRITERIA, 'Criteria', required=True)
    quantity = fields.Numeric('Quantity', required=True, digits=price_digits)
    product = fields.Many2One('product.product', 'Product',
        states={
            'required': Eval('criteria') == 'product',
            'invisible': Eval('criteria') != 'product',
            },
        depends=['criteria'])
    account_category = fields.Many2One('product.category',
        'Product Account Category',
        states={
            'required': Eval('criteria') == 'account_category',
            'invisible': Eval('criteria') != 'account_category',
            },
        depends=['criteria'])
    condition = fields.Selection(COMPARATORS, 'Condition', required=True)

    @classmethod
    def __setup__(cls):
        super(SaleRuleCondition, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @staticmethod
    def default_condition():
        return 'equal'

    @staticmethod
    def default_stop_further():
        return False

    def evaluate(self, sale):
        return getattr(self, 'evaluate_%s' % self.criteria)(sale)

    def evaluate_amount(self, sale):
        amount = getattr(sale, self.criteria)
        return self.apply_comparison(amount)

    def evaluate_untaxed_amount(self, sale):
        return self.evaluate_amount(sale)

    def evaluate_tax_amount(self, sale):
        return self.evaluate_amount(sale)

    def evaluate_total_amount(self, sale):
        return self.evaluate_amount(sale)

    def evaluate_sum(self, sale):
        quantity = sum([l.quantity for l in sale.lines
            if getattr(l, self.criteria) == getattr(self, self.criteria)
                and l.quantity])
        return self.apply_comparison(quantity)

    def evaluate_total_products(self, sale):
        quantity = sum([l.quantity for l in sale.lines if l.quantity])
        return self.apply_comparison(quantity)

    def evaluate_product(self, sale):
        return self.evaluate_sum(sale)

    def evaluate_account_category(self, sale):
        pool = Pool()
        Template = pool.get('product.template')
        templates = Template.search([
                (self.criteria, '=', getattr(self, self.criteria)),
                ])
        quantity = sum([l.quantity for l in sale.lines
                if l.product.template in templates if l.quantity])
        return self.apply_comparison(quantity)

    def apply_comparison(self, value):
        return getattr(self, 'apply_%s' % self.condition)(value)

    def apply_equal(self, value):
        return eval('%s == %s' % (value, self.quantity))

    def apply_not_equal(self, value):
        return eval('%s != %s' % (value, self.quantity))

    def apply_greater_than(self, value):
        return eval('%s > %s' % (value, self.quantity))

    def apply_greater_equal_than(self, value):
        return eval('%s >= %s' % (value, self.quantity))

    def apply_less_than(self, value):
        return eval('%s < %s' % (value, self.quantity))

    def apply_less_equal_than(self, value):
        return eval('%s <= %s' % (value, self.quantity))

    def apply_multiple(self, value):
        return eval('%s %s %s == 0' % (value, '%', self.quantity))

    def apply_not_multiple(self, value):
        return eval('%s %s %s != 0' % (value, '%', self.quantity))


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'
    action = fields.Many2One('sale.rule.action', 'Rule Action')
