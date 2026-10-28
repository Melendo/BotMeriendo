from src.utils.queue_utils import (
    DISCORD_MSG_LIMIT, normalizar_url, pistas_de_info, trocear,
)


def test_normalizar_url():
    assert normalizar_url("dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    full = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert normalizar_url(full) == full
    assert normalizar_url(None) is None


def test_pistas_video_suelto():
    info = {"webpage_url": "https://youtu.be/x", "title": "Uno"}
    assert pistas_de_info(info) == [("https://youtu.be/x", "Uno")]


def test_pistas_playlist_plana():
    # Formato de extract_flat: solo url (a veces id) y título
    info = {"title": "Lista", "entries": [
        {"url": "dQw4w9WgXcQ", "title": "A"},
        None,                      # vídeo borrado o privado
        {"title": "sin url"},      # entrada rota
        {"url": "https://www.youtube.com/watch?v=abcdefghijk"},
    ]}
    assert pistas_de_info(info) == [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "A"),
        ("https://www.youtube.com/watch?v=abcdefghijk", "Video desconocido"),
    ]


def test_pistas_vacio():
    assert pistas_de_info(None) == []
    assert pistas_de_info({"entries": []}) == []


def test_trocear_respeta_limite():
    lineas = [f"{i}. " + "x" * 150 for i in range(30)]
    msgs = trocear(lineas, cabecera="📜 Cola:")
    assert len(msgs) > 1
    assert all(len(m) <= DISCORD_MSG_LIMIT for m in msgs)
    assert msgs[0].startswith("📜 Cola:")
    juntos = "\n".join(msgs)
    assert all(l in juntos for l in lineas)


def test_trocear_linea_gigante():
    msgs = trocear(["y" * 5000])
    assert len(msgs) == 1 and len(msgs[0]) <= DISCORD_MSG_LIMIT
