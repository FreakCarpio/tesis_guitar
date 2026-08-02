"""
Canciones Service - Proxy centralizado de proveedores externos (Song Detail).

Toda la integración con Songsterr e iTunes pasa por aquí (nunca desde
Android): centraliza la lógica, aplica caché en MongoDB, desacopla el
cliente del proveedor y permite cambiar de fuente sin tocar la app.

Fuentes y qué aporta cada una (verificado empíricamente):
- Songsterr /api/songs?pattern&size&from : búsqueda paginada
- Songsterr /api/meta/{songId}           : metadata, pistas, afinación,
                                           dificultad, tags, videos, deep-link
- Songsterr /api/chords/{songId}         : 200 si la canción tiene hoja de
                                           acordes de la comunidad, 404 si no
- Songsterr página de acordes (SSR)      : la hoja ChordPro completa viaja
                                           embebida como JSON en el estado
                                           servido de /a/wsa/…-chords-s{id}
                                           (secciones, acordes por línea de
                                           letra, afinación y capo)
- iTunes Search API (sin key)            : portada real, género, duración

No disponibles en ninguna fuente gratuita (se omiten): tempo, tonalidad.
La TABLATURA (nota a nota) sí sigue tras un CDN firmado: solo deep-link.
"""

import http.client
import json
import urllib.parse
from datetime import datetime, timedelta, timezone

import requests

from database import acordes_cache, busqueda_cache, cancion_cache

SONGSTERR_BASE = "https://www.songsterr.com"
ITUNES_BASE = "https://itunes.apple.com"
TIMEOUT_SEG = 8

# TTLs de caché (la portada/metadata de una canción no cambia a diario).
TTL_DETALLE = timedelta(days=7)
TTL_BUSQUEDA = timedelta(hours=6)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _cache_vigente(doc: dict | None, ttl: timedelta) -> bool:
    if not doc:
        return False
    try:
        fecha = datetime.fromisoformat(doc["fecha"])
    except (KeyError, ValueError):
        return False
    return _ahora() - fecha < ttl


