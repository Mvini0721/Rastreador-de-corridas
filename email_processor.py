# email_processor.py (DEPURAÇÃO FINAL DA 99)
import os
import certifi
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['SSL_CERT_FILE'] = certifi.where()
import os.path, base64, re, requests, time, json, io
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    # (Esta função permanece sem alterações)
    creds = None
    token_json_str = os.environ.get('GOOGLE_TOKEN_JSON')
    creds_json_str = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if token_json_str:
        creds_data = json.loads(token_json_str)
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
    elif os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if creds_json_str:
                creds_data = json.loads(creds_json_str)
                flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
            elif os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            else: return None
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            if os.environ.get('GITHUB_ACTIONS'):
                print("AVISO: Novo token gerado. Atualize o secret 'GOOGLE_TOKEN_JSON' no GitHub.")
    return build('gmail', 'v1', credentials=creds)

def check_for_new_emails():
    print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Iniciando depuração da 99...")
    try:
        service = get_gmail_service()
        if not service: return

        # A busca mais simples possível
        query = "is:unread from:(@99app.com)"
        
        print(f"Usando a query de busca: '{query}'")
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("Nenhum e-mail da 99 encontrado com esta query.")
        else:
            print(f"Encontrado(s) {len(messages)} e-mail(s) da 99. Imprimindo estrutura do primeiro:")
            message = messages[0]
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            payload = msg['payload']
            print(json.dumps(payload, indent=2))
            # Marca como lido para não depurar de novo
            service.users().messages().modify(userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()
            print("  -> E-mail da 99 marcado como lido para fins de depuração.")

    except Exception as e:
        print(f"!!! Ocorreu um erro inesperado: {e}")

if __name__ == '__main__':
    print("--- Robô rodando em modo de depuração para a 99. ---")
    check_for_new_emails()
