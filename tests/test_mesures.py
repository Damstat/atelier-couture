from datetime import date

import pytest

API = "/api/v1"


@pytest.fixture()
def client_id(db):
    from app.models import Client

    c = Client(nom="Diop", prenom="Fatou", telephone="771234567")
    db.add(c)
    db.commit()
    return c.id


def prendre(client, h, cid, **valeurs):
    return client.post(f"{API}/clients/{cid}/mesures", json=valeurs or {"tour_taille": 80}, headers=h)


def test_tailleur_prend_des_mesures_201(client, headers, utilisateurs, client_id):
    r = prendre(client, headers["tailleur"], client_id, tour_taille=82.5, longueur_robe=120, notes="cliente debout")
    assert r.status_code == 201
    corps = r.json()
    assert corps["tour_taille"] == 82.5 and corps["longueur_robe"] == 120
    assert corps["tour_cou"] is None
    assert corps["date_prise"] == date.today().isoformat()
    assert corps["prise_par_id"] == utilisateurs["tailleur"].id
    assert corps["client_id"] == client_id


def test_date_prise_fournie(client, headers, client_id):
    r = prendre(client, headers["tailleur"], client_id, tour_cou=38, date_prise="2026-01-15")
    assert r.json()["date_prise"] == "2026-01-15"


def test_rg2_prise_vide_ou_hors_bornes_422(client, headers, client_id):
    h = headers["tailleur"]
    r = client.post(f"{API}/clients/{client_id}/mesures", json={"notes": "rien"}, headers=h)
    assert r.status_code == 422 and "au moins une mesure" in r.json()["detail"]
    r = prendre(client, h, client_id, tour_taille=0)
    assert r.status_code == 422 and "tour_taille" in r.json()["detail"]
    assert prendre(client, h, client_id, tour_taille=301).status_code == 422


def test_accueil_ne_peut_pas_prendre_de_mesures_403(client, headers, client_id):
    assert prendre(client, headers["accueil"], client_id).status_code == 403
    assert prendre(client, headers["admin"], client_id).status_code == 201


def test_mesures_client_inconnu_404(client, headers):
    assert prendre(client, headers["tailleur"], 9999).status_code == 404


def test_rg3_historique_et_dernieres_mesures(client, headers, client_id):
    h = headers["tailleur"]
    prendre(client, h, client_id, tour_taille=80, date_prise="2026-01-10")
    prendre(client, h, client_id, tour_taille=84, date_prise="2026-03-01")
    prendre(client, h, client_id, tour_taille=82, date_prise="2026-02-01")

    r = client.get(f"{API}/clients/{client_id}/mesures", headers=headers["accueil"])
    assert r.status_code == 200
    assert [m["date_prise"] for m in r.json()] == ["2026-03-01", "2026-02-01", "2026-01-10"]

    r = client.get(f"{API}/clients/{client_id}/mesures/derniere", headers=headers["accueil"])
    assert r.status_code == 200
    assert r.json()["date_prise"] == "2026-03-01" and r.json()["tour_taille"] == 84


def test_dernieres_mesures_404_si_aucune(client, headers, client_id):
    r = client.get(f"{API}/clients/{client_id}/mesures/derniere", headers=headers["accueil"])
    assert r.status_code == 404 and "aucune prise de mesures" in r.json()["detail"]
    assert client.get(f"{API}/clients/9999/mesures", headers=headers["accueil"]).status_code == 404


def test_detail_mesure_et_404(client, headers, client_id):
    mid = prendre(client, headers["tailleur"], client_id).json()["id"]
    r = client.get(f"{API}/mesures/{mid}", headers=headers["accueil"])
    assert r.status_code == 200 and r.json()["id"] == mid
    assert client.get(f"{API}/mesures/9999", headers=headers["accueil"]).status_code == 404
