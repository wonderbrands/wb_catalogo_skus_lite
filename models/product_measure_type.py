# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductMeasureType(models.Model):
    _name = 'product.measure.type'
    _description = 'Tipo de Medida de Producto'

    name = fields.Char(string='Nombre', required=True)
    description = fields.Text(string='Descripción')