def _midi_a_nota(midi: int) -> str:
    return NOTE_NAMES[((midi % 12) + 12) % 12] + str(midi // 12 - 1)


def _afinacion_texto(tuning: list | None) -> str | None:
    """Afinación legible de grave a agudo (la API la entrega de agudo a grave)."""
    if not tuning:
        return None
    return " ".join(_midi_a_nota(int(m)) for m in reversed(tuning))


def _dificultad_texto(nivel) -> str | None:
    return {0: "Fácil", 1: "Intermedio", 2: "Avanzado", 3: "Avanzado"}.get(nivel)


# --------------------------------------------------------------------------
# Songsterr
# --------------------------------------------------------------------------

def buscar_canciones(patron: str, size: int = 10, desde: int = 0) -> dict:
    """Búsqueda paginada en Songsterr, con caché de 6 h por (patrón, página)."""
    patron = patron.strip().lower()
    size = max(1, min(50, size))
    desde = max(0, desde)
    clave = f"{patron}|{size}|{desde}"

    doc = busqueda_cache.find_one({"clave": clave})
    if _cache_vigente(doc, TTL_BUSQUEDA):
        return doc["data"]

    r = requests.get(
        f"{SONGSTERR_BASE}/api/songs",
        params={"pattern": patron, "size": size, "from": desde},
        timeout=TIMEOUT_SEG,
    )
    r.raise_for_status()
    crudo = r.json()

    canciones = []
    for s in crudo:
        if s.get("isJunk"):
            continue
        tracks = s.get("tracks", [])
        track_def = tracks[s.get("defaultTrack", 0)] if 0 <= s.get("defaultTrack", 0) < len(tracks) else None
        canciones.append({
            "song_id": s["songId"],
            "titulo": s.get("title", ""),
            "artista": s.get("artist", ""),
            "dificultad": _dificultad_texto((track_def or {}).get("difficulty")),
            "tiene_acordes": bool(s.get("hasChords")),
            "tiene_player": bool(s.get("hasPlayer")),
            "pistas": len(tracks),
        })

    data = {
        "canciones": canciones,
        "cantidad": len(canciones),
        "desde": desde,
        "size": size,
        # Songsterr no informa el total; si vino la página llena, hay más.
        "hay_mas": len(crudo) >= size,
    }
    busqueda_cache.update_one(
        {"clave": clave},
        {"$set": {"clave": clave, "data": data, "fecha": _ahora().isoformat()}},
        upsert=True,
    )
    return data


def _songsterr_meta(song_id: int) -> dict | None:
    r = requests.get(f"{SONGSTERR_BASE}/api/meta/{song_id}", timeout=TIMEOUT_SEG)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


# --------------------------------------------------------------------------
# iTunes (portada, género, duración)
# --------------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    return "".join(c for c in texto.lower() if c.isalnum() or c == " ").strip()


def _itunes_enriquecer(artista: str, titulo: str) -> dict:
    """Busca la canción en iTunes y devuelve portada/género/duración.

    Valida que el artista coincida (contención normalizada) para no colgar
    la portada de otra canción. Si no hay match confiable, devuelve vacío.
    """
    try:
        r = requests.get(
            f"{ITUNES_BASE}/search",
            params={"term": f"{artista} {titulo}", "entity": "song", "limit": 5},
            timeout=TIMEOUT_SEG,
        )
        r.raise_for_status()
        resultados = r.json().get("results", [])
    except requests.RequestException:
        return {}

    art_norm = _normalizar(artista)
    for res in resultados:
        cand = _normalizar(res.get("artistName", ""))
        if art_norm and cand and (art_norm in cand or cand in art_norm):
            portada = res.get("artworkUrl100", "")
            return {
                "portada": portada.replace("100x100bb", "600x600bb") or None,
                "genero": res.get("primaryGenreName"),
                "duracion_seg": int(res["trackTimeMillis"] / 1000) if res.get("trackTimeMillis") else None,
                "album": res.get("collectionName"),
            }
    return {}


# --------------------------------------------------------------------------
# Detalle compuesto
# --------------------------------------------------------------------------

def obtener_detalle(song_id: int, forzar: bool = False) -> dict | None:
    """Detalle unificado de una canción (Songsterr + iTunes), cacheado 7 días.

    Devuelve None si la canción no existe en Songsterr.
    """
    doc = cancion_cache.find_one({"song_id": song_id})
    if not forzar and _cache_vigente(doc, TTL_DETALLE):
        return doc["data"]

    meta = _songsterr_meta(song_id)
    if meta is None:
        return None

    artista = meta.get("artist", "")
    titulo = meta.get("title", "")
    itunes = _itunes_enriquecer(artista, titulo)

    tracks = [t for t in meta.get("tracks", []) if not t.get("isEmpty")]
    pistas = [
        {
            "instrumento": t.get("instrument", ""),
            "nombre": t.get("name"),
            "afinacion": _afinacion_texto(t.get("tuning")),
            "dificultad": _dificultad_texto(t.get("difficulty")),
            "es_voz": bool(t.get("isVocalTrack")),
            "vistas": t.get("views"),
        }
        for t in tracks
    ]
    idx_def = meta.get("defaultTrack", 0)
    if not (0 <= idx_def < len(pistas)):
        idx_def = 0
    pista_def = pistas[idx_def] if pistas else None

    videos = [
        v["videoId"]
        for v in (meta.get("videos") or [])
        if v.get("status") == "done" and v.get("videoId")
    ]

    detalle = {
        "song_id": song_id,
        "titulo": titulo,
        "artista": artista,
        # Enriquecimiento iTunes (None si no hubo match confiable).
        "portada": itunes.get("portada"),
        "genero": itunes.get("genero"),
        "duracion_seg": itunes.get("duracion_seg"),
        "album": itunes.get("album"),
        # Metadata Songsterr.
        "afinacion": (pista_def or {}).get("afinacion"),
        "dificultad": (pista_def or {}).get("dificultad"),
        "tiene_acordes": bool(meta.get("hasChords")),
        "tiene_player": bool(meta.get("hasPlayer")),
        "descripcion": (meta.get("description") or "").strip() or None,
        "autor": (meta.get("author") or {}).get("name"),
        "vistas": meta.get("views"),
        "favoritos": meta.get("favoritesCount"),
        "tags": (meta.get("tags") or [])[:10],
        "pistas": pistas,
        "pista_default": idx_def,
        "videos": videos[:3],
        # Tablatura/acordes: solo deep-link (CDN firmado de Songsterr).
        "enlace_tab": f"{SONGSTERR_BASE}/a/wa/song?id={song_id}",
        "fuentes": {"songsterr": True, "itunes": bool(itunes)},
    }

    cancion_cache.update_one(
        {"song_id": song_id},
        {"$set": {"song_id": song_id, "data": detalle, "fecha": _ahora().isoformat()}},
        upsert=True,
    )
    return detalle


# --------------------------------------------------------------------------
# Acordes reales (hoja de acordes de la comunidad Songsterr)
# --------------------------------------------------------------------------

def _obtener_html(url: str, max_redirects: int = 3) -> str | None:
    """GET de una página HTML de Songsterr saltando respuestas 1xx.

    Cloudflare antepone "103 Early Hints" al 200 de las páginas (no de la
    API JSON) y el http.client de Python —el que usan requests/urllib—
    trata ese 103 como respuesta final con cuerpo vacío. Aquí se leen los
    estados informativos hasta llegar a la respuesta real y se siguen los
    redirects del slug canónico. Devuelve None si no se llega a un 200.
    """
    for _ in range(max_redirects + 1):
        parte = urllib.parse.urlsplit(url)
        conn = http.client.HTTPSConnection(parte.netloc, timeout=TIMEOUT_SEG)
        try:
            ruta = parte.path + (f"?{parte.query}" if parte.query else "")
            conn.request("GET", ruta, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html",
                "Accept-Encoding": "identity",
            })
            resp = conn.getresponse()
            while 100 <= resp.status < 200:
                # 1xx no lleva cuerpo: la respuesta real sigue en el socket.
                resp.read()
                resp = http.client.HTTPResponse(conn.sock, method="GET")
                resp.begin()
            if resp.status in (301, 302, 303, 307, 308):
                destino = resp.getheader("Location")
                if not destino:
                    return None
                url = urllib.parse.urljoin(url, destino)
                continue
            if resp.status != 200:
                return None
            return resp.read().decode("utf-8", errors="replace")
        except (OSError, http.client.HTTPException):
            return None
        finally:
            conn.close()
    return None


