from fastapi import FastAPI

from app.errors import installer_gestionnaires
from app.routers import auth

API_PREFIX = "/api/v1"

app = FastAPI(title="Atelier de couture", version="1.0.0")
installer_gestionnaires(app)

app.include_router(auth.router, prefix=API_PREFIX)


@app.get("/health")
def health():
    return {"status": "ok"}
