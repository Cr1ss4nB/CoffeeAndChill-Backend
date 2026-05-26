import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import auth, catalog, categories, employees, ingredients, inventory, products, tables, orders, workshops, public, payments

MEDIA_DIR = settings.MEDIA_DIR
os.makedirs(os.path.join(MEDIA_DIR, "images"), exist_ok=True)

app = FastAPI(
    title="Coffee & Chill API",
    version="0.1.0",
    description="API para el sistema POS + Reservas de Coffee & Chill",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(inventory.router)
app.include_router(ingredients.router)
app.include_router(products.router)
app.include_router(employees.router)
app.include_router(tables.router)
app.include_router(orders.router)
app.include_router(workshops.router)
app.include_router(public.router)
app.include_router(payments.router)


@app.get("/")
async def root():
    return {"message": "Welcome to Coffee & Chill API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
