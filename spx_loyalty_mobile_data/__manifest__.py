{
    'name': "Jenny's Customer App Data",
    'version': '19.0.4.3.0',
    'summary': 'Retains customer app settings and history when the connector is removed',
    'author': 'SPXCORP LTD',
    'license': 'LGPL-3',
    'depends': ['website_sale_loyalty', 'pos_loyalty', 'pos_restaurant', 'portal', 'mail', 'auth_signup'],
    'data': ['security/ir.model.access.csv', 'security/rules.xml'],
    'pre_init_hook': 'adopt_existing_data',
    'uninstall_hook': 'detach_mail_references',
    'installable': True,
    'application': False,
    'auto_install': False,
}
