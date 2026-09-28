import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

URL = "http://boletim.fazenda.pr.gov.br/"
HISTORICO_ARQUIVO = "historico_pr.json"

def buscar_boletins():
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    itens = []
    # Cada boletim aparece como um link/bloco com número, título e data
    linhas = soup.find_all("tr")  # ajustar conforme estrutura real da tabela
    for linha in linhas:
        texto = linha.get_text(separator=" | ", strip=True)
        if "Boletim Informativo" in texto:
            itens.append(texto)

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

    corpo = "Novos boletins da SEFAZ/PR:\n\n" + "\n\n".join(novos_itens)
    msg = MIMEText(corpo, "plain", "utf-8")
    msg["Subject"] = f"[SEFAZ-PR] {len(novos_itens)} nova(s) atualização(ões)"
    msg["From"] = remetente
    msg["To"] = destinatario

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(remetente, senha)
        server.sendmail(remetente, destinatario, msg.as_string())

def main():
    print(f"[{datetime.now()}] Verificando SEFAZ/PR...")
    try:
        itens_atuais = buscar_boletins()
    except Exception as e:
        print(f"[ERRO] Falha ao acessar o portal PR: {e}")
        return

    if not itens_atuais:
        print("[AVISO] Nenhum item encontrado. O layout do site pode ter mudado.")
        return

    historico = carregar_historico()
    novos = [item for item in itens_atuais if item not in historico]

    if novos:
        print(f"[INFO] {len(novos)} nova(s) atualização(ões) encontrada(s) (PR).")
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
        print("[INFO] Nenhuma novidade (PR).")

if __name__ == "__main__":
    main()
