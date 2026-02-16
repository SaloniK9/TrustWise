"""Simple HTTP server to serve the TrustWise frontend."""
import http.server
import socketserver
import os
from pathlib import Path

PORT = 3000
FRONTEND_DIR = Path(__file__).parent

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add headers to prevent caching during development
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def do_GET(self):
        # Serve index_simple.html as the default page
        if self.path == '/':
            self.path = '/index_simple.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    os.chdir(FRONTEND_DIR)
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"🚀 TrustWise Frontend Server")
        print(f"📡 Serving at http://localhost:{PORT}")
        print(f"📂 Directory: {FRONTEND_DIR}")
        print(f"\n✅ Open http://localhost:{PORT} in your browser")
        print(f"⚠️  Make sure the backend is running on http://localhost:8000")
        print(f"\nPress Ctrl+C to stop the server\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped")
