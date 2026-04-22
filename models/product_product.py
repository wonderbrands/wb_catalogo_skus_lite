from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
# VERSION LITE — Solo campos de clasificación (informativos)
#
# Este módulo agrega campos para categorizar productos pero NO modifica
# ningún flujo nativo de Odoo ni de Yuju:
#
#   ✓ Campos: data_entity_type, product_structure, data_product_id,
#             storable_base_id, is_internal_consu
#   ✓ Computes: clasificación automática basada en type/is_storable/BoM
#   ✓ Vistas: badges, filtros, searchpanel, menús
#
#   ✗ Sin bloqueos en write() (type/is_storable se cambian libremente)
#   ✗ Sin cron de duplicación (no crea clones ALM-xxx)
#   ✗ Sin overrides de stock (free_qty nativo, sin cálculo virtual)
#   ✗ Sin propagación de webhooks a combos padres
#
# Todo funciona exactamente igual que el nativo Odoo + Yuju.
# Los campos son puramente informativos para navegación y reporteo.

# ══════════════════════════════════════════════════════════════════════════


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_internal_consu = fields.Boolean(
        string="Es Consumible Interno",
        default=False,
        help="Actívalo solo para insumos/consumibles internos. "
             "Si no, el producto almacenable se trata como Base.",
    )

    data_entity_type = fields.Selection(
        selection=[
            ('salable_yuju', 'Vendible'),
            ('storable', 'Almacenable Base'),
            ('internal_consu', 'Consumible Interno'),
        ],
        string="Rol del Producto",
        compute='_compute_data_entity_type',
        store=True,
        readonly=True,
        tracking=True,
    )

    @api.depends('type', 'is_storable', 'is_internal_consu')
    def _compute_data_entity_type(self):
        for record in self:
            if record.is_storable:
                if record.is_internal_consu:
                    record.data_entity_type = 'internal_consu'
                else:
                    record.data_entity_type = 'storable'
            else:
                record.data_entity_type = 'salable_yuju'

    # ── Sin override de write() ───────────────────────────────────────────
    # En la versión Lite no se bloquean cambios de tipo.
    # type e is_storable se cambian libremente como en Odoo nativo.


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # ── Campos custom del catálogo ────────────────────────────────────────

    data_product_id = fields.Char(
        string="Data Product ID",
        copy=False,
        index=True,
        help="ID externo único para integraciones futuras.",
    )

    data_entity_type = fields.Selection(
        related='product_tmpl_id.data_entity_type',
        store=True,
        readonly=True,
        string="Rol del Producto",
    )

    is_internal_consu = fields.Boolean(
        related='product_tmpl_id.is_internal_consu',
        readonly=False,
    )

    # Vínculo manual al almacenable físico asociado.
    # En versión Lite este campo es editable manualmente.
    # En versión Completa lo llena el cron automáticamente.
    storable_base_id = fields.Many2one(
        'product.product',
        string="Base Almacenable Vinculada",
        copy=False,
        domain=[('data_entity_type', '=', 'storable')],
        help="Producto almacenable asociado. "
             "En versión Lite se asigna manualmente.",
    )

    # Relación inversa: desde un almacenable, ver qué vendibles lo usan
    salable_variant_ids = fields.One2many(
        'product.product',
        'storable_base_id',
        string="Vendibles Asociados",
        readonly=True,
    )

    # Clasificación informativa de la estructura del vendible
    product_structure = fields.Selection(
        selection=[
            ('simple', 'Simple'),
            ('combo', 'Combo'),
            ('multibox', 'Multicaja'),
        ],
        string="Estructura de Producto",
        compute="_compute_product_structure",
        store=True,
        help="Clasificación informativa basada en la BoM.\n"
             "Simple: sin BoM, BoM vacía, o BoM 1:1 (un componente qty=1).\n"
             "Combo: BoM con múltiples componentes sin patrón #BOX.\n"
             "Multicaja: BoM con componentes cuyo SKU sigue patrón #BOX/#CAJA/#PKG.",
    )

    _sql_constraints = [
        ('data_product_id_uniq',
         'UNIQUE(data_product_id)',
         'El Data Product ID debe ser único por producto.'),
    ]

    # ── COMPUTE: product_structure ────────────────────────────────────────
    # Analiza la BoM Phantom del vendible para clasificar su estructura.
    # Único criterio multibox vs combo: patrón #BOX en SKU de componentes.
    # Solo aplica a salable_yuju; storables e internal_consu quedan en False.

    @api.depends(
        'data_entity_type',
        'product_tmpl_id.bom_ids',
        'product_tmpl_id.bom_ids.bom_line_ids',
        'product_tmpl_id.bom_ids.bom_line_ids.product_id',
        'product_tmpl_id.bom_ids.bom_line_ids.product_qty',
    )
    def _compute_product_structure(self):
        for record in self:
            if record.data_entity_type != 'salable_yuju':
                record.product_structure = False
                continue

            bom = self._get_phantom_bom(record)

            if not bom or not bom.bom_line_ids:
                record.product_structure = 'simple'
                continue

            lines = bom.bom_line_ids
            
            logging.info(f'\n\n BOM {bom} ---- {lines}\n\n')

            # BoM con un solo componente y qty=1 → simple (1:1)
            if len(lines) == 1 and lines[0].product_qty == 1:
                record.product_structure = 'simple'
                continue

            # Único criterio: si algún componente tiene SKU #BOX → multibox
            
            logging.info(f'\n\n BOM {lines[0].product_id.default_code} ---- {record.default_code}\n\n')
            has_box_components = any(
                self._is_box_sku(line.product_id.default_code, record.default_code)
                for line in lines
            )

            if has_box_components:
                record.product_structure = 'multibox'
            else:
                record.product_structure = 'combo'

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_phantom_bom(self, product):
        """
        Busca la BoM Phantom del vendible.
        Prioridad: específica de variante > genérica de template.
        """
        return self.env['mrp.bom'].search([
            ('type', '=', 'phantom'),
            '|',
            ('product_id', '=', product.id),
            '&',
                ('product_id', '=', False),
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
        ])

    @staticmethod
    def _is_box_sku(component_sku, parent_sku):
        """
        Detecta si un SKU de componente sigue el patrón de multicaja.
        Patrón: {parent_sku}#BOX1, {parent_sku}#BOX2, etc.
        También acepta variantes como #CAJA1, #PKG1.
        Case-insensitive.
        """
        if not component_sku or not parent_sku:
            return False
        component_upper = (component_sku or '').upper()
        parent_upper = (parent_sku or '').upper()
        if not component_upper.startswith(parent_upper + '#'):
            return False
        suffix = component_upper[len(parent_upper) + 1:]
        return bool(suffix)

    # ══════════════════════════════════════════════════════════════════════
    # NOTA — Métodos NO implementados en versión Lite:
    #
    #   - send_webhook_action()           → sin propagación a combos
    #   - _get_product_stock()            → sin cálculo virtual Kit
    #   - get_stock_products()            → sin cálculo virtual batch
    #   - get_stock_data()                → sin inclusión de vendibles
    #   - _calc_kit_stock()               → sin cálculo recursivo
    #   - _cron_create_storable_bases()   → sin creación de clones
    #
    # Stock se reporta a Yuju tal cual lo hace nativamente:
    #   - free_qty directo del producto
    #   - Combos/Kits Phantom reportan 0 (comportamiento nativo Odoo)
    # ══════════════════════════════════════════════════════════════════════