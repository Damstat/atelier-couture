import pytest

from app.exceptions import Conflit
from app.models.enums import StatutCommande as S
from app.services.workflow import verifier_transition

AUTORISEES = [
    (S.en_attente, S.en_coupe), (S.en_attente, S.annulee),
    (S.en_coupe, S.en_couture), (S.en_coupe, S.annulee),
    (S.en_couture, S.essayage), (S.en_couture, S.terminee), (S.en_couture, S.annulee),
    (S.essayage, S.retouches), (S.essayage, S.terminee), (S.essayage, S.annulee),
    (S.retouches, S.essayage), (S.retouches, S.terminee), (S.retouches, S.annulee),
]


@pytest.mark.parametrize("actuel, demande", AUTORISEES)
def test_transitions_autorisees(actuel, demande):
    verifier_transition(actuel, demande)


@pytest.mark.parametrize("actuel, demande", [
    (a, d) for a in S for d in S
    if (a, d) not in AUTORISEES and a != d and d != S.livree
])
def test_toutes_les_autres_transitions_sont_refusees(actuel, demande):
    with pytest.raises(Conflit, match="Transition interdite"):
        verifier_transition(actuel, demande)


def test_message_indique_les_statuts_possibles():
    with pytest.raises(Conflit) as e:
        verifier_transition(S.en_attente, S.terminee)
    assert e.value.message == "Transition interdite : en_attente → terminee. Statuts possibles : annulee, en_coupe."


def test_statuts_finaux_et_terminee():
    with pytest.raises(Conflit, match="aucun \\(statut final\\)"):
        verifier_transition(S.annulee, S.en_coupe)
    with pytest.raises(Conflit, match="confirmation de livraison"):
        verifier_transition(S.terminee, S.annulee)


def test_rg13_meme_statut_refuse():
    with pytest.raises(Conflit, match="déjà au statut « en_coupe »"):
        verifier_transition(S.en_coupe, S.en_coupe)


@pytest.mark.parametrize("actuel", [S.en_attente, S.terminee, S.en_couture])
def test_rg13_livree_jamais_par_la_route_de_statut(actuel):
    with pytest.raises(Conflit, match="confirmation de livraison"):
        verifier_transition(actuel, S.livree)
