import datetime
import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import create_chart, get_accounts
from trytond.modules.account_invoice.tests.tools import create_payment_term
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.modules.sale_shop.tests.tools import create_shop
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules, set_user


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install sale_rule
        activate_modules('sale_rule')

        # Create company
        _ = create_company()
        company = get_company()

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create customer
        Party = Model.get('party.party')
        customer = Party(name='Customer')
        customer.save()

        # Create account categories
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        # Create products
        ProductUom = Model.get('product.uom')
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        template = ProductTemplate()
        template.name = 'Product'
        template.default_uom = unit
        template.type = 'goods'
        template.salable = True
        template.lead_time = datetime.timedelta(0)
        template.list_price = Decimal('20')
        template.account_category = account_category
        template.save()
        product1 = Product()
        product1.template = template
        product1.cost_price = Decimal('8')
        product1.save()
        product2 = Product()
        product2.cost_price = Decimal('8')
        product2.template = template
        product2.save()

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create Product Price List
        ProductPriceList = Model.get('product.price_list')
        price_list = ProductPriceList(name='Price List', price='list_price')
        price_list_line = price_list.lines.new()
        price_list_line.formula = 'unit_price'
        price_list.save()

        # Create Sale Shop
        shop = create_shop(payment_term, price_list)
        shop.save()

        # Save Sale Shop User
        User = Model.get('res.user')
        user, = User.find([])
        user.shops.append(shop)
        user.shop = shop
        user.save()
        set_user(user)

        # Create Rule
        Rule = Model.get('sale.rule')
        RuleCondition = Model.get('sale.rule.condition')
        RuleAction = Model.get('sale.rule.action')
        rule = Rule(name='Buy 2 Get 1 Free!')
        rule.save()
        condition = RuleCondition()
        condition.criteria = 'product'
        condition.product = product1
        condition.condition = 'greater_equal_than'
        condition.quantity = Decimal('2.0')
        condition.rule = rule
        condition.save()
        action = RuleAction()
        action.action_type = 'get_product_free'
        action.product = product1
        action.quantity = Decimal('1.0')
        action.comment = 'Buy 2 Get 1 Free!'
        action.rule = rule
        action.save()

        # Sale enough products for rule
        Sale = Model.get('sale.sale')
        sale = Sale()
        sale.shop = shop
        sale.party = customer
        sale.payment_term = payment_term
        sale_line = sale.lines.new()
        sale_line.product = product1
        sale_line.quantity = 2
        sale_line = sale.lines.new()
        sale_line.product = product2
        sale_line.quantity = 2
        sale.save()
        sale.click('quote')
        self.assertEqual(len(sale.lines), 3)

        # Go back to draft reset the original price
        sale.click('draft')

        # Sale not enough products for rule
        sale = Sale()
        sale.shop = shop
        sale.party = customer
        sale.payment_term = payment_term
        sale_line = sale.lines.new()
        sale_line.product = product1
        sale_line.quantity = 1
        sale_line = sale.lines.new()
        sale_line.product = product2
        sale_line.quantity = 2
        sale.save()
        sale.click('quote')
        self.assertEqual(len(sale.lines), 2)
