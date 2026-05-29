"""
Local development server — serves both the static frontend and the Python API.
Mirrors the Vercel production setup exactly.

Usage:  python dev_server.py          (default port 3000)
        python dev_server.py 8080     (custom port)
"""
import sys, os, json, mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
PUBLIC = Path(__file__).parent / 'public'

# Import the calculation engine
sys.path.insert(0, str(Path(__file__).parent / 'api'))
from calculate import solve

CORS = {
    'Access-Control-Allow-Origin':  '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
}


class DevHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in CORS.items(): self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/calculate':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length else '{}'
            try:
                result = solve(json.loads(body))
                resp = json.dumps(result).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
            except Exception as e:
                import traceback
                resp = json.dumps({'error': str(e), 'trace': traceback.format_exc()}).encode()
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
            for k, v in CORS.items(): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(resp)
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        # Route /api/* → 404 (GET not supported on API)
        if self.path.startswith('/api/'):
            self.send_response(405); self.end_headers(); return

        # Serve static files from public/
        path = self.path.split('?')[0]
        if path == '/':
            path = '/index.html'
        file_path = PUBLIC / path.lstrip('/')

        if not file_path.exists() or not file_path.is_file():
            # SPA fallback: serve index.html for unknown paths
            file_path = PUBLIC / 'index.html'

        content_type, _ = mimetypes.guess_type(str(file_path))
        try:
            data = file_path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', content_type or 'text/html')
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_response(500); self.end_headers()

    def log_message(self, fmt, *args):
        print(f'  {self.address_string()} {fmt % args}')


if __name__ == '__main__':
    server = HTTPServer(('', PORT), DevHandler)
    print(f'\nDMI-IPAC dev server running at http://localhost:{PORT}')
    print(f'  Frontend : http://localhost:{PORT}/')
    print(f'  API      : http://localhost:{PORT}/api/calculate')
    print(f'\nCtrl+C to stop\n')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
