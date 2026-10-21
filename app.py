# ──────────────────────────────────────────────────────────────────────────────
# app.py  –  Servidor web Flask del generador de firmas de email
#
# Rutas:
#   GET  /           → muestra el formulario
#   POST /generate   → genera la firma y devuelve la página de descarga
# ──────────────────────────────────────────────────────────────────────────────

import base64
import io
import json
from pathlib import Path

from flask import Flask, render_template, request
from PIL import Image

from signature_generator import generate_signature

app = Flask(__name__)

# Límite de subida: 10 MB (para admitir GIFs animados pesados)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# Carpeta donde se guardan los logos de cada empresa
EMPRESAS_DIR  = Path(__file__).parent / "empresas"

# JSON con la URL asociada a cada empresa  →  { "NombreEmpresa": "https://..." }
EMPRESAS_JSON = Path(__file__).parent / "empresas.json"

# Extensiones de imagen admitidas para los logos
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _load_urls() -> dict[str, str]:
    """
    Lee empresas.json y devuelve un diccionario con las claves en minúsculas
    para poder hacer búsquedas sin distinguir mayúsculas.
    Ejemplo: {"grupoxtra": "https://grupoxtra.es/", ...}
    """
    if not EMPRESAS_JSON.exists():
        return {}
    data = json.loads(EMPRESAS_JSON.read_text(encoding="utf-8"))
    return {k.lower(): v for k, v in data.items()}


def get_empresas() -> list[tuple[str, str]]:
    """
    Escanea la carpeta /empresas y devuelve una lista de tuplas
    (nombre_a_mostrar, nombre_de_archivo) ordenadas alfabéticamente.
    El nombre mostrado en el selector es el nombre del fichero sin extensión.
    """
    if not EMPRESAS_DIR.exists():
        return []
    return sorted(
        (f.stem, f.name)
        for f in EMPRESAS_DIR.iterdir()
        if f.suffix.lower() in _IMAGE_EXTS
    )


# ── Rutas ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Muestra el formulario de creación de firma."""
    urls = _load_urls()
    # empresa_urls se pasa como JSON para que el JS del formulario
    # pueda autorellenar el campo 'Sitio web' al cambiar la empresa
    return render_template("index.html", empresas=get_empresas(), empresa_urls=json.dumps(urls))


@app.route("/generate", methods=["POST"])
def generate():
    """Recibe el formulario, genera la imagen de firma y devuelve la página de descarga."""

    # Si el campo 'website' llega vacío, lo rellenamos automáticamente
    # con la URL configurada en empresas.json para la empresa seleccionada
    empresa_stem = Path(request.form.get("empresa", "")).stem.lower()
    website = request.form.get("website", "").strip()
    if not website and empresa_stem:
        website = _load_urls().get(empresa_stem, "")

    # Datos del formulario que se usarán para pintar el texto de la firma
    data = {
        "name":      request.form.get("name", ""),
        "cargo":     request.form.get("cargo", ""),
        "departamento":    request.form.get("departamento", ""),
        "sede":      request.form.get("sede", ""),
        "phone":     request.form.get("phone", ""),
        "extension": request.form.get("extension", ""),
        "email":     request.form.get("email", ""),
        "website":   website,
    }

    # Carga el logo de la empresa seleccionada desde la carpeta /empresas
    # Path(...).name elimina cualquier "../" para evitar path traversal
    photo_bytes = None
    empresa_file = Path(request.form.get("empresa", "")).name
    if empresa_file:
        empresa_path = EMPRESAS_DIR / empresa_file
        if empresa_path.is_file() and empresa_path.suffix.lower() in _IMAGE_EXTS:
            photo_bytes = empresa_path.read_bytes()

    # Genera los frames de la firma (más de uno si el logo es un GIF animado)
    frames, durations, is_animated = generate_signature(data, photo_bytes)

    buf = io.BytesIO()

    if is_animated:
        # GIF animado: cada frame se cuantiza a 256 colores (límite del formato GIF)
        # dither=NONE evita el tramado que difumina los textos
        gif_frames = [
            f.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            for f in frames
        ]
        gif_frames[0].save(
            buf,
            format="GIF",
            save_all=True,
            append_images=gif_frames[1:],
            loop=0,           # 0 = repetir infinitamente
            duration=durations,
            optimize=False,
        )
        mime     = "image/gif"
        filename = "firma_email.gif"
    else:
        # Imagen estática: se guarda como PNG de alta calidad
        frames[0].save(buf, format="PNG", optimize=True)
        mime     = "image/png"
        filename = "firma_email.png"

    # Codifica la imagen en base64 para incrustarla directamente en el HTML
    # (evita guardar ficheros temporales en el servidor)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    return render_template("result.html", img_b64=img_b64, mime=mime, filename=filename)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
