URL = "/api/v1/clients"

FATOU = {"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67", "genre": "femme"}


def creer(client, headers, **corps):
    return client.post(URL, json={**FATOU, **corps}, headers=headers)


def test_creer_client_201_telephone_normalise(client, headers):
    r = creer(client, headers["accueil"])
    assert r.status_code == 201
    corps = r.json()
    assert corps["telephone"] == "771234567"
    assert corps["nom"] == "Diop" and corps["genre"] == "femme"


def test_rg1_doublon_de_telephone_409(client, headers):
    creer(client, headers["accueil"])
    r = creer(client, headers["accueil"], prenom="Awa", telephone="771234567")
    assert r.status_code == 409
    assert "771234567" in r.json()["detail"] and "déjà utilisé" in r.json()["detail"]


def test_rg1_telephone_invalide_422(client, headers):
    r = creer(client, headers["accueil"], telephone="77 12")
    assert r.status_code == 422
    assert "téléphone" in r.json()["detail"]


def test_creer_client_champs_obligatoires_422(client, headers):
    assert creer(client, headers["accueil"], nom="   ").status_code == 422
    r = client.post(URL, json={"nom": "Diop"}, headers=headers["accueil"])
    assert r.status_code == 422
    assert "prenom" in r.json()["detail"] and "telephone" in r.json()["detail"]


def test_creer_client_genre_invalide_422(client, headers):
    assert creer(client, headers["accueil"], genre="autre").status_code == 422
