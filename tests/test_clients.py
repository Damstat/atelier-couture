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


def _peupler(client, h):
    creer(client, h, nom="Diop", prenom="Fatou", telephone="771234567", genre="femme")
    creer(client, h, nom="Ba", prenom="Moussa", telephone="781112233", genre="homme")
    creer(client, h, nom="Diop", prenom="Awa", telephone="769998877", genre="femme")
    creer(client, h, nom="Sow", prenom="Ali", telephone="701234500", genre="enfant")


def test_lister_clients_pagine_trie_par_nom_puis_prenom(client, headers):
    _peupler(client, headers["accueil"])
    r = client.get(URL, headers=headers["tailleur"])
    assert r.status_code == 200
    corps = r.json()
    assert corps["total"] == 4 and corps["limit"] == 20 and corps["offset"] == 0
    assert [(c["nom"], c["prenom"]) for c in corps["items"]] == [
        ("Ba", "Moussa"), ("Diop", "Awa"), ("Diop", "Fatou"), ("Sow", "Ali")]

    r = client.get(URL, params={"limit": 2, "offset": 1}, headers=headers["tailleur"]).json()
    assert r["total"] == 4 and [c["prenom"] for c in r["items"]] == ["Awa", "Fatou"]


def test_lister_clients_recherche_q(client, headers):
    _peupler(client, headers["accueil"])
    h = headers["accueil"]
    assert [c["prenom"] for c in client.get(URL, params={"q": "diop"}, headers=h).json()["items"]] == ["Awa", "Fatou"]
    assert [c["prenom"] for c in client.get(URL, params={"q": "mou"}, headers=h).json()["items"]] == ["Moussa"]
    assert [c["prenom"] for c in client.get(URL, params={"q": "77 123"}, headers=h).json()["items"]] == ["Fatou"]


def test_lister_clients_filtre_genre(client, headers):
    _peupler(client, headers["accueil"])
    r = client.get(URL, params={"genre": "enfant"}, headers=headers["accueil"]).json()
    assert r["total"] == 1 and r["items"][0]["prenom"] == "Ali"


def test_lister_clients_parametres_invalides_422(client, headers):
    h = headers["accueil"]
    r = client.get(URL, params={"q": "a"}, headers=h)
    assert r.status_code == 422 and "2 caractères" in r.json()["detail"]
    assert client.get(URL, params={"limit": 101}, headers=h).status_code == 422
    assert client.get(URL, params={"offset": -1}, headers=h).status_code == 422
