# Generador de firmas de correo

Aplicación web en Flask para crear una firma de correo corporativa como imagen. La persona usuaria completa un formulario, elige uno de los logos disponibles y descarga el resultado listo para insertarlo en su cliente de correo.

La aplicación no requiere base de datos ni guarda las firmas generadas: construye la imagen en memoria, la muestra en la respuesta y permite descargarla desde el navegador.

## Características

- Formulario en español para los datos de contacto profesionales.
- Catálogo de empresas configurable mediante imágenes locales y un archivo JSON de URLs.
- URL corporativa autocompletada y bloqueada al elegir una empresa configurada.
- Salida PNG para firmas con logo estático y GIF para logos con varios fotogramas.
- Conservación de la animación y la transparencia de los logos al generar GIF.
- Diseño compacto de 500 × 200 píxeles, con logo, separador vertical y texto.
- Instrucciones de inserción para Gmail, Outlook y Apple Mail después de generar la firma.
- Sin almacenamiento temporal de los datos personales ni de las imágenes resultantes en el servidor.

## Cómo funciona

```text
Formulario web → Flask reúne los datos → Pillow compone la firma
       ↑                                                   ↓
 Logos y URL de empresa                          Base64 en la respuesta
                                                       ↓
                                            Vista previa y descarga
```

1. La ruta `GET /` busca las imágenes admitidas en `empresas/`, las ordena por nombre y muestra el formulario.
2. Al seleccionar una empresa, el JavaScript del navegador consulta las URL de `empresas.json`. Si encuentra una, rellena el campo **Sitio web** y lo deja en solo lectura.
3. Al enviar el formulario a `POST /generate`, el servidor vuelve a resolver la URL si el campo llega vacío, carga el logo seleccionado y llama a `generate_signature()`.
4. Pillow dibuja el texto y el logo sobre un lienzo blanco. Si el logo tiene más de un fotograma, se compone un fotograma de firma por cada uno.
5. El resultado se codifica en Base64 y se incrusta directamente en la página de resultado. El enlace de descarga usa esa misma imagen; no se crea ningún archivo de firma en el disco del servidor.

## Requisitos

- Python 3.9 o posterior.
- `pip`.
- Dependencias definidas en `requirements.txt`:
  - Flask 3 o posterior.
  - Pillow 10 o posterior.

Para una renderización de texto de mejor calidad en Linux, se recomienda tener instalada una fuente TrueType compatible, preferiblemente DejaVu Sans. La aplicación prueba DejaVu Sans, Liberation Sans y FreeSans; si no encuentra ninguna, Pillow utiliza su fuente interna.

En Debian/Ubuntu se puede instalar DejaVu Sans con:

```bash
sudo apt-get install fonts-dejavu-core
```

La interfaz carga Bootstrap 5.3.2 desde CDN, por lo que se necesita conexión a internet para aplicar sus estilos estándar. La generación de la firma no utiliza servicios externos.

## Instalación y ejecución local

Desde la raíz del proyecto:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

En Windows PowerShell, la activación del entorno es:

```powershell
.\venv\Scripts\Activate.ps1
```

