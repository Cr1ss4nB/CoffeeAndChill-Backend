import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import create_db_and_tables
from app.routers import (
    auth,
    catalog,
    employees,
    ingredients,
    inventory,
    orders,
    payments,
    products,
    public,
    tables,
    workshops,
)

logger = logging.getLogger(__name__)

MEDIA_DIR = settings.MEDIA_DIR
os.makedirs(os.path.join(MEDIA_DIR, "images"), exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.AUTO_CREATE_TABLES:
        create_db_and_tables()

    if settings.AUTO_SEED_DEMO_DATA:
        try:
            from seeders import run_all

            run_all()
            logger.info("Demo data seeded successfully")
        except Exception:
            logger.exception("Demo data seeding failed during startup")

    yield


app = FastAPI(
    title="Coffee & Chill API",
    version="0.1.0",
    description="API para el sistema POS + Reservas de Coffee & Chill",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["catalog"])
app.include_router(catalog.router, prefix="/catalog", tags=["catalog"])
app.include_router(inventory.router, prefix="/api/v1/admin/inventory", tags=["inventory"])
app.include_router(inventory.router, prefix="/admin/inventory", tags=["inventory"])
app.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
app.include_router(ingredients.router, prefix="/api/v1/admin/ingredients", tags=["ingredients"])
app.include_router(ingredients.router, prefix="/admin/ingredients", tags=["ingredients"])
app.include_router(ingredients.router, prefix="/ingredients", tags=["ingredients"])
app.include_router(products.router, prefix="/api/v1/admin/products", tags=["products"])
app.include_router(products.router, prefix="/admin/products", tags=["products"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(employees.router, prefix="/api/v1/admin/employees", tags=["employees"])
app.include_router(employees.router, prefix="/admin/employees", tags=["employees"])
app.include_router(employees.router, prefix="/employees", tags=["employees"])
app.include_router(tables.router, prefix="/api/v1/admin/tables", tags=["tables"])
app.include_router(tables.router, prefix="/admin/tables", tags=["tables"])
app.include_router(tables.router, prefix="/tables", tags=["tables"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(workshops.router, prefix="/api/v1/workshops", tags=["workshops"])
app.include_router(workshops.router, prefix="/admin/workshops", tags=["workshops"])
app.include_router(workshops.router, prefix="/workshops", tags=["workshops"])
app.include_router(public.router, prefix="/api/v1/public", tags=["public"])
app.include_router(public.router, prefix="/public", tags=["public"])
app.include_router(payments.router, prefix="/api/v1/admin/payments", tags=["payments"])
app.include_router(payments.router, prefix="/admin/payments", tags=["payments"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])


@app.get("/")
async def root():
    return {"message": "Welcome to Coffee & Chill API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
