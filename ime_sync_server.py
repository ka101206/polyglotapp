import http.server
import socketserver
import urllib.parse
import subprocess
import json

PORT = 8081

class IMESyncHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            text = data.get('text', '')
            
            if text:
                # Use xclip to put text in the clipboard
                p1 = subprocess.Popen(['echo', '-n', text], stdout=subprocess.PIPE)
                p2 = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=p1.stdout, stdout=subprocess.PIPE, env={'DISPLAY': ':99'})
                p1.stdout.close()
                p2.communicate()
                
                # Use xdotool to simulate Ctrl+V
                subprocess.run(['xdotool', 'key', 'ctrl+v'], env={'DISPLAY': ':99'})
            
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success'}).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode('utf-8'))

with socketserver.TCPServer(("", PORT), IMESyncHandler) as httpd:
    print(f"IME Sync Server serving at port {PORT}")
    httpd.serve_forever()
