from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, field_validator

from app.errors import installer_gestionnaires


class Exemple(BaseModel):
    nom: str = Field(min_length=1)
    age: int = Field(gt=0)

    @field_validator("nom")
    @classmethod
    def pas_toto(cls, v: str) -> str:
        if v == "toto":
            raise ValueError("ce nom est interdit")
        return v


def _client():
    app = FastAPI()
    installer_gestionnaires(app)

    @app.post("/exemple")
    def exemple(corps: Exemple):
        return corps

    return TestClient(app)


def test_erreur_422_en_francais_au_format_detail_texte():
    r = _client().post("/exemple", json={"age": 0})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert isinstance(detail, str)
    assert "Champ « nom » : champ obligatoire manquant" in detail
    assert "Champ « age » : doit être strictement supérieur à 0" in detail


def test_message_des_validateurs_metier_conserve():
    r = _client().post("/exemple", json={"nom": "toto", "age": 3})
    assert r.status_code == 422
    assert r.json()["detail"] == "Champ « nom » : ce nom est interdit"
