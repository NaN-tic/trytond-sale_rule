==================
Sale Rule Scenario
==================

Imports::

    >>> import datetime
    >>> from decimal import Decimal
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_chart, \
    ...     get_accounts
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     create_payment_term

Configure::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install sale_rule::

    >>> Module = Model.get('ir.module')
    >>> module, = Module.find([
    ...         ('name', '=', 'sale_rule'),
    ...         ])
    >>> module.click('install')
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> revenue = accounts['revenue']

Create customer::

    >>> Party = Model.get('party.party')
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create products::

    >>> ProductUom = Model.get('product.uom')
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> template = ProductTemplate()
    >>> template.name = 'Product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.salable = True
    >>> template.lead_time = datetime.timedelta(0)
    >>> template.list_price = Decimal('20')
    >>> template.cost_price = Decimal('8')
    >>> template.account_revenue = revenue
    >>> template.save()
    >>> product1 = Product()
    >>> product1.template = template
    >>> product1.save()
    >>> product2 = Product()
    >>> product2.template = template
    >>> product2.save()

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create Product Price List::

    >>> ProductPriceList = Model.get('product.price_list')
    >>> product_price_list = ProductPriceList()
    >>> product_price_list.name = 'Price List'
    >>> product_price_list.company = company
    >>> product_price_list.save()

Create Sale Shop::

    >>> Shop = Model.get('sale.shop')
    >>> Sequence = Model.get('ir.sequence')
    >>> Location = Model.get('stock.location')
    >>> shop = Shop()
    >>> shop.name = 'Sale Shop'
    >>> warehouse, = Location.find([
    ...         ('type', '=', 'warehouse'),
    ...         ])
    >>> shop.warehouse = warehouse
    >>> shop.price_list = product_price_list
    >>> shop.payment_term = payment_term
    >>> sequence, = Sequence.find([
    ...         ('code', '=', 'sale.sale'),
    ...         ])
    >>> shop.sale_sequence = sequence
    >>> shop.sale_invoice_method = 'shipment'
    >>> shop.sale_shipment_method = 'order'
    >>> shop.save()

Save Sale Shop User::

    >>> user, = User.find([])
    >>> user.shops.append(shop)
    >>> user.shop = shop
    >>> user.save()

Create Rule::

    >>> Rule = Model.get('sale.rule')
    >>> RuleCondition = Model.get('sale.rule.condition')
    >>> RuleAction = Model.get('sale.rule.action')
    >>> rule = Rule(name='Buy 2 Get 1 Free!')
    >>> rule.save()
    >>> condition = RuleCondition()
    >>> condition.criteria = 'product'
    >>> condition.product = product1
    >>> condition.condition = 'greater_equal_than'
    >>> condition.quantity = Decimal('2.0')
    >>> condition.rule = rule
    >>> condition.save()
    >>> action = RuleAction()
    >>> action.action_type = 'get_product_free'
    >>> action.product = product1
    >>> action.quantity = Decimal('1.0')
    >>> action.comment = 'Buy 2 Get 1 Free!'
    >>> action.rule = rule
    >>> action.save()

Sale enough products for rule::

    >>> Sale = Model.get('sale.sale')
    >>> sale = Sale()
    >>> sale.shop = shop
    >>> sale.party = customer
    >>> sale.payment_term = payment_term
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product1
    >>> sale_line.quantity = 2
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product2
    >>> sale_line.quantity = 2
    >>> sale.save()
    >>> sale.click('quote')
    >>> len(sale.lines)
    3

Go back to draft reset the original price::

    >>> sale.click('draft')

Sale not enough products for rule::

    >>> sale = Sale()
    >>> sale.shop = shop
    >>> sale.party = customer
    >>> sale.payment_term = payment_term
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product1
    >>> sale_line.quantity = 1
    >>> sale_line = sale.lines.new()
    >>> sale_line.product = product2
    >>> sale_line.quantity = 2
    >>> sale.save()
    >>> sale.click('quote')
    >>> len(sale.lines)
    2
