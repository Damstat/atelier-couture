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


def _peupler(client, db, h):
    from app.models import TypeVetement

    creer(client, h, nom="Robe", prix_base=30000, delai_jours=7)
    creer(client, h)
    db.add(TypeVetement(nom="Ancienne prestation", prix_base=1000, delai_jours=1, actif=False))
    db.commit()


def test_lister_catalogue_actifs_tries_par_nom(client, headers, db):
    _peupler(client, db, headers["admin"])
    r = client.get(URL, headers=headers["tailleur"])
    assert r.status_code == 200
    assert [p["nom"] for p in r.json()] == ["Boubou", "Robe"]


def test_lister_catalogue_avec_inactifs(client, headers, db):
    _peupler(client, db, headers["admin"])
    r = client.get(URL, params={"actifs_seulement": "false"}, headers=headers["accueil"])
    assert [p["nom"] for p in r.json()] == ["Ancienne prestation", "Boubou", "Robe"]


def test_detail_prestation_et_404(client, headers):
    pid = creer(client, headers["admin"]).json()["id"]
    r = client.get(f"{URL}/{pid}", headers=headers["accueil"])
    assert r.status_code == 200 and r.json()["nom"] == "Boubou"
    r = client.get(f"{URL}/9999", headers=headers["accueil"])
    assert r.status_code == 404 and "introuvable" in r.json()["detail"]