def _nombre_acorde(chord: dict) -> str | None:
    """Nombre legible de un acorde del ChordPro de Songsterr:
    baseNote + sufijo (+ bajo si es acorde con inversión): Em7, G, D/F#."""
    base = (chord.get("baseNote") or {}).get("name")
    if not base:
        return None
    nombre = base + ((chord.get("chordType") or {}).get("suffix") or "")
    bajo = (chord.get("firstNote") or {}).get("name")
    if bajo and bajo != base:
        nombre += f"/{bajo}"
    return nombre


def _extraer_chordpro(html: str) -> list | None:
    """Extrae el array de tokens ChordPro embebido en el estado SSR de la
    página de acordes ("chordpro":{"current":[…]}). None si no aparece."""
    marca = '"chordpro":{"current":'
    i = html.find(marca)
    if i < 0:
        return None
    j = html.find("[", i + len(marca) - 1)
    if j < 0:
        return None
    try:
        tokens, _ = json.JSONDecoder().raw_decode(html, j)
    except ValueError:
        return None
    return tokens if isinstance(tokens, list) else None


def _parsear_chordpro(tokens: list) -> dict | None:
    """Convierte los tokens ChordPro en el contenido de práctica:

    secciones [{nombre, lineas:[{texto, acorde}]}] respetando el ORDEN real
    (cada acorde de una línea sale como línea propia con el fragmento de
    letra que le sigue), más afinación, capo y la progresión (acordes
    únicos en orden de aparición). None si no hay ningún acorde."""
    secciones: list[dict] = []
    actual: dict | None = None
    afinacion: str | None = None
    capo: int | None = None
    progresion: list[str] = []

    for token in tokens:
        tipo = token.get("type")
        if tipo == "tuning":
            afinacion = token.get("text") or None
        elif tipo == "capo":
            try:
                capo = int(token.get("text"))
            except (TypeError, ValueError):
                pass
        elif tipo == "section":
            actual = {"nombre": token.get("text") or f"Parte {len(secciones) + 1}",
                      "lineas": []}
            secciones.append(actual)
        elif tipo == "line":
            if actual is None:
                actual = {"nombre": "Canción", "lineas": []}
                secciones.append(actual)
            texto_previo = ""
            hubo_acorde = False
            for bloque in token.get("line") or []:
                if bloque.get("type") == "chord":
                    nombre = _nombre_acorde(bloque.get("chord") or {})
                    if nombre is None:
                        continue
                    # El texto suelto ANTES del primer acorde de la línea se
                    # arrastra a la línea de ese acorde (no cambia el orden).
                    actual["lineas"].append({"texto": texto_previo, "acorde": nombre})
                    texto_previo = ""
                    hubo_acorde = True
                    if nombre not in progresion:
                        progresion.append(nombre)
                elif bloque.get("type") == "text":
                    trozo = bloque.get("text") or ""
                    if hubo_acorde:
                        actual["lineas"][-1]["texto"] += trozo
                    else:
                        texto_previo += trozo
            if not hubo_acorde and texto_previo.strip():
                actual["lineas"].append({"texto": texto_previo, "acorde": None})

    secciones = [s for s in secciones if s["lineas"]]
    if not progresion or not secciones:
        return None
    for s in secciones:
        for linea in s["lineas"]:
            linea["texto"] = linea["texto"].strip()
    return {
        "secciones": secciones,
        "progresion": progresion,
        "afinacion": afinacion,
        "capo": capo,
    }


