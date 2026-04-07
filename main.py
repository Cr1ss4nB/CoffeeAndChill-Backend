from fastapi import FastAPI
from app.routers import auth

app = FastAPI(
    title="Coffee & Chill API",
    version="0.1.0",
    description="API para el sistema POS + Reservas de Coffee & Chill",
)

app.include_router(auth.router)


@app.get("/")
async def root():
    return {"message": "Welcome to Coffee & Chill API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
