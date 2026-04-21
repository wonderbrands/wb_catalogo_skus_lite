# -*- coding: utf-8 -*-
{
    'name': "Catálogo de SKUs WB",
    'summary': "Clasificación y navegación de productos por rol y estructura",
    'description': """
        Módulo de catálogo de productos (versión Lite).

        Agrega campos informativos de clasificación sobre productos:
        - Rol del Producto: Vendible (Yuju) / Almacenable Base / Consumible Interno
        - Estructura: Simple (1:1) / Combo Real / Multicaja

        No modifica flujos nativos de Odoo ni de Yuju.
        Todos los campos son informativos para reporteo y navegación.
    """,
    'author': "Sergio Guerrero",
    'category': 'Inventory',
    'version': '18.0.1.0',
    'depends': ['base', 'product', 'stock', 'mrp'],
    'application': True,
    'sequence': 10,
    'data': [
        'security/security.xml',
        'views/product_product_view.xml',
        'views/catalogue_search.xml',
    ],
    'post_init_hook': '_recompute_product_structure',
}