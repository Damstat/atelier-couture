URL = "/api/v1/catalogue"

BOUBOU = {"nom": "Boubou", "description": "Boubou homme en bazin ou brodé", "prix_base": 35000, "delai_jours": 10}


def creer(client, headers, **corps):
    return client.post(URL, json={**BOUBOU, **corps}, headers=headers)


def test_creer_prestation_201(client, headers):
    r = creer(client, headers["admin"])
    assert r.status_code == 201
    assert r.json() | {"id": 0} == {**BOUBOU, "id": 0, "actif": True}


def test_creer_prestation_nom_existant_409(client, headers):
    creer(client, headers["admin"])
    r = creer(client, headers["admin"], nom="  boubou ")
    assert r.status_code == 409
    assert "Boubou" in r.json()["detail"] or "boubou" in r.json()["detail"]


def test_creer_prestation_valeurs_invalides_422(client, headers):
    h = headers["admin"]
    assert creer(client, h, prix_base=0).status_code == 422
    assert creer(client, h, delai_jours=-1).status_code == 422
    assert creer(client, h, nom="").status_code == 422


def test_creer_prestation_reservee_admin(client, headers):
    assert creer(client, headers["accueil"]).status_code == 403
    assert creer(client, headers["tailleur"]).status_code == 403
    assert client.post(URL, json=BOUBOU).status_code == 401
