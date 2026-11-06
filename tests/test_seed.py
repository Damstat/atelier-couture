import pytest

from app.models import TypeVetement, Utilisateur
from app.models.enums import Role
from app.security import verifier_mot_de_passe
from app.seed import initialiser


def test_seed_cree_l_admin_et_le_catalogue_de_l_annexe_b(db):
    messages = initialiser(db, "Patron@Atelier.sn", "motdepasse-admin", "Patron")
    admin = db.query(Utilisateur).one()
    assert admin.email == "patron@atelier.sn" and admin.role == Role.admin and admin.actif
    assert verifier_mot_de_passe("motdepasse-admin", admin.mot_de_passe_hash)
    catalogue = {t.nom: (t.prix_base, t.delai_jours) for t in db.query(TypeVetement)}
    assert catalogue == {
        "Boubou": (35000, 10), "Costume 2 pièces": (85000, 14), "Robe": (30000, 7),
        "Ensemble wax": (25000, 7), "Chemise": (15000, 5), "Pantalon": (12000, 4), "Retouche": (3000, 2),
    }
    assert "créé" in messages[0] and "7 prestation(s) ajoutée(s)" in messages[1]


def test_seed_peut_etre_relance_sans_doublon(db):
    initialiser(db, "patron@atelier.sn", "motdepasse-admin", "Patron")
    messages = initialiser(db, "patron@atelier.sn", "motdepasse-admin", "Patron")
    assert db.query(Utilisateur).count() == 1 and db.query(TypeVetement).count() == 7
    assert "déjà présent" in messages[0] and "0 prestation(s) ajoutée(s)" in messages[1]


def test_seed_sans_variables_admin_cree_quand_meme_le_catalogue(db):
    messages = initialiser(db, "", "", "Patron")
    assert db.query(Utilisateur).count() == 0 and db.query(TypeVetement).count() == 7
    assert "ADMIN_EMAIL" in messages[0]


def test_seed_mot_de_passe_admin_trop_court(db):
    with pytest.raises(ValueError, match="8 caractères"):
        initialiser(db, "patron@atelier.sn", "court", "Patron")


def test_admin_du_seed_peut_se_connecter(client, db):
    initialiser(db, "patron@atelier.sn", "motdepasse-admin", "Patron")
    r = client.post("/api/v1/auth/login", data={"username": "patron@atelier.sn", "password": "motdepasse-admin"})
    assert r.status_code == 200
