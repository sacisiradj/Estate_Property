{
    'name': 'E-State',
    'depends': [
        'account',
        'mail'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/estate.property.type.csv',

        'demo/demo_data.xml',

        'views/estate_property_views.xml',
        'views/estate_menus.xml',
    ],
    'license': 'LGPL-3',
}
