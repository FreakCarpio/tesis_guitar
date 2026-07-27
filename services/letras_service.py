"""
Letras Service - Proxy de LRCLIB (letras de canciones) para la práctica
guiada de canciones.

LRCLIB (lrclib.net) es una base comunitaria de letras, gratuita y sin API
key. Aporta lo que Songsterr/iTunes no exponen: la letra en texto plano y,
cuando existe, la letra SINCRONIZADA (timestamp por línea), que permite el
desplazamiento automático estilo Yousician/Ultimate Guitar.

Igual que el resto de proveedores externos, TODA la integración pasa por
FastAPI con caché en MongoDB: Android nunca habla con lrclib.net.
"""

import re
from datetime import datetime, timedelta, timezone

import requests

from database import letra_cache

LRCLIB_BASE = "https://lrclib.net"
TIMEOUT_SEG = 8

# La letra de una canción no cambia: caché larga. Los "misses" se cachean
# poco tiempo por si la comunidad la sube después.
TTL_LETRA = timedelta(days=30)
TTL_SIN_LETRA = timedelta(days=2)

# "[mm:ss.xx] texto" (el estándar LRC que devuelve syncedLyrics).
_LRC_LINEA = re.compile(r"^\[(\d+):(\d+(?:\.\d+)?)\]\s?(.*)$")


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _cache_vigente(doc: dict | None) -> bool:
    if not doc:
        return False
    try:
        fecha = datetime.fromisoformat(doc["fecha"])
    except (KeyError, ValueError):
        return False
    ttl = TTL_LETRA if (doc.get("data") or {}).get("tiene_letra") else TTL_SIN_LETRA
    return _ahora() - fecha < ttl


def _parsear_sincronizada(synced: str) -> list[dict]:
    """Convierte un cuerpo LRC en líneas [{t_seg, texto}] ordenadas."""
    lineas = []
    for cruda in synced.splitlines():
        m = _LRC_LINEA.match(cruda.strip())
        if not m:
            continue
        minutos, segundos, texto = m.groups()
        lineas.append({
            "t_seg": round(int(minutos) * 60 + float(segundos), 2),
            "texto": texto.strip(),
        })
    lineas.sort(key=lambda l: l["t_seg"])
    return lineas


def _parsear_plana(plain: str) -> list[dict]:
    """Letra sin tiempos: [{t_seg: None, texto}], conservando líneas vacías
    (separan estrofas y definen las secciones)."""
    return [{"t_seg": None, "texto": l.strip()} for l in plain.splitlines()]


def _consultar_lrclib(artista: str, titulo: str, duracion_seg: int | None) -> dict | None:
    """GET /api/get exacto; si falla, /api/search y se toma el mejor match."""
    params = {"artist_name": artista, "track_name": titulo}
    if duracion_seg:
        params["duration"] = duracion_seg
    r = requests.get(f"{LRCLIB_BASE}/api/get", params=params, timeout=TIMEOUT_SEG)
    if r.status_code == 200:
        return r.json()

    r = requests.get(
        f"{LRCLIB_BASE}/api/search",
        params={"track_name": titulo, "artist_name": artista},
        timeout=TIMEOUT_SEG,
    )
    if r.status_code != 200:
        return None
    resultados = r.json() or []
    # Prefiere resultados con letra sincronizada; luego con letra plana.
    for res in resultados:
        if res.get("syncedLyrics"):
            return res
    for res in resultados:
        if res.get("plainLyrics"):
            return res
    return None


def obtener_letra(artista: str, titulo: str, duracion_seg: int | None = None) -> dict:
    """Letra de una canción vía LRCLIB, cacheada en Mongo.

    Devuelve:
      {
        "tiene_letra": bool,
        "sincronizada": bool,       # True si hay timestamps por línea
        "lineas": [{"t_seg": float|None, "texto": str}],
        "instrumental": bool,
      }
    Nunca lanza por errores del proveedor: sin letra => tiene_letra False.
    """
    clave = f"{artista.strip().lower()}|{titulo.strip().lower()}"
    doc = letra_cache.find_one({"clave": clave})
    if _cache_vigente(doc):
        return doc["data"]

    data = {"tiene_letra": False, "sincronizada": False, "lineas": [], "instrumental": False}
    try:
        res = _consultar_lrclib(artista, titulo, duracion_seg)
        if res:
            if res.get("instrumental"):
                data["instrumental"] = True
            synced = res.get("syncedLyrics")
            plain = res.get("plainLyrics")
            if synced:
                lineas = _parsear_sincronizada(synced)
                if lineas:
                    data = {
                        "tiene_letra": True,
                        "sincronizada": True,
                        "lineas": lineas,
                        "instrumental": False,
                    }
            elif plain:
                lineas = _parsear_plana(plain)
                if any(l["texto"] for l in lineas):
                    data = {
                        "tiene_letra": True,
                        "sincronizada": False,
                        "lineas": lineas,
                        "instrumental": False,
                    }
    except requests.RequestException:
        # Proveedor caído: se devuelve "sin letra" y NO se cachea el fallo.
        return data

    letra_cache.update_one(
        {"clave": clave},
        {"$set": {"clave": clave, "data": data, "fecha": _ahora().isoformat()}},
        upsert=True,
    )
    return data
