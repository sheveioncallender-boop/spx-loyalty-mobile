{
    'name': 'SPX Loyalty Mobile Connector',
    'version': '19.0.1.2.0',
    'summary': 'Customer mobile access to existing Odoo loyalty and eCommerce',
    'author': 'SPXCORP LTD',
    'license': 'LGPL-3',
    'depends': ['website_sale_loyalty', 'pos_loyalty', 'portal', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/mobile_views.xml',
    ],
    'installable': True,
    'application': False,
}
