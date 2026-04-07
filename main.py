from fastapi import FastAPI
from app.routers import auth, catalog, orders

app = FastAPI(
    title="Coffee & Chill API",
    version="0.1.0",
    description="API para el sistema POS + Reservas de Coffee & Chill",
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(orders.router)


@app.get("/")
async def root():
    return {"message": "Welcome to Coffee & Chill API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
