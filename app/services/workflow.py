"""Workflow des statuts de commande (section 6 de l'énoncé, RG13)."""
from app.exceptions import Conflit
from app.models.enums import StatutCommande as S

# Transitions autorisées par la route de changement de statut.
# « terminee -> livree » n'y figure pas : elle résulte de la confirmation de livraison.
TRANSITIONS: dict[S, set[S]] = {
    S.en_attente: {S.en_coupe, S.annulee},
    S.en_coupe: {S.en_couture, S.annulee},
    S.en_couture: {S.essayage, S.terminee, S.annulee},
    S.essayage: {S.retouches, S.terminee, S.annulee},
    S.retouches: {S.essayage, S.terminee, S.annulee},
    S.terminee: set(),
    S.livree: set(),
    S.annulee: set(),
}


def statuts_possibles(actuel: S) -> str:
    """Texte des statuts possibles après « actuel », pour les messages d'erreur."""
    if actuel == S.terminee:
        return "livree (uniquement par la confirmation de livraison)"
    possibles = TRANSITIONS[actuel]
    if not possibles:
        return "aucun (statut final)"
    return ", ".join(sorted(s.value for s in possibles))


def verifier_transition(actuel: S, demande: S) -> None:
    """Lève Conflit (409) si la transition n'est pas permise, avec les statuts possibles."""
    if demande == actuel:
        raise Conflit(
            f"La commande est déjà au statut « {actuel.value} ». "
            f"Statuts possibles : {statuts_possibles(actuel)}."
        )
    if demande == S.livree:
        raise Conflit(
            "Le statut « livree » ne peut pas être posé par cette route : il résulte de la "
            "confirmation de livraison (POST /commandes/{id}/livraison/confirmer)."
        )
    if demande not in TRANSITIONS[actuel]:
        raise Conflit(
            f"Transition interdite : {actuel.value} → {demande.value}. "
            f"Statuts possibles : {statuts_possibles(actuel)}."
        )
