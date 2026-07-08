"""
Canciones Service - Proxy centralizado de proveedores externos (Song Detail).

Toda la integración con Songsterr e iTunes pasa por aquí (nunca desde
Android): centraliza la lógica, aplica caché en MongoDB, desacopla el
cliente del proveedor y permite cambiar de fuente sin tocar la app.

Fuentes y qué aporta cada una (verificado empíricamente):
- Songsterr /api/songs?pattern&size&from : búsqueda paginada
- Songsterr /api/meta/{songId}           : metadata, pistas, afinación,
                                           dificultad, tags, videos, deep-link
- iTunes Search API (sin key)            : portada real, género, duración

No disponibles en ninguna fuente gratuita (se omiten): tempo, tonalidad,
capo, letra, secciones. La tablatura/acordes reales viven tras un CDN
firmado de Songsterr: solo deep-link.
"""

from datetime import datetime, timedelta, timezone

import requests

from database import busqueda_cache, cancion_cache

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
