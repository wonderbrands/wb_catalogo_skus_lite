# -*- coding: utf-8 -*-
from odoo import models, fields

class ProdEstatus(models.Model):
    _name = 'product.estatus'
    _description = 'Estatus de producto'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Char(string='Secuencia asignada')

class ProdSubestatus(models.Model):
    _name = 'product.subestatus'
    _description = 'Subestatus de producto'

    name = fields.Char(string='Nombre', required=True)
    subsequence = fields.Char(string='Subsecuencia asignada')
