# email_processor.py (VERSÃO DE DEPURAÇÃO DE PDF)
import os
import certifi

# Força o uso dos certificados corretos em QUALQUER ambiente
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
os.environ['SSL_CERT_FILE'] = certifi.where()

import os.path
import base64
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import json 
import io
from PyPDF2 import PdfReader

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']
API_URL = "https://rastreador-de-corridas.onrender.com/api/corridas" 
CHECK_INTERVAL = 900

def get_gmail_service():
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

def parse_html_details(html_content, from_header, date_header):
    soup = BeautifulSoup(html_content, 'html.parser')
    details = {'valor': None, 'plataforma': 'Uber', 'origem': None, 'destino': None, 'data_corrida': date_header, 'forma_pagamento': None}
    texto_completo = soup.get_text(" ", strip=True)
    total_text_element = soup.find(lambda tag: tag.name in ['td', 'div'] and 'Total' in tag.get_text())
    if total_text_element:
        match = re.search(r"R\$\s*(\d+[,.]\d{2})", total_text_element.get_text())
        if match: details['valor'] = float(match.group(1).replace(',', '.'))
    time_elements = soup.find_all(string=re.compile(r'^\s*\d{1,2}:\d{2}\s*$'))
    if len(time_elements) >= 2:
        try:
            origem_time_el, destino_time_el = time_elements[0], time_elements[1]
            origem_container = origem_time_el.find_parent('td').find_parent('tr').find_next_sibling('tr')
            if origem_container: details['origem'] = origem_container.get_text(separator=' ', strip=True)
            destino_container = destino_time_el.find_parent('td').find_parent('tr').find_next_sibling('tr')
            if destino_container: details['destino'] = destino_container.get_text(separator=' ', strip=True)
        except (AttributeError, IndexError): pass
    padrao_cartao = r'(\w[\w\s]*)\s+(?:•{4}|\*{4})(\d{4})'
    match_pix = re.search(r'PIX', texto_completo, re.I)
    match_dinheiro = re.search(r'Dinheiro', texto_completo, re.I)
    match_cartao = re.search(padrao_cartao, texto_completo)
    if match_pix: details['forma_pagamento'] = 'PIX'
    elif match_dinheiro: details['forma_pagamento'] = 'Dinheiro'
    elif match_cartao:
        nome_cartao = match_cartao.group(1).split()[-2:]
        details['forma_pagamento'] = f"{' '.join(nome_cartao)} final {match_cartao.group(2)}"
    return details

def parse_pdf_details(pdf_content, date_header):
    """Versão de depuração para imprimir o texto extraído do PDF da 99."""
    details = {'plataforma': '99', 'data_corrida': date_header, 'valor': None, 'origem': None, 'destino': None, 'forma_pagamento': None}
    try:
        texto_pdf = ""
        reader = PdfReader(io.BytesIO(pdf_content))
        for page in reader.pages:
            texto_pdf += page.extract_text()

        # --- DEPURAÇÃO ---
        print("\n--- TEXTO EXTRAÍDO DO PDF DA 99 ---")
        print(texto_pdf)
        print("--- FIM DO TEXTO DO PDF ---\n")
        # -----------------
        
        match_valor = re.search(r'(?:Total|Valor\s+da\s+corrida)\s+R\$\s*([\d,]+\.\d{2})', texto_pdf, re.I)
        if match_valor: details['valor'] = float(match_valor.group(1).replace(',', ''))
        
        match_origem = re.search(r'Embarque\s+[\d/]+\s+às\s+\d{2}:\d{2}\s+em\s+(.*?)\s+Desembarque', texto_pdf, re.DOTALL)
        if match_origem: details['origem'] = match_origem.group(1).strip().replace('\n', ' ')

        match_destino = re.search(r'Desembarque\s+[\d/]+\s+às\s+\d{2}:\d{2}\s+em\s+(.*?)\s+Duração', texto_pdf, re.DOTALL)
        if match_destino: details['destino'] = match_destino.group(1).strip().replace('\n', ' ')
        
        match_pagamento = re.search(r'Pagamento\s+em\s+([\w\s-]+)', texto_pdf, re.I)
        if match_pagamento: details['forma_pagamento'] = match_pagamento.group(1).strip()

    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
    return details

