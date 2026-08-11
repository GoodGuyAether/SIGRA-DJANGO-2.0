"""Formatting helpers shared by document-generation workflows."""


def texto_en_mayusculas(valor: str) -> str:
    """Return a trimmed value in uppercase for resolution body text."""
    return " ".join(str(valor).split()).upper()


def nombre_en_titulo(valor: str) -> str:
    """Return a trimmed person name in title case."""
    return " ".join(str(valor).split()).title()
