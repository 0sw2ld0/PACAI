"""Validación de mensajes contra el esquema JSON de PACAI 0.2.

El esquema viaja dentro del paquete (``pacai-0.2.schema.json``). Lo copia
``schema/generar.py`` cada vez que se regenera.
"""
from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any, Mapping

__all__ = ['schema', 'validator', 'validate', 'is_valid', 'ValidationFailed']


class ValidationFailed(ValueError):
    """Un mensaje no cumple el esquema. ``errors`` lleva los motivos."""

    def __init__(self, errors: list[str]):
        super().__init__('; '.join(errors))
        self.errors = errors


@lru_cache(maxsize=1)
def schema() -> dict:
    texto = resources.files('pacai').joinpath('pacai-0.2.schema.json').read_text(encoding='utf-8')
    return json.loads(texto)


@lru_cache(maxsize=1)
def validator():
    import jsonschema  # única dependencia del paquete

    return jsonschema.Draft202012Validator(schema(), format_checker=jsonschema.FormatChecker())


def validate(message: Mapping[str, Any]) -> list[str]:
    """Devuelve la lista de errores de esquema (vacía si el mensaje es válido)."""
    errores = sorted(validator().iter_errors(message), key=lambda e: list(e.absolute_path))
    return [e.message for e in errores]


def is_valid(message: Mapping[str, Any]) -> bool:
    return not validate(message)
