# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    measure_type_id = fields.Many2one(
        'product.measure.type',
        string='Tipo de medida',
        help='Establece el tipo de medida del producto',
        tracking=True
    )

    status = fields.Many2one('product.estatus', string='Estatus', help='Estatus del producto', tracking=True)
    substatus = fields.Many2one('product.subestatus', string='Subestatus', help='Subestatus del producto', tracking=True)
    status_sequence = fields.Char(related='status.sequence', string='Secuencia')
    status_subsequence = fields.Char(related='substatus.subsequence', string='Subsecuencia')

    # Enable tracking and definitions on packing measure fields
    packing_length = fields.Float(string='Largo empaque', help="Largo del Empaque en centimetros", tracking=True)
    packing_height = fields.Float(string='Alto empaque', help="Alto del Empaque en centimetros", tracking=True)
    packing_width = fields.Float(string='Ancho empaque', help="Ancho del Empaque en centimetros", tracking=True)
    packing_weight = fields.Float(string='Peso empaque', help="Peso del Empaque en centimetros", tracking=True)

    @api.onchange('packing_length', 'packing_height', 'packing_width', 'packing_weight')
    def _onchange_packing_measures_tracking(self):
        if hasattr(self, 'data_averages_updated_date'):
            self.data_averages_updated_date = fields.Datetime.now()
        if hasattr(self, 'data_averages_updated_by'):
            self.data_averages_updated_by = self.env.user.id

    def write(self, vals):
        packing_fields = {
            'packing_length': 'Largo empaque',
            'packing_height': 'Alto empaque',
            'packing_width': 'Ancho empaque',
            'packing_weight': 'Peso empaque',
        }
        old_vals = {}
        for rec in self:
            old_vals[rec.id] = {field: getattr(rec, field) for field in packing_fields if field in vals and hasattr(rec, field)}

        res = super(ProductTemplate, self).write(vals)

        for rec in self:
            changes = []
            if rec.id in old_vals:
                for field, label in packing_fields.items():
                    if field in vals:
                        old_v = old_vals[rec.id].get(field)
                        new_v = getattr(rec, field) if hasattr(rec, field) else None
                        if old_v != new_v:
                            changes.append(f"<li><b>{label}</b>: {old_v} &rarr; {new_v}</li>")
            if changes:
                user_name = self.env.user.name
                msg = f"<p><b>Medidas de empaque actualizadas por {user_name}:</b></p><ul>"
                msg += "".join(changes)
                msg += "</ul>"
                if hasattr(rec, 'message_post'):
                    rec.message_post(body=msg)
                update_dict = {}
                if hasattr(rec, 'data_averages_updated_date'):
                    update_dict['data_averages_updated_date'] = fields.Datetime.now()
                if hasattr(rec, 'data_averages_updated_by'):
                    update_dict['data_averages_updated_by'] = self.env.user.id
                if update_dict:
                    super(ProductTemplate, rec).write(update_dict)
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    measure_type_id = fields.Many2one(
        related='product_tmpl_id.measure_type_id',
        string='Tipo de medida',
        readonly=False
    )
    status = fields.Many2one(related='product_tmpl_id.status', string='Estatus', readonly=False)
    substatus = fields.Many2one(related='product_tmpl_id.substatus', string='Subestatus', readonly=False)
    packing_length = fields.Float(related='product_tmpl_id.packing_length', string='Largo empaque', readonly=False)
    packing_height = fields.Float(related='product_tmpl_id.packing_height', string='Alto empaque', readonly=False)
    packing_width = fields.Float(related='product_tmpl_id.packing_width', string='Ancho empaque', readonly=False)
    packing_weight = fields.Float(related='product_tmpl_id.packing_weight', string='Peso empaque', readonly=False)