def add_ride_to_api(ride_details):
    if ride_details.get('valor') is None:
        print("  -> Falha: Valor da corrida não encontrado no e-mail/PDF.")
        return False
    try:
        response = requests.post(API_URL, json=ride_details)
        if response.status_code in [200, 201]:
            status = "registrada" if response.status_code == 201 else "duplicada ignorada"
            print(f"  -> Sucesso! Corrida de R${ride_details.get('valor')} {status}.")
            return True
        else:
            print(f"  -> Erro na API: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  -> ERRO DE CONEXÃO com a API em {API_URL}.")
        return False

def check_for_new_emails():
    """Versão de PRODUÇÃO: Verifica e processa HTML da Uber e PDF da 99."""
    print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Verificando por novos e-mails...")
    try:
        service = get_gmail_service()
        if not service: return

        query = "is:unread from:(@uber.com OR @99app.com) subject:(recibo OR sua viagem OR receipt)"
        
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        if not messages:
            print("Nenhum novo recibo de corrida encontrado.")
        else:
            print(f"Encontrado(s) {len(messages)} novo(s) recibo(s). Processando...")
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
                payload = msg['payload']
                headers = payload['headers']
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'Sem Assunto')
                from_header = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                date_header = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
                detalhes_corrida = None
                
                if '99app.com' in from_header:
                    print(f"\nProcessando e-mail da 99: '{subject}'")
                    parts = payload.get('parts', [])
                    for part in parts:
                        if part.get('mimeType') == 'application/pdf' and part.get('body') and part['body'].get('attachmentId'):
                            attachment_id = part['body']['attachmentId']
                            attachment = service.users().messages().attachments().get(userId='me', messageId=message['id'], id=attachment_id).execute()
                            pdf_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
                            detalhes_corrida = parse_pdf_details(pdf_data, date_header)
                            break 
                else: 
                    print(f"\nProcessando e-mail da Uber: '{subject}'")
                    html_content = ""
                    if 'parts' in payload:
                        for part in payload['parts']:
                            if part.get('mimeType') == 'text/html':
                                data = part['body']['data']
                                html_content = base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
                                break
                    if not html_content and 'body' in payload and 'data' in payload['body']:
                        data = payload['body']['data']
                        html_content = base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
                    if html_content:
                        detalhes_corrida = parse_html_details(html_content, from_header, date_header)

                if detalhes_corrida:
                    sucesso = add_ride_to_api(detalhes_corrida)
                    if sucesso:
                        service.users().messages().modify(userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()
                        print("  -> E-mail marcado como lido.")
                    else:
                        print("  -> FALHA AO REGISTRAR. O e-mail NÃO será marcado como lido.")
                else:
                    print("  -> Não foi possível extrair detalhes. Marcando como lido para evitar loops.")
                    service.users().messages().modify(userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()
    except Exception as e:
        print(f"!!! Ocorreu um erro inesperado: {e}")

if __name__ == '__main__':
    is_ci_environment = os.environ.get('GITHUB_ACTIONS')
    if is_ci_environment:
        print("--- Robô rodando em ambiente de CI/CD. Executando uma vez. ---")
        check_for_new_emails()
    else:
        print("--- Serviço de Monitoramento de E-mails Iniciado (Modo Local) ---")
        print(f"O robô irá verificar por novos e-mails a cada {int(CHECK_INTERVAL / 60)} minutos.")
        print("Para parar o serviço, pressione Ctrl + C.")
        while True:
            check_for_new_emails()
            print(f"--- Próxima verificação em {int(CHECK_INTERVAL / 60)} minutos. Aguardando... ---")
            time.sleep(CHECK_INTERVAL)