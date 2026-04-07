from fastapi import FastAPI

app = FastAPI(title="Coffee & Chill API")

@app.get("/")
async def root():
    return {"message": "Welcome to Coffee & Chill API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
