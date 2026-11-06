"""RG1 : normalisation et validation du numéro de téléphone."""
import re

_SEPARATEURS = re.compile(r"[\s.\-()]")
_FORME_VALIDE = re.compile(r"^\+?\d{6,20}$")

MESSAGE_INVALIDE = (
    "numéro de téléphone invalide : 6 à 20 chiffres, avec un « + » initial facultatif "
    "(espaces, points, tirets et parenthèses acceptés), par exemple « 77 123 45 67 »"
)


def normaliser_telephone(telephone: str) -> str:
    """« 77 123 45 67 » -> « 771234567 ». Lève ValueError si la forme est invalide."""
    normalise = _SEPARATEURS.sub("", telephone or "")
    if not _FORME_VALIDE.fullmatch(normalise):
        raise ValueError(MESSAGE_INVALIDE)
    return normalise
