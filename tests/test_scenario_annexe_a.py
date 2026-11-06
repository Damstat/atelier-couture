"""Scénario de démonstration de l'annexe A, de bout en bout, uniquement via l'API."""
from datetime import date, timedelta

from app.seed import initialiser

API = "/api/v1"


def connexion(client, email, mot_de_passe):
    r = client.post(f"{API}/auth/login", data={"username": email, "password": mot_de_passe})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_scenario_de_demonstration(client, db):
    # Préparation : python -m app.seed (admin + catalogue de l'annexe B), puis l'admin crée l'équipe
    initialiser(db, "patron@atelier.sn", "patron-2026", "Mamadou")
    admin = connexion(client, "patron@atelier.sn", "patron-2026")
    for email, role in [("awa@atelier.sn", "accueil"), ("moussa@atelier.sn", "tailleur")]:
        r = client.post(f"{API}/utilisateurs", headers=admin,
                        json={"email": email, "nom_complet": email.split("@")[0], "mot_de_passe": "atelier-2026", "role": role})
        assert r.status_code == 201
    catalogue = {p["nom"]: p for p in client.get(f"{API}/catalogue", headers=admin).json()}
    ca_avant = client.get(f"{API}/statistiques/tableau-de-bord", headers=admin).json()["chiffre_affaires_mois"]

    # 1. Accueil : crée Fatou Diop ; un second client avec « 771234567 » est refusé (409)
    accueil = connexion(client, "awa@atelier.sn", "atelier-2026")
    r = client.post(f"{API}/clients", headers=accueil,
                    json={"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67", "genre": "femme"})
    assert r.status_code == 201
    fatou = r.json()
    r = client.post(f"{API}/clients", headers=accueil, json={"nom": "Autre", "prenom": "Client", "telephone": "771234567"})
    assert r.status_code == 409

    # 2. Tailleur : prend les mesures de Fatou ; l'accueil qui tente la même action reçoit 403
    tailleur = connexion(client, "moussa@atelier.sn", "atelier-2026")
    mesures = {"tour_poitrine": 92, "tour_taille": 74, "tour_bassin": 100, "longueur_pantalon": 102}
    r = client.post(f"{API}/clients/{fatou['id']}/mesures", headers=tailleur, json=mesures)
    assert r.status_code == 201
    mesure = r.json()
    assert client.post(f"{API}/clients/{fatou['id']}/mesures", headers=accueil, json=mesures).status_code == 403

    # 3. Accueil : 2 boubous + 1 pantalon à prix négocié, avec une remise
    r = client.post(f"{API}/commandes", headers=accueil, json={
        "client_id": fatou["id"],
        "lignes": [
            {"type_vetement_id": catalogue["Boubou"]["id"], "quantite": 2},
            {"type_vetement_id": catalogue["Pantalon"]["id"], "quantite": 1, "prix_unitaire": 10000},
        ],
        "remise": 5000,
    })
    assert r.status_code == 201
    commande = r.json()
    cid = commande["id"]
    assert commande["numero"] == f"CMD-{date.today().year}-{cid:05d}"
    assert commande["montant_total"] == 2 * 35000 + 10000 - 5000 == 75000
    assert commande["date_livraison_prevue"] == (date.today() + timedelta(days=10)).isoformat()
    assert commande["mesure_id"] == mesure["id"]
    assert commande["statut"] == "en_attente"

    # 4. Accueil : passer à « terminee » est refusé (409), le message indique les statuts possibles
    r = client.post(f"{API}/commandes/{cid}/statut", headers=accueil, json={"statut": "terminee"})
    assert r.status_code == 409
    assert r.json()["detail"] == "Transition interdite : en_attente → terminee. Statuts possibles : annulee, en_coupe."

    # 5. Tailleur : avance jusqu'à « terminee » avec un aller-retour essayage / retouches
    for statut in ["en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"]:
        r = client.post(f"{API}/commandes/{cid}/statut", headers=tailleur, json={"statut": statut})
        assert r.status_code == 200, (statut, r.text)
    historique = client.get(f"{API}/commandes/{cid}/historique", headers=tailleur).json()
    assert [h["nouveau_statut"] for h in historique] == [
        "en_attente", "en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"]
    assert historique[0]["ancien_statut"] is None

    # 6. Accueil : acompte Wave ; un paiement supérieur au solde est refusé (409)
    r = client.post(f"{API}/commandes/{cid}/paiements", headers=accueil,
                    json={"montant": 30000, "mode": "wave", "reference": "WAVE-0001"})
    assert r.status_code == 201
    r = client.post(f"{API}/commandes/{cid}/paiements", headers=accueil, json={"montant": 45001, "mode": "wave"})
    assert r.status_code == 409

    # 7. Accueil : confirmer la livraison est refusé (409) car le solde n'est pas payé
    r = client.post(f"{API}/commandes/{cid}/livraison/confirmer", headers=accueil)
    assert r.status_code == 409 and "45000 FCFA" in r.json()["detail"]

    # 8. Accueil : encaisse le solde puis confirme : la commande est « livree », solde à 0
    assert client.post(f"{API}/commandes/{cid}/paiements", headers=accueil,
                       json={"montant": 45000, "mode": "especes"}).status_code == 201
    r = client.post(f"{API}/commandes/{cid}/livraison/confirmer", headers=accueil)
    assert r.status_code == 200
    assert r.json()["statut"] == "livree" and r.json()["solde"] == 0
    assert r.json()["livraison"]["mode"] == "retrait_atelier"

    # 9. Admin : le CA du mois a augmenté du montant de la commande ; l'accueil reçoit 403
    tableau = client.get(f"{API}/statistiques/tableau-de-bord", headers=admin).json()
    assert tableau["chiffre_affaires_mois"] == ca_avant + 75000
    assert tableau["encaisse_mois"] == 75000
    assert client.get(f"{API}/statistiques/tableau-de-bord", headers=accueil).status_code == 403

    # 10. Admin : consulte les impayés et les commandes en retard
    r = client.get(f"{API}/statistiques/impayes", headers=admin)
    assert r.status_code == 200 and r.json()["total"] == 0
    r = client.get(f"{API}/commandes", params={"en_retard": "true"}, headers=admin)
    assert r.status_code == 200 and r.json()["total"] == 0