def obtener_acordes(song_id: int) -> dict | None:
    """Acordes REALES de una canción (hoja de la comunidad Songsterr),
    cacheados 7 días. Devuelve None si la canción no tiene acordes
    publicados; los fallos transitorios de red/parseo NO se cachean (para
    no marcar como inexistente algo que sí existe)."""
    doc = acordes_cache.find_one({"song_id": song_id})
    if _cache_vigente(doc, TTL_DETALLE):
        return doc["data"] or None

    r = requests.get(f"{SONGSTERR_BASE}/api/chords/{song_id}", timeout=TIMEOUT_SEG)
    if r.status_code == 404:
        # Confirmado por el proveedor: esta canción NO tiene acordes.
        acordes_cache.update_one(
            {"song_id": song_id},
            {"$set": {"song_id": song_id, "data": None, "fecha": _ahora().isoformat()}},
            upsert=True,
        )
        return None
    r.raise_for_status()

    # El slug del artista/título se resuelve solo: cualquier slug con el
    # songId correcto redirige a la página canónica.
    html = _obtener_html(f"{SONGSTERR_BASE}/a/wsa/song-chords-s{song_id}")
    tokens = _extraer_chordpro(html) if html else None
    data = _parsear_chordpro(tokens) if tokens else None
    if data is None:
        # Había hoja según la API pero no se pudo extraer: no cachear.
        return None

    acordes_cache.update_one(
        {"song_id": song_id},
        {"$set": {"song_id": song_id, "data": data, "fecha": _ahora().isoformat()}},
        upsert=True,
    )
    return data