Abre [http://localhost:5000](http://localhost:5000) en el navegador. El servidor de desarrollo escucha en el puerto `5000` y, tal como está configurado el proyecto, en todas las interfaces (`0.0.0.0`).

## Uso de la aplicación

1. Elige una empresa o **Sin imagen**.
2. Escribe el nombre completo; es el único campo obligatorio en la interfaz.
3. Añade, si corresponde, cargo, departamento, sede, teléfono, extensión, correo y sitio web.
4. Pulsa **Generar firma**.
5. Revisa la vista previa y descarga `firma_email.png` o `firma_email.gif`.
6. Inserta el archivo descargado como imagen en la configuración de firma de tu cliente de correo.

La página de resultado incluye una guía rápida para Gmail, Outlook y Apple Mail.

### Campos del formulario

| Campo | Comportamiento en la firma |
| --- | --- |
| Empresa | Determina el logo. Si no se selecciona, se genera una firma solo de texto. |
| Nombre completo | Se muestra en negrita. Es obligatorio en el navegador. |
| Cargo y departamento | Se unen como `Cargo \| Departamento`; el texto se ajusta a varias líneas si hace falta. |
| Sede | Se muestra en una línea secundaria si tiene valor. |
| Teléfono | La aplicación añade el prefijo `(+34)` automáticamente. Introduce el número nacional, por ejemplo `618 786 007`, para no duplicarlo. |
| Extensión | Se añade como `Ext. N` solo cuando también existe teléfono. |
| Correo electrónico | Se dibuja como texto en la firma. |
| Sitio web | Se rellena desde `empresas.json` para las empresas configuradas. Con **Sin imagen** o una empresa sin URL asociada, se puede editar manualmente. |

Como el resultado es una imagen, la dirección de correo, el teléfono y la URL no son enlaces interactivos.

## Formatos y resultado

Los logos disponibles deben tener extensión `.jpg`, `.jpeg`, `.png`, `.gif` o `.webp`. El tamaño máximo de la solicitud HTTP es de 10 MB, configurado para poder manejar logos animados de cierto tamaño.

- Un logo de un solo fotograma genera `firma_email.png` (`image/png`).
- Un logo con varios fotogramas genera `firma_email.gif` (`image/gif`), que se repite indefinidamente.
- Los GIF de salida se cuantizan a 256 colores, una limitación propia del formato GIF. Se desactiva el dithering para mantener el texto nítido.
- Los logos se redimensionan manteniendo proporción hasta un máximo de 160 × 100 píxeles.

La firma se compone siempre sobre fondo blanco y mide 500 × 200 píxeles. Cuando hay logo, aparece a la derecha de una línea vertical gris; sin logo, el texto ocupa el ancho disponible. Para evitar que el contenido se corte, conviene usar textos breves, especialmente en el nombre, el cargo y el departamento.

## Estructura del proyecto

```text
.
├── app.py                    # Rutas Flask, catálogo de empresas y respuesta web
├── signature_generator.py    # Composición de la firma con Pillow
├── empresas.json             # Mapa nombre de empresa → URL corporativa
├── empresas/                 # Logos disponibles en el selector
├── templates/
│   ├── index.html            # Formulario y autocompletado de URL
│   └── result.html           # Vista previa, descarga e instrucciones de uso
├── static/css/style.css      # Ajustes visuales propios sobre Bootstrap
├── requirements.txt          # Dependencias de Python
└── LICENSE                   # Licencia MIT
```

## Personalizar empresas y logos

El selector no permite subir logos desde el navegador. Los logos se administran en el repositorio para que todas las firmas empleen la imagen corporativa correcta.

### Añadir o reemplazar un logo

1. Copia el archivo de imagen a `empresas/` con una extensión admitida.
2. El nombre visible en el selector será el nombre del archivo sin extensión. Por ejemplo, `empresas/MiEmpresa.png` se mostrará como `MiEmpresa`.
3. Añade la URL asociada en `empresas.json` si quieres que se autocompleten el sitio web y el campo quede bloqueado:

```json
{
  "MiEmpresa": "https://www.miempresa.example/"
}
```

La clave del JSON debe coincidir con el nombre base del archivo; la comparación no distingue mayúsculas de minúsculas. Mantén las demás entradas existentes al editar el fichero. Reinicia el servidor si se está ejecutando sin recarga automática.

Las empresas incluidas actualmente son `Aetherium`, `Nodosia` y `Vortex`; sus nombres visibles proceden de los archivos de logo, mientras que `empresas.json` contiene los nombres completos y sus URL. **En el estado actual, esas claves no coinciden**, por lo que el autocompletado de URL no se activa para esos tres logos. Para habilitarlo, renombra las claves del JSON como `Aetherium`, `Nodosia` y `Vortex`, o cambia los nombres de los archivos para que coincidan. Si se cambia uno, cambia el otro en consecuencia.

### Modificar el diseño de la firma

Los ajustes de composición están centralizados en `signature_generator.py`:

- `_BOLD_FONTS` y `_REGULAR_FONTS` establecen el orden de fuentes.
- `PHOTO_SZ` define el tamaño máximo del logo.
- `W`, `H`, `PAD` y los valores `GAP_*` de `_render_frame()` controlan el lienzo, márgenes y separación.
- `accent` y `bg_color` definen, respectivamente, el color de los datos de contacto y el fondo; en la versión actual ambos son negro y blanco.
- `_wrap_text()` ajusta solamente el bloque de cargo y departamento al ancho de texto disponible.

Tras cambiar esos valores, genera una firma de ejemplo para comprobar que el contenido cabe bien y que mantiene una apariencia consistente en el cliente de correo objetivo.

## Detalle técnico

### Rutas HTTP

| Método y ruta | Responsabilidad |
| --- | --- |
| `GET /` | Renderiza `index.html` con la lista de logos y el mapa de URL. |
| `POST /generate` | Lee los datos, verifica el nombre de archivo del logo, genera la imagen y renderiza `result.html`. |

`app.py` usa `Path(...).name` antes de acceder al logo seleccionado, de modo que solo se utiliza el nombre de archivo dentro de `empresas/` y se evita recorrer directorios mediante el valor enviado en el formulario.

La función pública de generación es:

```python
generate_signature(data, photo_bytes=None)
# devuelve: (frames, durations_ms, is_animated)
```

`frames` contiene una imagen Pillow por fotograma; `durations_ms` conserva la duración de los fotogramas del logo cuando aplica; `is_animated` decide si la respuesta se serializa como PNG o GIF.

## Desarrollo y despliegue

No hay una suite de pruebas automatizada incluida. Para una comprobación manual, inicia el servidor, genera una firma con y sin empresa y confirma que la descarga y la vista previa corresponden al formato esperado.

`python3 app.py` activa `debug=True`, por lo que es adecuado únicamente para desarrollo. Para producción, ejecuta la aplicación con un servidor WSGI y desactiva el modo de depuración. Por ejemplo, tras instalar Gunicorn como dependencia de despliegue:

```bash
gunicorn --bind 0.0.0.0:5000 app:app
```

La configuración de proxy inverso, TLS, registros y supervisión no forma parte de este repositorio y debe proporcionarla el entorno de despliegue.

## Limitaciones actuales

- No hay autenticación, cuentas de usuario ni historial de firmas.
- No se admiten logos personalizados desde el formulario; hay que añadirlos en `empresas/`.
- Los campos se rasterizan en una imagen y no producen enlaces clicables ni texto seleccionable.
- El diseño está pensado para datos cortos y un logo corporativo compacto.
- La validación de campos en el navegador es básica; los datos deben revisarse antes de compartir la firma.

## Licencia

Este proyecto se distribuye bajo la [licencia MIT](LICENSE).
