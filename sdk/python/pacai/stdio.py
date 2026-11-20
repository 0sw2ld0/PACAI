"""Transporte ``pacai+stdio`` (§5.1): un mensaje JSON compacto por línea.

stdout lleva solo mensajes PACAI; los registros van por stderr.
"""
from __future__ import annotations

import io
import json
import sys
from typing import IO, Any, Iterator, Mapping

__all__ = ['encode', 'decode', 'read_messages', 'StdioTransport', 'DEFAULT_MAX_BYTES']

DEFAULT_MAX_BYTES = 1024 * 1024  # §4.1: 1 MiB por defecto


class MessageTooLarge(ValueError):
    """La línea supera el límite negociado (``error`` ``message_too_large``)."""


def encode(message: Mapping[str, Any]) -> str:
    """JSON compacto en UTF-8 terminado en ``\\n``. Nunca contiene saltos de línea internos."""
    return json.dumps(message, ensure_ascii=False, separators=(',', ':')) + '\n'


def decode(line: str | bytes) -> dict[str, Any]:
    if isinstance(line, bytes):
        line = line.decode('utf-8')
    valor = json.loads(line)
    if not isinstance(valor, dict):
        raise ValueError('un mensaje PACAI es un objeto JSON')
    return valor


def read_messages(stream: IO, max_bytes: int = DEFAULT_MAX_BYTES) -> Iterator[dict[str, Any]]:
    """Itera los mensajes de un flujo JSONL hasta EOF. Salta líneas vacías."""
    for linea in stream:
        if len(linea.encode('utf-8') if isinstance(linea, str) else linea) > max_bytes:
            raise MessageTooLarge(f'línea de más de {max_bytes} bytes')
        if linea.strip():
            yield decode(linea)


class StdioTransport:
    """Lee y escribe JSONL sobre flujos de texto. El límite incluye el salto de línea."""

    def __init__(self, reader: IO[str] | None = None, writer: IO[str] | None = None,
                 max_bytes: int = DEFAULT_MAX_BYTES):
        self.reader = reader if reader is not None else sys.stdin
        self.writer = writer if writer is not None else sys.stdout
        self.max_bytes = max_bytes

    def send(self, message: Mapping[str, Any]) -> None:
        linea = encode(message)
        if len(linea.encode('utf-8')) > self.max_bytes:
            raise MessageTooLarge(f'mensaje de más de {self.max_bytes} bytes')
        self.writer.write(linea)
        self.writer.flush()

    def receive(self) -> dict[str, Any] | None:
        """El siguiente mensaje, o ``None`` en EOF (que equivale a ``close``)."""
        while True:
            linea = self.reader.readline()
            if not linea:
                return None
            if len(linea.encode('utf-8')) > self.max_bytes:
                raise MessageTooLarge(f'línea de más de {self.max_bytes} bytes')
            if linea.strip():
                return decode(linea)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        while (m := self.receive()) is not None:
            yield m

    @classmethod
    def in_memory(cls, text: str = '') -> 'StdioTransport':
        """Transporte sobre cadenas, útil en pruebas."""
        return cls(io.StringIO(text), io.StringIO())
