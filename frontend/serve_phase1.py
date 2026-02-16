"""HTTP server for Phase 1 frontend."""
import http.server
import socketserver
import os
from pathlib import Path

PORT = 3001
FRONTEND_DIR = Path(__file__).parent

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def do_GET(self):
        # Serve phase1.html as index
        if self.path == '/':
            self.path = '/phase1.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    os.chdir(FRONTEND_DIR)
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"🚀 TrustWise Phase 1 Frontend")
        print(f"📡 Serving at http://localhost:{PORT}")
        print(f"📂 Directory: {FRONTEND_DIR}")
        print(f"\n✅ Open http://localhost:{PORT} in your browser")
        print(f"⚠️  Make sure the backend is running on http://localhost:8000")
        print(f"\nPress Ctrl+C to stop the server\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped")
