"""Funciones puras de la cola de música (sin Discord ni red: fáciles de probar)."""

DISCORD_MSG_LIMIT = 2000
TITULO_DESCONOCIDO = "Video desconocido"


def normalizar_url(url: str | None) -> str | None:
    """yt-dlp en modo plano a veces devuelve solo el id (11 caracteres)."""
    if url and len(url) == 11 and " " not in url and "." not in url and "/" not in url:
        return f"https://www.youtube.com/watch?v={url}"
    return url


def entrada_a_pista(entry: dict | None) -> tuple[str, str] | None:
    """Convierte una entrada de yt-dlp en (url, título), o None si no vale."""
    if not entry:
        return None
    url = normalizar_url(entry.get("webpage_url") or entry.get("url"))
    if not url:
        return None
    return url, entry.get("title") or TITULO_DESCONOCIDO


def pistas_de_info(info: dict | None) -> list[tuple[str, str]]:
    """Todas las pistas de un resultado de yt-dlp (vídeo suelto o playlist)."""
    if not info:
        return []
    if info.get("entries") is not None:
        return [p for p in (entrada_a_pista(e) for e in info["entries"]) if p]
    pista = entrada_a_pista(info)
    return [pista] if pista else []


def trocear(lineas: list[str], cabecera: str = "", limite: int = DISCORD_MSG_LIMIT) -> list[str]:
    """Junta líneas en mensajes que no pasen del límite de Discord."""
    mensajes: list[str] = []
    actual = cabecera
    for linea in lineas:
        if len(linea) > limite - 1:
            linea = linea[: limite - 2] + "…"
        candidato = f"{actual}\n{linea}" if actual else linea
        if len(candidato) > limite:
            mensajes.append(actual)
            actual = linea
        else:
            actual = candidato
    if actual:
        mensajes.append(actual)
    return mensajes
