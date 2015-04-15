# This file is part of the sale_rule module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval

__all__ = ['Sale', 'SaleRule', 'SaleRuleAction', 'SaleRuleCondition',
    'SaleLine']
__metaclass__ = PoolMeta
CRITERIA = [
    ('untaxed_amount', 'Untaxed Amount'),
    ('tax_amount', 'Tax Amount'),
    ('total_amount', 'Total Amount'),
    ('total_products', 'Total Products'),
    ('product', 'Total Product Quantity'),
    ('category', 'Total Product Category Quantity'),
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
    ('cart_discoutn_fixed', 'Fixed amount on Sub Total'),
    ('stop_sale', 'Stop Sale'),
    ('get_product_free', 'Get X Product Free'),
    ]


class Sale:
    __name__ = 'sale.sale'

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls._buttons.update({
                'apply_rules': {
                    'invisible': Eval('state') != 'draft',
                    },
                })

    @classmethod
    def quote(cls, sales):
        super(Sale, cls).quote(sales)
        cls.apply_rules(sales)

    @classmethod
    def apply_rules(cls, sales):
        pool = Pool()
        Line = pool.get('sale.line')
        Rule = pool.get('sale.rule')
        today = datetime.today()
        for sale in sales:
            rules = Rule.search([
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
                    ['OR',
                        ('category', 'in', sale.party.categories),
                        ('category', '=', None),
                        ],
                    ])
            Line.delete([l for l in sale.lines if l.action is not None])
            Rule.apply_rules(rules, sale)


class SaleRule(ModelView, ModelSQL):
    'Sale Rule'
    __name__ = 'sale.rule'
    name = fields.Char('Description', required=True)
    active = fields.Boolean('Active')
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

    @classmethod
    def __setup__(cls):
        super(SaleRule, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_quantifier():
        return 'all'

    def apply_actions(self, sale):
        for action in self.actions:
            action.apply(sale)

    def meet_conditions(self, sale):
        if self.quantifier == 'any':
            return any([c.evaluate(sale) for c in self.conditions])
        return all([c.evaluate(sale) for c in self.conditions])

    def apply_rule(self, sale):
        applicable = self.meet_conditions(sale)
        if applicable:
            self.apply_actions(sale)
        return applicable

    @classmethod
    def apply_rules(cls, rules, sale):
        for rule in rules:
            applied = rule.apply_rule(sale)
            if applied and rule.stop_further:
                break


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
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'on_change_with_currency_digits')
    quantity = fields.Numeric('Quantity',
        states={
            'required': Eval('action_type') != 'stop_sale',
            'invisible': Eval('action_type') == 'stop_sale',
            },
        digits=(16, Eval('currency_digits', 2)),
        depends=['currency_digits', 'action_type'])
    comment = fields.Text('Comment', translate=True, required=True)

    @classmethod
    def __setup__(cls):
        super(SaleRuleAction, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))
        cls._error_messages.update({
                'sale_forbidden': ('You cannot make this sale because of %s.'),
                })

    @fields.depends('account')
    def on_change_with_currency_digits(self, name=None):
        return self.rule.shop and self.rule.shop.currency.digits or 2

    @fields.depends('rule')
    def on_change_action_type(self):
        res = {}
        if self.rule:
            res['currency_digits'] = (self.rule.shop
                and self.rule.shop.currency.digits or 2)
        return res

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
        line.description = self.comment
        line.party = sale.party
        line.type = 'line'
        line.sequence = 9999

        for key, value in line.on_change_product().iteritems():
            setattr(line, key, value)
        return line

    def apply_stop_sale(self, sale):
        self.raise_user_error('sale_forbidden',
            error_args=(self.comment,),
            )

    def apply_cart_discount_percentage(self, sale):
        line = self.get_default_sale_line(sale)
        line.unit_price = -(sale.total_amount * self.quantity / 100)
        return line

    def apply_cart_discoutn_fixed(self, sale):
        line = self.get_default_sale_line(sale)
        line.unit_price = -self.quantity
        return line

    def apply_get_product_free(self, sale):
        line = self.get_default_sale_line(sale)
        line.quantity = self.quantity
        line.unit_price = 0
        return line

    def apply(self, sale):
        line = getattr(self, 'apply_%s' % self.action_type)(sale)
        line.save()


class SaleRuleCondition(ModelSQL, ModelView):
    'Sale Rule Condition'
    __name__ = 'sale.rule.condition'
    rule = fields.Many2One('sale.rule', 'Rule', required=True,
        ondelete='CASCADE')
    sequence = fields.Integer('Sequence')
    stop_further = fields.Boolean('Stop further checks')
    criteria = fields.Selection(CRITERIA, 'Criteria', required=True)
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'on_change_with_currency_digits')
    quantity = fields.Numeric('Quantity',
        states={
            'required': True,
            },
        digits=(16, Eval('currency_digits', 2)),
        depends=['currency_digits'])
    product = fields.Many2One('product.product', 'Product',
        states={
            'required': Eval('criteria') == 'product',
            'invisible': Eval('criteria') != 'product',
            },
        depends=['criteria'])
    category = fields.Many2One('product.category', 'Product Category',
        states={
            'required': Eval('criteria') == 'category',
            'invisible': Eval('criteria') != 'category',
            },
        depends=['criteria'])
    condition = fields.Selection(COMPARATORS, 'Condition', required=True)

    @classmethod
    def __setup__(cls):
        super(SaleRuleCondition, cls).__setup__()
        cls._order.insert(0, ('sequence', 'ASC'))

    @fields.depends('account')
    def on_change_with_currency_digits(self, name=None):
        return self.rule.shop and self.rule.shop.currency.digits or 2

    @fields.depends('rule')
    def on_change_criteria(self):
        res = {}
        if self.rule:
            res['currency_digits'] = (self.rule.shop
                and self.rule.shop.currency.digits or 2)
        return res

    @staticmethod
    def default_condition():
        return 'equal'

    @staticmethod
    def default_stop_further():
        return False

    def evaluate(self, sale):
        return getattr(self, 'evaluate_%s' % self.criteria)(sale)

    def evaluate_amount(self, sale):
        Sale = Pool().get('sale.sale')
        amount = Sale.get_amount([sale], [self.criteria])
        return self.apply_comparison(amount[self.criteria][sale.id])

    def evaluate_untaxed_amount(self, sale):
        return self.evaluate_amount(sale)

    def evaluate_tax_amount(self, sale):
        return self.evaluate_amount(sale)

    def evaluate_total_amount(self, sale):
        return self.evaluate_amount(sale)

    def evaluate_sum(self, sale):
        quantity = sum([l.quantity for l in sale.lines
            if getattr(l, self.criteria) == getattr(self, self.criteria)])
        return self.apply_comparison(quantity)

    def evaluate_total_products(self, sale):
        quantity = sum([l.quantity for l in sale.lines])
        return self.apply_comparison(quantity)

    def evaluate_product(self, sale):
        return self.evaluate_sum(sale)

    def evaluate_category(self, sale):
        pool = Pool()
        Template = pool.get('product.template')
        templates = Template.search([
                (self.criteria, '=', getattr(self, self.criteria)),
                ])
        quantity = sum([l.quantity for l in sale.lines
                if l.product.template in templates])
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


class SaleLine:
    __name__ = 'sale.line'
    action = fields.Many2One('sale.rule.action', 'Rule Action')
