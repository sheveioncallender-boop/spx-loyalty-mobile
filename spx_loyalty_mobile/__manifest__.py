{
    'name': "Jenny's Rewards",
    'version': '19.0.3.0.4',
    'summary': "Jenny's customer cards, loyalty, messages and mobile app",
    'author': 'SPXCORP LTD',
    'license': 'LGPL-3',
    'depends': ['website_sale_loyalty', 'pos_loyalty', 'pos_restaurant', 'portal', 'mail', 'auth_signup'],
    'data': [
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/mobile_views.xml',
        'views/onboarding_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'spx_loyalty_mobile/static/src/home/home.js',
            'spx_loyalty_mobile/static/src/home/home.xml',
            'spx_loyalty_mobile/static/src/home/home.css',
        ],
    },
    'post_init_hook': 'preserve_existing_members',
    'installable': True,
    'application': True,
}
