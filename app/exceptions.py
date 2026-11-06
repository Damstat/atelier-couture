"""Exceptions levées par les services (indépendantes de FastAPI).

Elles sont converties en réponse {"detail": message} avec le bon code HTTP
par le gestionnaire installé dans app/errors.py.
"""


class ErreurMetier(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class Introuvable(ErreurMetier):
    status_code = 404


class Conflit(ErreurMetier):
    status_code = 409


class DonneesInvalides(ErreurMetier):
    status_code = 422


class Interdit(ErreurMetier):
    status_code = 403


class NonAuthentifie(ErreurMetier):
    status_code = 401
