import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

URL = "https://dfe-portal.svrs.rs.gov.br/DFe/Documentos"
HISTORICO_ARQUIVO = "historico_rs.json"

def buscar_documentos():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MonitorNFe/1.0)"}
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    itens = []
    # Percorre todos os títulos (geralmente h2/h3) e tenta achar a data associada
    for titulo in soup.find_all(["h2", "h3", "h4"]):
        texto_titulo = titulo.get_text(strip=True)
        if not texto_titulo or len(texto_titulo) < 5:
            continue

        # Procura uma data (dd/mm/aaaa) em elementos vizinhos anteriores
        data_encontrada = ""
        anterior = titulo.find_previous(string=lambda s: s and "/" in s and len(s.strip()) <= 12)
        if anterior:
            data_encontrada = anterior.strip()

        item = f"{data_encontrada} | {texto_titulo}"
        itens.append(item)

    return itens

def carregar_historico():
    if os.path.exists(HISTORICO_ARQUIVO):
        with open(HISTORICO_ARQUIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_historico(historico):
    with open(HISTORICO_ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

def enviar_email(novos_itens):
    remetente = os.environ["EMAIL_REMETENTE"]
    senha = os.environ["EMAIL_SENHA"]
    destinatario = os.environ["EMAIL_DESTINATARIO"]

    corpo = "Novos documentos da SEFAZ/RS (SVRS):\n\n" + "\n\n".join(novos_itens)
    msg = MIMEText(corpo, "plain", "utf-8")
    msg["Subject"] = f"[SEFAZ-RS] {len(novos_itens)} nova(s) atualização(ões)"
    msg["From"] = remetente
    msg["To"] = destinatario

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(remetente, senha)
        server.sendmail(remetente, destinatario, msg.as_string())

def main():
    print(f"[{datetime.now()}] Verificando SEFAZ/RS (SVRS)...")
    try:
        itens_atuais = buscar_documentos()
    except Exception as e:
        print(f"[ERRO] Falha ao acessar o portal RS: {e}")
        return

    if not itens_atuais:
        print("[AVISO] Nenhum item encontrado. O layout do site pode ter mudado.")
        return

    print(f"[DEBUG] {len(itens_atuais)} itens capturados na página.")

    historico = carregar_historico()
    novos = [item for item in itens_atuais if item not in historico]

    if novos:
        print(f"[INFO] {len(novos)} nova(s) atualização(ões) encontrada(s) (RS).")
        for item in novos:
            print(f" - {item}")

        historico = itens_atuais + historico
        salvar_historico(historico)

        try:
            enviar_email(novos)
            print("[OK] E-mail enviado.")
        except Exception as e:
            print(f"[ERRO] Falha ao enviar e-mail: {e}")
    else:
        print("[INFO] Nenhuma novidade (RS).")

if __name__ == "__main__":
    main()
