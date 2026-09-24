"""
NFe Monitor - MVP Fase 1
Monitora Notas Técnicas do Portal Nacional da NF-e e dispara e-mail quando houver novidade.
"""
import hashlib
import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------- CONFIGURAÇÃO ----------
URL_NT = "https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=e05gsFYVn/g="
DB_FILE = Path("historico_nts.json")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO", "seuemail@exemplo.com")
# -----------------------------------


def carregar_historico() -> dict:
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text(encoding="utf-8"))
    return {}


def salvar_historico(historico: dict) -> None:
    DB_FILE.write_text(json.dumps(historico, indent=2, ensure_ascii=False), encoding="utf-8")


def buscar_notas_tecnicas() -> list[dict]:
    """Faz scraping da página de Notas Técnicas do Portal Nacional NF-e."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resp = requests.get(URL_NT, headers=headers, timeout=30, verify=True)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    itens = []

    # O portal renderiza o conteúdo dentro de uma div/tabela com classe "conteudoGeral"
    # Ajustar o seletor caso o HTML mude (ponto de manutenção do scraper)
    linhas = soup.select("table tr") or soup.select("div.linkNoticia") or soup.select("a[href*='.pdf']")

    for linha in linhas:
        texto = linha.get_text(strip=True)
        link_tag = linha.find("a", href=True)
        if not texto or not link_tag:
            continue
        link = link_tag["href"]
        if not link.startswith("http"):
            link = "https://www.nfe.fazenda.gov.br" + link

        item_hash = hashlib.sha256((texto + link).encode("utf-8")).hexdigest()
        itens.append({"titulo": texto, "link": link, "hash": item_hash})

    return itens


def enviar_email(novas: list[dict]) -> None:
    if not SMTP_USER or not SMTP_PASS:
        print("[AVISO] Credenciais SMTP não configuradas. E-mail não enviado.")
        return

    corpo = "Foram detectadas novas Notas Técnicas / atualizações:\n\n"
    for nt in novas:
        corpo += f"📄 {nt['titulo']}\n🔗 {nt['link']}\n\n"

    msg = MIMEText(corpo, "plain", "utf-8")
    msg["Subject"] = f"[NFe Monitor] {len(novas)} nova(s) atualização(ões) detectada(s)"
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_DESTINO

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [EMAIL_DESTINO], msg.as_string())

    print(f"[OK] E-mail enviado para {EMAIL_DESTINO}")


def main():
    print("Iniciando verificação do Portal Nacional NF-e...")
    historico = carregar_historico()

    try:
        atuais = buscar_notas_tecnicas()
    except Exception as e:
        print(f"[ERRO] Falha ao acessar o portal: {e}")
        sys.exit(1)

    if not atuais:
        print("[AVISO] Nenhum item encontrado. O layout do site pode ter mudado.")
        sys.exit(0)

    novas = [item for item in atuais if item["hash"] not in historico]

    if novas:
        print(f"[INFO] {len(novas)} nova(s) atualização(ões) encontrada(s).")
        for nt in novas:
            print(f" - {nt['titulo']}")
            historico[nt["hash"]] = nt
        salvar_historico(historico)
        enviar_email(novas)
    else:
        print("[INFO] Nenhuma novidade encontrada.")


if __name__ == "__main__":
    main()
