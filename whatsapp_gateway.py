"""
SparkHub - Gateway Local de WhatsApp (Opção B - Custo R$ 0,00)
Servidor HTTP leve em Python escutando em http://localhost:8082/send-whatsapp
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class WhatsAppGatewayHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Responde a requisições no navegador com uma página visual de confirmação."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        
        html_content = """
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <title>SparkHub - Gateway WhatsApp Local</title>
            <style>
                body { font-family: Arial, sans-serif; background-color: #0d1117; color: #c9d1d9; text-align: center; padding: 50px; }
                .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 30px; display: inline-block; max-width: 500px; }
                h1 { color: #2ea043; margin-bottom: 10px; }
                p { font-size: 16px; line-height: 1.5; color: #8b949e; }
                .badge { background: #238636; color: white; padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; }
                .endpoint { background: #21262d; padding: 10px; border-radius: 6px; font-family: monospace; color: #58a6ff; margin-top: 15px; word-break: break-all; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🟢 Gateway WhatsApp SparkHub</h1>
                <span class="badge">Ativo & Operacional</span>
                <p>O servidor local está pronto para receber notificações em segundo plano no Windows 11.</p>
                <div class="endpoint">POST http://localhost:8082/send-whatsapp</div>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html_content.encode("utf-8"))

    def check_auth(self):
        import os
        from dotenv import load_dotenv
        load_dotenv("D:\\SparkHub\\.env")
        token = os.getenv("SPARKHUB_API_TOKEN", "")
        auth_header = self.headers.get("Authorization")
        if not token or auth_header != f"Bearer {token}":
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "error", "message": "Unauthorized"}')
            return False
        return True

    def do_POST(self):
        """Recebe notificações via POST HTTP do SparkHub."""
        if not self.check_auth():
            return
            
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        
        try:
            payload = json.loads(post_data.decode("utf-8"))
            phone = payload.get("phone", "Não informado")
            message = payload.get("message", "Sem conteúdo")
            
            print("=" * 60)
            print(f"[WHATSAPP GATEWAY LOCAL] Notificação enviada para: {phone}")
            print("-" * 60)
            print(message)
            print("=" * 60)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode("utf-8"))

    def log_message(self, format, *args):
        return  # Silencia logs repetitivos no terminal

def run_whatsapp_gateway(port=8082):
    server = HTTPServer(("127.0.0.1", port), WhatsAppGatewayHandler)
    print(f"[WHATSAPP GATEWAY LOCAL] Servidor ativo em http://localhost:{port}/send-whatsapp")
    server.serve_forever()

if __name__ == "__main__":
    run_whatsapp_gateway()
