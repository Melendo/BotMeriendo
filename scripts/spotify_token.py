"""Saca el SPOTIFY_REFRESH_TOKEN del bot (se hace una sola vez, en tu ordenador).

Antes:
  1. Crea una app en https://developer.spotify.com/dashboard
  2. En la app, añade este Redirect URI exacto: http://127.0.0.1:8888/callback
  3. Marca "Web API" como API usada.

Uso (desde la raíz del repo):
  python scripts/spotify_token.py

Te pedirá el Client ID y el Client Secret, abrirá Spotify en el navegador
y al aceptar imprimirá las tres líneas para pegar en el .env.
"""
import base64
import getpass
import http.server
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser

HOST, PORT = "127.0.0.1", 8888  # solo esta máquina
REDIRECT_URI = f"http://{HOST}:{PORT}/callback"
SCOPES = "playlist-read-private playlist-read-collaborative"


def pedir_code(client_id: str) -> str:
    state = secrets.token_urlsafe(16)
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
    })
    resultado = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [None])[0] != state:
                resultado["error"] = "state no coincide (posible petición ajena)"
            elif "error" in q:
                resultado["error"] = q["error"][0]
            else:
                resultado["code"] = q.get("code", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("Listo. Ya puedes cerrar esta pestaña y volver a la terminal.".encode())

        def log_message(self, *args):
            pass

    with http.server.HTTPServer((HOST, PORT), Handler) as srv:
        print("\nAbre este enlace si no se abre solo:\n" + url + "\n")
        webbrowser.open(url)
        while not resultado:
            srv.handle_request()

    if "error" in resultado:
        sys.exit(f"Error de Spotify: {resultado['error']}")
    return resultado["code"]


def cambiar_code(client_id: str, client_secret: str, code: str) -> dict:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }).encode(),
        headers={"Authorization": f"Basic {basic}"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def main():
    client_id = os.getenv("SPOTIFY_CLIENT_ID") or input("Client ID: ").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET") or getpass.getpass("Client Secret (no se ve al escribir): ").strip()
    code = pedir_code(client_id)
    data = cambiar_code(client_id, client_secret, code)
    if "refresh_token" not in data:
        sys.exit(f"Spotify no devolvió refresh token: {data}")
    print("\nPega esto en tu .env (y en el secreto ENV_FILE de GitHub). No lo compartas:\n")
    print(f"SPOTIFY_CLIENT_ID={client_id}")
    print(f"SPOTIFY_CLIENT_SECRET={client_secret}")
    print(f"SPOTIFY_REFRESH_TOKEN={data['refresh_token']}")


if __name__ == "__main__":
    main()
