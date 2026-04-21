from . import models


def _recompute_product_structure(env):
    """Recalcula product_structure para todos los productos tras actualizar."""
    products = env['product.product'].search([])
    products._compute_product_structure()