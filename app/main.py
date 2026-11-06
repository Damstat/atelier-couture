from fastapi import FastAPI

from app.errors import installer_gestionnaires

app = FastAPI(title="Atelier de couture", version="1.0.0")
installer_gestionnaires(app)


@app.get("/health")
def health():
    return {"status": "ok"}
