"""Erreurs de l'API : toujours {"detail": "message en français"}."""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_MESSAGES = {
    "missing": "champ obligatoire manquant",
    "string_too_short": "doit contenir au moins {min_length} caractère(s)",
    "string_too_long": "ne doit pas dépasser {max_length} caractère(s)",
    "string_type": "doit être une chaîne de caractères",
    "int_parsing": "doit être un nombre entier",
    "int_type": "doit être un nombre entier",
    "int_from_float": "doit être un nombre entier",
    "float_parsing": "doit être un nombre",
    "float_type": "doit être un nombre",
    "bool_parsing": "doit être vrai ou faux",
    "bool_type": "doit être vrai ou faux",
    "greater_than": "doit être strictement supérieur à {gt}",
    "greater_than_equal": "doit être supérieur ou égal à {ge}",
    "less_than": "doit être strictement inférieur à {lt}",
    "less_than_equal": "doit être inférieur ou égal à {le}",
    "enum": "valeur non autorisée (valeurs possibles : {expected})",
    "literal_error": "valeur non autorisée (valeurs possibles : {expected})",
    "date_parsing": "date invalide (format attendu : AAAA-MM-JJ)",
    "date_from_datetime_parsing": "date invalide (format attendu : AAAA-MM-JJ)",
    "date_type": "date invalide (format attendu : AAAA-MM-JJ)",
    "json_invalid": "corps JSON invalide",
    "model_type": "objet JSON attendu",
    "list_type": "liste attendue",
    "too_short": "doit contenir au moins {min_length} élément(s)",
    "extra_forbidden": "champ non autorisé",
}


def _message(err: dict) -> str:
    type_ = err.get("type", "")
    ctx = err.get("ctx") or {}
    if type_ == "value_error":
        # Message de nos propres validateurs (déjà en français)
        texte = str(ctx.get("error", err.get("msg", "")))
    elif type_ in _MESSAGES:
        try:
            texte = _MESSAGES[type_].format(**ctx)
        except (KeyError, IndexError):
            texte = _MESSAGES[type_]
    elif "email" in err.get("msg", "").lower():
        texte = "adresse e-mail invalide"
    else:
        texte = err.get("msg", "valeur invalide")

    # loc = ("body", "telephone") -> « telephone » ; on ignore la source (body, query...)
    champs = [str(p) for p in err.get("loc", ()) if p not in ("body", "query", "path", "header", "form")]
    if champs:
        return f"Champ « {'.'.join(champs)} » : {texte}"
    return texte[:1].upper() + texte[1:]


async def _erreur_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
    detail = " ; ".join(_message(e) for e in exc.errors())
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": detail})


def installer_gestionnaires(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _erreur_validation)
