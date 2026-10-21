# ──────────────────────────────────────────────────────────────────────────────
# signature_generator.py  –  Generación de la imagen de firma con Pillow
#
# Función principal:
#   generate_signature(data, photo_bytes) → (frames, durations, is_animated)
#
# El ancho del canvas se calcula dinámicamente según el texto real,
# de forma que el separador y el logo queden justos al lado del contenido.
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import io
import subprocess
import unicodedata
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageSequence

# Rutas de fuentes en orden de preferencia (se usa la primera que exista)
# Si ninguna está disponible, Pillow cae en su fuente bitmap interna
_BOLD_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    
]

_REGULAR_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    
]


def _load_font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    """Carga DejaVu Sans del sistema Debian o la primera fuente disponible."""
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue

    # En Debian, fontconfig encuentra la fuente instalada incluso cuando está
    # en una ruta distinta de la habitual.
    style = "Bold" if paths is _BOLD_FONTS else "Regular"
    try:
        match = subprocess.run(
            ["fc-match", "-f", "%{file}", f"DejaVu Sans:style={style}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        ).stdout.strip()
        if match:
            return ImageFont.truetype(match, size)
    except (OSError, subprocess.SubprocessError):
        pass

    # Pillow's scalable built-in font keeps the requested size and supports
    # accented Spanish characters even when no system fonts are installed.
    return ImageFont.load_default(size=size)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convierte un color hexadecimal (#RRGGBB) a tupla RGB."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """
    Divide el texto en líneas que caben dentro de max_width píxeles.
    Usa draw.textlength() para medir el ancho real con la fuente dada.
    """
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _measure_text(draw, candidate, font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _uses_unicode_fallback(font) -> bool:
    """True when the fallback font maps Spanish accents to its missing glyph."""
    try:
        return bytes(font.getmask("á")) == bytes(font.getmask("?"))
    except (AttributeError, TypeError):
        return False


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font) -> float:
    if not _uses_unicode_fallback(font):
        return draw.textlength(text, font=font)
    plain = "".join(ch for ch in unicodedata.normalize("NFD", text)
                    if not unicodedata.combining(ch))
    return draw.textlength(plain, font=font)


def _draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
               font, fill, stroke_width: int = 0) -> None:
    """Draw Spanish diacritics manually if the installed fallback lacks them."""
    if not _uses_unicode_fallback(font):
        draw.text(xy, text, font=font, fill=fill, stroke_width=stroke_width,
                  stroke_fill=fill)
        return

    x, y = xy
    for char in text:
        decomposed = unicodedata.normalize("NFD", char)
        base = decomposed[0]
        marks = decomposed[1:]
        draw.text((x, y), base, font=font, fill=fill, stroke_width=stroke_width,
                  stroke_fill=fill)
        bbox = draw.textbbox((x, y), base, font=font, stroke_width=stroke_width)
        width = max(1, bbox[2] - bbox[0])
        for mark in marks:
            if mark == "\u0301":  # acute accent
                draw.line((x + width * .48 - 1, y + 1, x + width * .48 + 1, y - 2),
                          fill=fill, width=1)
            elif mark == "\u0303":  # tilde
                draw.line((x + width * .25, y, x + width * .5, y - 2,
                           x + width * .75, y), fill=fill, width=1)
            elif mark == "\u0308":  # diaeresis
                draw.point((x + width * .38, y - 1), fill=fill)
                draw.point((x + width * .62, y - 1), fill=fill)
        x += draw.textlength(base, font=font) + stroke_width * 2


def _render_frame(
    data: dict,
    photo: Optional[Image.Image],
    accent: tuple,
    fonts: tuple,
    bg_color: tuple = (255, 255, 255),
) -> Image.Image:
    """Genera un frame de la firma con canvas de tamaño fijo."""
    W   = 500        # ancho aproximado de la referencia
    H   = 200        # alto fijo en píxeles
    PAD = 20          # margen exterior
    GAP_TEXT_SEP = 20 # espacio entre el texto y la línea separadora
    GAP_SEP_IMG  = 22  # espacio entre la línea separadora y el logo

    f_name, f_title, f_regular, f_small = fonts

    # Extraer y limpiar todos los campos de texto
    name      = data.get("name",      "").strip()
    cargo     = data.get("cargo",     "").strip()
    departamento    = data.get("departamento",    "").strip()
    # Cargo y título se muestran unidos con un separador visual.
    title = " | ".join(filter(None, [cargo, departamento]))
    sede      = data.get("sede",      "").strip()
    phone_raw = data.get("phone", "").strip()
    phone     = f"(+34) {phone_raw}" if phone_raw else ""
    extension = data.get("extension", "").strip()
    email_v   = data.get("email",     "").strip()
    website   = data.get("website",   "").strip()

    phone_ext = f"{phone}  Ext. {extension}" if phone and extension else phone
    sede_txt  = f"{sede}" if sede else ""

    # Ancho reservado para el logo (si hay imagen)
    photo_w = photo.width if photo is not None else 0

    # Ancho disponible para el bloque de texto
    # Layout: [PAD] [texto] [GAP_TEXT_SEP] [1px sep] [GAP_SEP_IMG] [logo] [PAD]
    if photo is not None:
        # Columna de texto como en la referencia; evita empujar el separador
        # y el logo hasta el extremo derecho del lienzo.
        content_w = min(240, W - PAD - GAP_TEXT_SEP - 1 - GAP_SEP_IMG - photo_w - PAD)
    else:
        content_w = W - 2 * PAD

    content_w = max(content_w, 120)  # nunca menos de 120 px

    # Renderizar imagen
    img  = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    lum = 0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]
    text_primary   = (255, 255, 255) if lum < 128 else (15, 15, 15)
    text_secondary = (195, 195, 195) if lum < 128 else (90, 90, 90)
    sep_color      = (155, 155, 155) if lum < 128 else (200, 200, 200)

    sep_x = PAD + content_w + GAP_TEXT_SEP

    # Pegar el logo a la derecha del separador
    if photo is not None:
        px = sep_x + 1 + GAP_SEP_IMG
        py = (H - photo.height) // 2
        mask = photo.split()[3] if photo.mode == "RGBA" else None
        img.paste(photo.convert("RGB"), (px, py), mask=mask)
        draw.rectangle([sep_x, PAD, sep_x + 1, H - PAD], fill=sep_color)

    tx = PAD
    # Usar la caja real de cada fuente evita que las líneas se solapen.
    # Los incrementos fijos anteriores no tenían en cuenta el ascendente y
    # descendente de las fuentes TrueType.
    ty = PAD

    def draw_line(text: str, font, fill, spacing: int = 2, stroke_width: int = 0) -> None:
        nonlocal ty
        _draw_text(draw, (tx, ty), text, font, fill, stroke_width)
        bbox = draw.textbbox((tx, ty), text, font=font)
        ty += (bbox[3] - bbox[1]) + spacing

    if name:
        draw_line(name, f_name, text_primary, spacing=3, stroke_width=1)

    if title:
        for ln in _wrap_text(draw, title, f_title, content_w):
            draw_line(ln, f_title, text_secondary, spacing=2)

    if sede_txt:
        draw_line(sede_txt, f_small, text_secondary, spacing=2)

    if phone_ext:
        draw_line(phone_ext, f_regular, accent, spacing=3.5)

    if email_v:
        draw_line(email_v, f_small, accent, spacing=1)

    if website:
        draw_line(website, f_small, accent, spacing=1)

    return img


def generate_signature(
    data: dict, photo_bytes: Optional[bytes] = None
) -> tuple[list[Image.Image], list[int], bool]:
    """
    Punto de entrada principal. Devuelve (frames, durations_ms, is_animated).

    - Si photo_bytes es un GIF animado, genera un frame por cada frame del GIF.
    - Si es una imagen estática (JPG/PNG/etc.), genera un único frame.
    - Si no hay imagen, genera la firma solo con texto.
    """
    accent   = (0, 0, 0)       # color de texto de contacto: siempre negro
    bg_color = (255, 255, 255)  # fondo: siempre blanco

    # Referencia: nombre en negrita de 20 px; cargo en gris de 13 px;
    # sede, teléfono, correo y web en 12 px.
    fonts = (
        _load_font(_BOLD_FONTS,    20),
        _load_font(_REGULAR_FONTS,  13),
        _load_font(_REGULAR_FONTS,  12),
        _load_font(_REGULAR_FONTS,  12),
    )

    # Tamaño máximo del logo en píxeles (thumbnail mantiene la proporción)
    PHOTO_SZ = (160, 100)  # tamaño aproximado del logo en la referencia

    photo_frames: list[Image.Image] = []
    durations: list[int] = []
    is_animated = False

    if photo_bytes:
        try:
            src = Image.open(io.BytesIO(photo_bytes))
            n_frames = getattr(src, "n_frames", 1)
            is_animated = n_frames > 1  # GIF con más de un frame

            for frame in ImageSequence.Iterator(src):
                duration = frame.info.get("duration", 100)  # ms por frame
                # Convertir a RGBA para preservar la transparencia de los PNG
                f = frame.convert("RGBA")
                f.thumbnail(PHOTO_SZ, Image.LANCZOS)
                photo_frames.append(f)
                durations.append(duration)
        except Exception:
            pass  # imagen corrupta o formato no soportado → se ignora

    # Sin imagen: firma solo con texto
    if not photo_frames:
        return [_render_frame(data, None, accent, fonts, bg_color)], [100], False

    # Con imagen: un frame renderizado por cada frame del logo
    rendered = [_render_frame(data, pf, accent, fonts, bg_color) for pf in photo_frames]
    return rendered, durations, is_animated
