"""Droits sur /utilisateurs : administrateur uniquement."""
import pytest

URL = "/api/v1/utilisateurs"
CORPS = {"email": "x@atelier.sn", "nom_complet": "X", "mot_de_passe": "secret123", "role": "accueil"}


def _appels(uid):
    return [
        ("post", URL, CORPS),
        ("get", URL, None),
        ("get", f"{URL}/{uid}", None),
        ("patch", f"{URL}/{uid}", {"nom_complet": "Y"}),
    ]


@pytest.mark.parametrize("role", ["accueil", "tailleur"])
def test_utilisateurs_interdit_hors_admin_403(client, headers, utilisateurs, role):
    for methode, url, corps in _appels(utilisateurs["accueil"].id):
        r = client.request(methode, url, json=corps, headers=headers[role])
        assert r.status_code == 403, (methode, url)


def test_utilisateurs_sans_jeton_401(client, utilisateurs):
    for methode, url, corps in _appels(utilisateurs["accueil"].id):
        assert client.request(methode, url, json=corps).status_code == 401, (methode, url)


def test_utilisateurs_admin_autorise(client, headers, utilisateurs):
    attendus = [201, 200, 200, 200]
    for (methode, url, corps), code in zip(_appels(utilisateurs["accueil"].id), attendus):
        assert client.request(methode, url, json=corps, headers=headers["admin"]).status_code == code
