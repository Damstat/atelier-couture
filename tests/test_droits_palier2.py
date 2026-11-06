"""Droits par rôle sur mesures, commandes et paiements (section 4 de l'énoncé)."""
import pytest

from tests.factories import corps_commande, creer_commande

API = "/api/v1"
TOUS = {"admin", "accueil", "tailleur"}
TAILLEUR = {"admin", "tailleur"}
ACCUEIL = {"admin", "accueil"}
ADMIN = {"admin"}


@pytest.fixture()
def ids(client, headers, donnees):
    c = creer_commande(client, headers["admin"], corps_commande(donnees)).json()
    p = client.post(f"{API}/commandes/{c['id']}/paiements", json={"montant": 1000, "mode": "wave"},
                    headers=headers["admin"]).json()
    return {**donnees, "commande": c["id"], "ligne": c["lignes"][1]["id"], "paiement": p["id"]}


def _routes(d):
    f, cmd = d["fatou"], d["commande"]
    m = d["mesure_ancienne"]  # non utilisée par la commande : supprimable
    # (méthode, url, corps, rôles autorisés, code si autorisé) — exécutées dans cet ordre
    return [
        ("post", f"{API}/clients/{f}/mesures", {"tour_cou": 38}, TAILLEUR, 201),
        ("get", f"{API}/clients/{f}/mesures", None, TOUS, 200),
        ("get", f"{API}/clients/{f}/mesures/derniere", None, TOUS, 200),
        ("get", f"{API}/mesures/{m}", None, TOUS, 200),
        ("patch", f"{API}/mesures/{m}", {"tour_taille": 81}, TAILLEUR, 200),
        ("delete", f"{API}/mesures/{m}", None, TAILLEUR, 204),
        ("post", f"{API}/commandes", corps_commande(d), ACCUEIL, 201),
        ("get", f"{API}/commandes", None, TOUS, 200),
        ("get", f"{API}/commandes/{cmd}", None, TOUS, 200),
        ("patch", f"{API}/commandes/{cmd}", {"notes": "x"}, ACCUEIL, 200),
        ("get", f"{API}/commandes/{cmd}/historique", None, TOUS, 200),
        ("post", f"{API}/commandes/{cmd}/lignes", {"type_vetement_id": d["pantalon"]}, ACCUEIL, 201),
        ("delete", f"{API}/commandes/{cmd}/lignes/{d['ligne']}", None, ACCUEIL, 200),
        ("post", f"{API}/commandes/{cmd}/paiements", {"montant": 500, "mode": "especes"}, ACCUEIL, 201),
        ("get", f"{API}/commandes/{cmd}/paiements", None, TOUS, 200),
        ("delete", f"{API}/paiements/{d['paiement']}", None, ADMIN, 204),
        ("post", f"{API}/commandes/{cmd}/statut", {"statut": "en_coupe"}, TOUS, 200),
    ]


@pytest.mark.parametrize("role", sorted(TOUS))
def test_droits_par_role_palier2(client, headers, ids, role):
    for methode, url, corps, autorises, code in _routes(ids):
        r = client.request(methode, url, json=corps, headers=headers[role])
        attendu = code if role in autorises else 403
        assert r.status_code == attendu, (role, methode, url, r.text)


def test_rg14_annulation_interdite_au_tailleur_permise_a_l_accueil(client, headers, ids):
    url = f"{API}/commandes/{ids['commande']}/statut"
    corps = {"statut": "annulee", "commentaire": "acompte remboursé"}
    assert client.post(url, json=corps, headers=headers["tailleur"]).status_code == 403
    assert client.post(url, json=corps, headers=headers["accueil"]).status_code == 200


def test_sans_jeton_401_partout(client, ids):
    for methode, url, corps, _, _ in _routes(ids):
        assert client.request(methode, url, json=corps).status_code == 401, (methode, url)
