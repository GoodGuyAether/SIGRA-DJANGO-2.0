"""Best-effort DOCX to PDF conversion through LibreOffice."""
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


def _buscar_libreoffice() -> str | None:
    configured = os.environ.get("LIBREOFFICE_BIN")
    if configured:
        return configured if Path(configured).exists() or shutil.which(configured) else None

    candidates = ["soffice", "libreoffice"]
    if sys.platform.startswith("win"):
        candidates.extend(
            [
                r"C:\\Program Files\\LibreOffice\\program\\soffice.exe",
                r"C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",
            ]
        )

    for candidate in candidates:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    return None


def convertir_a_pdf(path_docx: Path, output_dir: Path, timeout: int | None = None) -> Path | None:
    """Convert a DOCX into a PDF, returning ``None`` when conversion is unavailable."""
    binary = _buscar_libreoffice()
    if not binary:
        logger.warning("No se encontró LibreOffice; se entregará solamente el DOCX.")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    timeout = timeout if timeout is not None else settings.LIBREOFFICE_TIMEOUT
    command = [binary, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(path_docx)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        logger.warning("Falló la conversión a PDF: %s", error, exc_info=True)
        return None

    pdf_path = output_dir / f"{path_docx.stem}.pdf"
    if result.returncode != 0 or not pdf_path.exists():
        logger.warning(
            "LibreOffice no pudo convertir %s (código %s). stderr: %s",
            path_docx,
            result.returncode,
            result.stderr.strip(),
        )
        return None
    return pdf_path
