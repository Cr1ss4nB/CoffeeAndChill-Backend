from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, catalog, employees, inventory, products, tables, orders

app = FastAPI(
    title="Coffee & Chill API",
    version="0.1.0",
    description="API para el sistema POS + Reservas de Coffee & Chill",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this should be specific
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(inventory.router)
app.include_router(products.router)
app.include_router(employees.router)
app.include_router(tables.router)
app.include_router(orders.router)


@app.get("/")
async def root():
    return {"message": "Welcome to Coffee & Chill API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
