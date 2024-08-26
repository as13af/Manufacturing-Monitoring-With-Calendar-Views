{
    'name': 'Custom Calendar View',
    'version': '1.0',
    'summary': 'Custom Calendar App to Maximize Products!',
    'description': 'A standalone app to display custom calendar with additional information',
    'author': 'Ali Shidqie AL Faruqi',
    'depends': ['base' ,'mrp', 'sale', 'purchase', 'stock', 'product', ],
    'data': [
        'views\custom_calendar.xml',
        'security\ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
}
