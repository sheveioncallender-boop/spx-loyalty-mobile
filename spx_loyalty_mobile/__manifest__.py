{
    'name': "Jenny's Rewards",
    'version': '19.0.2.0.0',
    'summary': "Jenny's customer cards, loyalty, messages and mobile app",
    'author': 'SPXCORP LTD',
    'license': 'LGPL-3',
    'depends': ['website_sale_loyalty', 'pos_loyalty', 'pos_restaurant', 'portal', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/mobile_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'spx_loyalty_mobile/static/src/home/home.js',
            'spx_loyalty_mobile/static/src/home/home.xml',
            'spx_loyalty_mobile/static/src/home/home.css',
        ],
    },
    'installable': True,
    'application': True,
}
