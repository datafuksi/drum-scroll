"""Serve the drum scroller on your Wi-Fi.  python serve.py  -> open the printed address on the iPad."""
import http.server, socket, socketserver, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try: s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]
except Exception: ip = "localhost"
PORT = 8765
print(f"\n  On your iPad (same Wi-Fi) open:  http://{ip}:{PORT}\n  Ctrl+C to stop.\n")
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), http.server.SimpleHTTPRequestHandler) as h: h.serve_forever()
