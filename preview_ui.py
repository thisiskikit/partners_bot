from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser


PORT = 4173
ROOT = Path(__file__).resolve().parent / "ui_shell"


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)


def main():
    url = f"http://127.0.0.1:{PORT}/"
    print(f"UI shell preview running at {url}")

    with ThreadingHTTPServer(("127.0.0.1", PORT), PreviewHandler) as server:
        try:
            webbrowser.open(url)
        except Exception:
            pass

        server.serve_forever()


if __name__ == "__main__":
    main()
