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


def test_detail_client_et_404(client, headers):
    cid = creer(client, headers["accueil"]).json()["id"]
    r = client.get(f"{URL}/{cid}", headers=headers["tailleur"])
    assert r.status_code == 200 and r.json()["prenom"] == "Fatou"
    r = client.get(f"{URL}/9999", headers=headers["tailleur"])
    assert r.status_code == 404 and r.json() == {"detail": "Client 9999 introuvable."}


def test_modifier_client_partiel(client, headers):
    cid = creer(client, headers["accueil"], adresse="Médina").json()["id"]
    r = client.patch(f"{URL}/{cid}", json={"adresse": "Parcelles Assainies"}, headers=headers["accueil"])
    assert r.status_code == 200
    assert r.json()["adresse"] == "Parcelles Assainies"
    assert r.json()["nom"] == "Diop" and r.json()["telephone"] == "771234567"


def test_modifier_client_garder_son_numero_n_est_pas_un_doublon(client, headers):
    cid = creer(client, headers["accueil"]).json()["id"]
    r = client.patch(f"{URL}/{cid}", json={"telephone": "77.123.45.67"}, headers=headers["accueil"])
    assert r.status_code == 200 and r.json()["telephone"] == "771234567"


def test_modifier_client_numero_d_un_autre_409(client, headers):
    creer(client, headers["accueil"])
    cid = creer(client, headers["accueil"], prenom="Awa", telephone="781112233").json()["id"]
    r = client.patch(f"{URL}/{cid}", json={"telephone": "77 123 45 67"}, headers=headers["accueil"])
    assert r.status_code == 409


def test_modifier_client_ne_peut_pas_vider_nom_prenom_telephone_422(client, headers):
    cid = creer(client, headers["accueil"]).json()["id"]
    h = headers["accueil"]
    for corps in ({"nom": None}, {"prenom": ""}, {"telephone": None}, {"telephone": "  "}):
        r = client.patch(f"{URL}/{cid}", json=corps, headers=h)
        assert r.status_code == 422, corps
    assert client.patch(f"{URL}/9999", json={"notes": "x"}, headers=h).status_code == 404


def test_supprimer_client_204_supprime_aussi_ses_mesures(client, headers, db):
    from sqlalchemy import select

    from app.models import Mesure
    from tests.factories import mesure_en_base

    cid = creer(client, headers["accueil"]).json()["id"]
    mesure_en_base(db, cid)
    r = client.delete(f"{URL}/{cid}", headers=headers["admin"])
    assert r.status_code == 204 and r.content == b""
    assert client.get(f"{URL}/{cid}", headers=headers["admin"]).status_code == 404
    db.expire_all()
    assert db.scalars(select(Mesure).where(Mesure.client_id == cid)).all() == []


def test_rg4_supprimer_client_avec_commandes_409(client, headers, db):
    from tests.factories import commande_en_base

    cid = creer(client, headers["accueil"]).json()["id"]
    commande_en_base(db, cid)
    r = client.delete(f"{URL}/{cid}", headers=headers["admin"])
    assert r.status_code == 409
    assert "1 commande" in r.json()["detail"]


def test_supprimer_client_reserve_admin_et_404(client, headers):
    cid = creer(client, headers["accueil"]).json()["id"]
    assert client.delete(f"{URL}/{cid}", headers=headers["accueil"]).status_code == 403
    assert client.delete(f"{URL}/{cid}", headers=headers["tailleur"]).status_code == 403
    assert client.delete(f"{URL}/9999", headers=headers["admin"]).status_code == 404


def test_commandes_du_client_paginees_plus_recente_d_abord(client, headers, db):
    from datetime import date, timedelta

    from app.models.enums import StatutCommande
    from tests.factories import commande_en_base

    cid = creer(client, headers["accueil"]).json()["id"]
    autre = creer(client, headers["accueil"], prenom="Awa", telephone="781112233").json()["id"]
    il_y_a_un_mois = date.today() - timedelta(days=30)
    commande_en_base(db, cid, "CMD-2026-00001", date_commande=il_y_a_un_mois, montant_total=20000, montant_paye=5000)
    commande_en_base(db, cid, "CMD-2026-00002")
    commande_en_base(db, autre, "CMD-2026-00003")
    commande_en_base(db, cid, "CMD-2026-00004", statut=StatutCommande.livree, date_commande=il_y_a_un_mois)

    r = client.get(f"{URL}/{cid}/commandes", headers=headers["tailleur"])
    assert r.status_code == 200
    corps = r.json()
    assert corps["total"] == 3
    assert [c["numero"] for c in corps["items"]] == ["CMD-2026-00002", "CMD-2026-00004", "CMD-2026-00001"]
    ancienne = corps["items"][2]
    assert ancienne["client_nom"] == "Fatou Diop"
    assert ancienne["solde"] == 15000
    assert ancienne["en_retard"] is True           # RG11 : date prévue dépassée
    assert corps["items"][1]["en_retard"] is False  # livrée : jamais en retard

    page = client.get(f"{URL}/{cid}/commandes", params={"limit": 1, "offset": 1}, headers=headers["tailleur"]).json()
    assert page["total"] == 3 and [c["numero"] for c in page["items"]] == ["CMD-2026-00004"]


def test_commandes_client_inconnu_404(client, headers):
    assert client.get(f"{URL}/9999/commandes", headers=headers["accueil"]).status_code == 404


def test_resume_client_exclut_les_commandes_annulees(client, headers, db):
    from datetime import date, timedelta

    from app.models.enums import StatutCommande
    from tests.factories import commande_en_base, mesure_en_base

    cid = creer(client, headers["accueil"]).json()["id"]
    hier = date.today() - timedelta(days=1)
    commande_en_base(db, cid, "CMD-2026-00001", date_commande=hier, montant_total=50000, montant_paye=20000)
    commande_en_base(db, cid, "CMD-2026-00002", montant_total=30000, montant_paye=30000)
    commande_en_base(db, cid, "CMD-2026-00003", statut=StatutCommande.annulee, montant_total=99000, montant_paye=1000)

    r = client.get(f"{URL}/{cid}/resume", headers=headers["tailleur"])
    assert r.status_code == 200
    corps = r.json()
    assert corps["nb_commandes"] == 2
    assert corps["chiffre_affaires"] == 80000
    assert corps["total_paye"] == 50000
    assert corps["solde_du"] == 30000
    assert corps["derniere_commande"]["numero"] == "CMD-2026-00002"
    assert corps["a_des_mesures"] is False

    mesure_en_base(db, cid)
    assert client.get(f"{URL}/{cid}/resume", headers=headers["tailleur"]).json()["a_des_mesures"] is True


def test_resume_client_sans_commande_et_404(client, headers):
    cid = creer(client, headers["accueil"]).json()["id"]
    corps = client.get(f"{URL}/{cid}/resume", headers=headers["accueil"]).json()
    assert corps["nb_commandes"] == 0 and corps["solde_du"] == 0 and corps["derniere_commande"] is None
    assert client.get(f"{URL}/9999/resume", headers=headers["accueil"]).status_code == 404
