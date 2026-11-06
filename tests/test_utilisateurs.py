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


def test_lister_utilisateurs_tries_par_nom(client, headers):
    r = client.get(URL, headers=headers["admin"])
    assert r.status_code == 200
    noms = [u["nom_complet"] for u in r.json()]
    assert noms == sorted(noms) == ["Awa Accueil", "Moussa Tailleur", "Patron"]
    assert all("mot_de_passe_hash" not in u for u in r.json())


def test_detail_utilisateur_et_404(client, headers, utilisateurs):
    r = client.get(f"{URL}/{utilisateurs['accueil'].id}", headers=headers["admin"])
    assert r.status_code == 200 and r.json()["role"] == "accueil"
    r = client.get(f"{URL}/9999", headers=headers["admin"])
    assert r.status_code == 404
    assert r.json() == {"detail": "Utilisateur 9999 introuvable."}


def test_modifier_utilisateur_champs_envoyes_seulement(client, headers, utilisateurs):
    uid = utilisateurs["tailleur"].id
    r = client.patch(f"{URL}/{uid}", json={"nom_complet": "Moussa Diop"}, headers=headers["admin"])
    assert r.status_code == 200
    assert r.json()["nom_complet"] == "Moussa Diop"
    assert r.json()["role"] == "tailleur" and r.json()["actif"] is True


def test_modifier_mot_de_passe_puis_connexion(client, headers, utilisateurs):
    uid = utilisateurs["accueil"].id
    assert client.patch(f"{URL}/{uid}", json={"mot_de_passe": "nouveau-mdp"}, headers=headers["admin"]).status_code == 200
    r = client.post("/api/v1/auth/login", data={"username": "accueil@atelier.sn", "password": "nouveau-mdp"})
    assert r.status_code == 200


def test_desactiver_un_compte_le_bloque_immediatement(client, headers, utilisateurs):
    uid = utilisateurs["tailleur"].id
    r = client.patch(f"{URL}/{uid}", json={"actif": False}, headers=headers["admin"])
    assert r.status_code == 200 and r.json()["actif"] is False
    assert client.get("/api/v1/auth/me", headers=headers["tailleur"]).status_code == 401


def test_rg24_admin_ne_peut_pas_se_desactiver(client, headers, utilisateurs):
    r = client.patch(f"{URL}/{utilisateurs['admin'].id}", json={"actif": False}, headers=headers["admin"])
    assert r.status_code == 409
    assert "désactiver votre propre compte" in r.json()["detail"]


def test_rg24_admin_ne_peut_pas_retirer_son_role(client, headers, utilisateurs):
    r = client.patch(f"{URL}/{utilisateurs['admin'].id}", json={"role": "accueil"}, headers=headers["admin"])
    assert r.status_code == 409
    assert "rôle d'administrateur" in r.json()["detail"]


def test_modifier_utilisateur_null_ou_mdp_court_422_et_404(client, headers, utilisateurs):
    uid = utilisateurs["tailleur"].id
    assert client.patch(f"{URL}/{uid}", json={"nom_complet": None}, headers=headers["admin"]).status_code == 422
    assert client.patch(f"{URL}/{uid}", json={"mot_de_passe": "court"}, headers=headers["admin"]).status_code == 422
    assert client.patch(f"{URL}/9999", json={"actif": True}, headers=headers["admin"]).status_code == 404
