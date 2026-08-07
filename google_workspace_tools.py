import os
import datetime
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Escopos de leitura necessários
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

SECRETS_DIR = Path("D:/SparkHub/secrets")
CREDENTIALS_FILE = SECRETS_DIR / "credentials.json"
TOKEN_FILE = SECRETS_DIR / "token.json"

def get_google_credentials():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(f"Arquivo {CREDENTIALS_FILE} não encontrado. Cole as credenciais OAuth baixadas do Google Cloud Console.")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            # Rodar servidor local na porta zero (dinâmica) para receber o callback
            creds = flow.run_local_server(port=0)
            
        with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
            token.write(creds.to_json())
    return creds

def search_gmail(query: str, max_results: int = 5) -> str:
    """Busca e-mails recentes correspondentes a uma query."""
    try:
        creds = get_google_credentials()
        service = build('gmail', 'v1', credentials=creds)
        
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            return "Nenhum e-mail encontrado para a busca."
            
        snippets = []
        for msg in messages:
            msg_id = msg['id']
            msg_data = service.users().messages().get(userId='me', id=msg_id, format='metadata').execute()
            
            subject = "Sem Assunto"
            date = "Data Desconhecida"
            headers = msg_data.get('payload', {}).get('headers', [])
            for h in headers:
                if h['name'].lower() == 'subject':
                    subject = h['value']
                if h['name'].lower() == 'date':
                    date = h['value']
            
            snippet = msg_data.get('snippet', '')
            snippets.append(f"Data: {date}\nAssunto: {subject}\nTrecho: {snippet}\n---")
            
        return "\n".join(snippets)
        
    except Exception as e:
        return f"Erro ao acessar Gmail: {str(e)}"


def search_drive(query: str, max_results: int = 3) -> str:
    """Busca arquivos no Drive correspondentes a uma query e retorna metadata."""
    try:
        creds = get_google_credentials()
        service = build('drive', 'v3', credentials=creds)
        
        # 'fullText contains "texto"' pode ser usado no Drive v3.
        # Formataremos a query para evitar injeção bruta.
        safe_query = query.replace("'", "\\'")
        q = f"fullText contains '{safe_query}'"
        
        results = service.files().list(
            q=q,
            pageSize=max_results,
            fields="nextPageToken, files(id, name, mimeType, createdTime)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            return "Nenhum arquivo encontrado no Drive para a busca."
            
        output = []
        for item in items:
            output.append(f"Arquivo: {item['name']} (Tipo: {item['mimeType']}) - Criado em: {item.get('createdTime', '')}")
            
        return "\n".join(output)
        
    except Exception as e:
        return f"Erro ao acessar Google Drive: {str(e)}"

if __name__ == "__main__":
    # Teste de execução direta para gerar token
    print("Testando autenticação do Google Workspace...")
    try:
        creds = get_google_credentials()
        print("Autenticação válida! Token salvo.")
    except Exception as e:
        print(f"Falha na autenticação: {e}")
