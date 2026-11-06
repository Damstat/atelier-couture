from tests.conftest import MOT_DE_PASSE

URL = "/api/v1/auth/login"


def _login(client, email, mdp):
    return client.post(URL, data={"username": email, "password": mdp})


def test_login_ok_renvoie_un_jeton(client, utilisateurs):
    r = _login(client, "accueil@atelier.sn", MOT_DE_PASSE)
    assert r.status_code == 200
    corps = r.json()
    assert corps["token_type"] == "bearer"
    assert corps["expires_in"] > 0
    assert corps["access_token"]


def test_login_email_insensible_a_la_casse(client, utilisateurs):
    assert _login(client, " Accueil@Atelier.SN ", MOT_DE_PASSE).status_code == 200


def test_login_meme_message_email_inconnu_ou_mauvais_mot_de_passe(client, utilisateurs):
    inconnu = _login(client, "personne@atelier.sn", MOT_DE_PASSE)
    faux = _login(client, "accueil@atelier.sn", "mauvais-mdp")
    assert inconnu.status_code == faux.status_code == 401
    assert inconnu.json() == faux.json() == {"detail": "E-mail ou mot de passe incorrect."}


def test_login_compte_desactive_401(client, db, utilisateurs):
    utilisateurs["tailleur"].actif = False
    db.commit()
    r = _login(client, "tailleur@atelier.sn", MOT_DE_PASSE)
    assert r.status_code == 401
    assert "désactivé" in r.json()["detail"]


def test_login_champs_manquants_422(client):
    r = client.post(URL, data={})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)
