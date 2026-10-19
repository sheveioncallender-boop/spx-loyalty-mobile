{
    'name': "Jenny's Rewards - Native POS Checkout",
    'version': '19.0.1.0.3',
    'summary': 'Open the cashier-prepared native POS checkout from the customer app',
    'author': 'SPXCORP LTD',
    'license': 'LGPL-3',
    'depends': ['spx_loyalty_mobile', 'pos_online_payment', 'pos_loyalty'],
    'data': ['views/pos_order_views.xml'],
    'assets': {
        'point_of_sale._assets_pos': [
            'spx_loyalty_mobile_pos_payment/static/src/loyalty_handoff.js',
            'spx_loyalty_mobile_pos_payment/static/src/loyalty_completion.js',
        ],
    },
    'auto_install': True,
    'installable': True,
}


