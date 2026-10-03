from .admin import router as admin_router
from .common import router as common_router
from .operators import router as operators_router
from .orders import router as orders_router

__all__ = ["admin_router", "common_router", "operators_router", "orders_router"]
