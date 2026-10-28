"""Check deployment links and execute the README curl examples against a stub API."""
import base64
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import unittest
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aMxkAAAAASUVORK5CYII=')


class TemplateTests(unittest.TestCase):
    def test_catalog_links_match_template(self):
        def links(path):
            raw = re.findall(r'https://console\.nebius\.com/serverless/endpoint/create\?[^"\s)]+', path.read_text())
            return [parse_qs(urlsplit(html.unescape(u)).query) for u in raw if 'FLUX.2-klein-4B' in u]
        reference = links(ROOT / 'README.md')
        self.assertEqual(len(reference), 1)
        query = reference[0]
        self.assertIn('@sha256:', query['image'][0])
        self.assertEqual(query['auth'], ['true'])
        self.assertEqual(query['preemptible'], ['false'])
        self.assertEqual(query['platform'], ['gpu-l40s-a'])
        self.assertIn('--port 8000', query['command'][0])
        self.assertEqual(links(REPO / 'README.md'), reference)
        self.assertEqual(links(REPO / 'templates/README.md'), reference * 2)

    def test_readme_curl_generation_and_editing(self):
        received = []

        class API(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                received.append((self.path, self.headers.get('Authorization'), body))
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'data': [{'b64_json': base64.b64encode(PNG).decode()}]}).encode())

        server = ThreadingHTTPServer(('127.0.0.1', 0), API)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        text = (ROOT / 'README.md').read_text()
        blocks = re.findall(r'```bash\n(.*?)```', text, re.S)
        snippets = [b for b in blocks if 'curl --fail-with-body' in b]
        self.assertEqual(len(snippets), 2)
        setup = f'BASE_URL=http://127.0.0.1:{server.server_port}\nAUTH=(-H "Authorization: Bearer test-token")\n'
        try:
            with tempfile.TemporaryDirectory() as directory:
                for snippet in snippets:
                    subprocess.run(['bash', '-euo', 'pipefail', '-c', setup + snippet], cwd=directory, check=True)
                self.assertEqual((Path(directory) / 'klein-generated.png').read_bytes(), PNG)
                self.assertEqual((Path(directory) / 'klein-edited.png').read_bytes(), PNG)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        self.assertEqual([r[0] for r in received], ['/v1/images/generations', '/v1/images/edits'])
        self.assertTrue(all(r[1] == 'Bearer test-token' for r in received))
        generation = json.loads(received[0][2])
        self.assertEqual((generation['num_inference_steps'], generation['guidance_scale']), (4, 1.0))
        self.assertEqual(generation['model'], 'black-forest-labs/FLUX.2-klein-4B')
        self.assertIn(b'name="image"; filename="klein-generated.png"', received[1][2])
        self.assertIn(PNG, received[1][2])


if __name__ == '__main__':
    unittest.main()
