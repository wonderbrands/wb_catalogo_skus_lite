from . import estatus
from . import product_measure_type
from . import product_product
from . import product_template_extension

def _recompute_product_structure(env):
    """Recalcula product_structure para todos los productos tras actualizar."""
    products = env['product.product'].search([])
    products._compute_product_structure()