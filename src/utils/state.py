# Estado de música por servidor (guild_id)

# Cola: lista de (url, título)
music_queues = {}

# Canción que suena ahora: (url, título)
now_playing = {}

# Servidores con la canción actual en bucle
loop_enabled = set()

# Servidores donde se pidió saltar (el bucle no repite esa vez)
skip_once = set()


def reset_guild(guild_id):
    """Deja el servidor sin música: cola, canción actual y bucle."""
    music_queues[guild_id] = []
    now_playing.pop(guild_id, None)
    loop_enabled.discard(guild_id)
    skip_once.discard(guild_id)
