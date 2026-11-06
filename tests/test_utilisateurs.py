URL = "/api/v1/utilisateurs"

NOUVEAU = {"email": "Fatou@Atelier.sn", "nom_complet": "Fatou Ndiaye", "mot_de_passe": "secret123", "role": "tailleur"}


def test_creer_utilisateur_201_sans_mot_de_passe_dans_la_reponse(client, headers):
    r = client.post(URL, json=NOUVEAU, headers=headers["admin"])
    assert r.status_code == 201
    corps = r.json()
    assert corps["email"] == "fatou@atelier.sn"
    assert corps["role"] == "tailleur" and corps["actif"] is True
    assert "mot_de_passe" not in corps and "mot_de_passe_hash" not in corps


def test_nouvel_utilisateur_peut_se_connecter(client, headers):
    client.post(URL, json=NOUVEAU, headers=headers["admin"])
    r = client.post("/api/v1/auth/login", data={"username": "fatou@atelier.sn", "password": "secret123"})
    assert r.status_code == 200


def test_creer_utilisateur_email_existant_409(client, headers):
    client.post(URL, json=NOUVEAU, headers=headers["admin"])
    r = client.post(URL, json={**NOUVEAU, "email": "FATOU@atelier.sn"}, headers=headers["admin"])
    assert r.status_code == 409
    assert "existe déjà" in r.json()["detail"]


def test_creer_utilisateur_mot_de_passe_trop_court_422(client, headers):
    r = client.post(URL, json={**NOUVEAU, "mot_de_passe": "court"}, headers=headers["admin"])
    assert r.status_code == 422
    assert "mot_de_passe" in r.json()["detail"]


def test_creer_utilisateur_role_ou_email_invalide_422(client, headers):
    assert client.post(URL, json={**NOUVEAU, "role": "patron"}, headers=headers["admin"]).status_code == 422
    assert client.post(URL, json={**NOUVEAU, "email": "pas-un-email"}, headers=headers["admin"]).status_code == 422
