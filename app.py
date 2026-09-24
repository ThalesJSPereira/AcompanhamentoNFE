"""
NFe Monitor - Painel Web (Streamlit)
Exibe o histórico de Notas Técnicas monitoradas + permite verificação manual.
"""
import json
from datetime import datetime

import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="NFe Monitor", page_icon="📄", layout="wide")

# URL raw do histórico salvo pelo GitHub Actions
# Troque USUARIO/REPOSITORIO pelo seu repositório real
RAW_URL = "https://raw.githubusercontent.com/USUARIO/REPOSITORIO/main/historico_nts.json"
URL_NT = "https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=e05gsFYVn/g="


@st.cache_data(ttl=300)  # cache de 5 min
def carregar_historico_remoto():
    try:
        resp = requests.get(RAW_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def buscar_notas_tecnicas_live():
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(URL_NT, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    itens = []
    linhas = soup.select("table tr") or soup.select("a[href*='.pdf']")
    for linha in linhas:
        texto = linha.get_text(strip=True)
        link_tag = linha.find("a", href=True)
        if not texto or not link_tag:
            continue
        link = link_tag["href"]
        if not link.startswith("http"):
            link = "https://www.nfe.fazenda.gov.br" + link
        itens.append({"titulo": texto, "link": link})
    return itens


# ---------- HEADER ----------
st.title("📄 NFe Monitor — Notas Técnicas")
st.caption("Monitoramento automático do Portal Nacional da NF-e")

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 Verificar agora (manual)"):
        with st.spinner("Consultando o portal..."):
            try:
                itens = buscar_notas_tecnicas_live()
                st.success(f"{len(itens)} itens encontrados agora no portal.")
                st.session_state["verificacao_manual"] = itens
            except Exception as e:
                st.error(f"Erro ao acessar o portal: {e}")

# ---------- RESULTADO DA VERIFICAÇÃO MANUAL ----------
if "verificacao_manual" in st.session_state:
    st.subheader("Resultado da verificação manual (não salvo no histórico)")
    for item in st.session_state["verificacao_manual"][:20]:
        st.write(f"📄 [{item['titulo']}]({item['link']})")
    st.divider()

# ---------- HISTÓRICO OFICIAL (salvo pelo Actions) ----------
st.subheader("📚 Histórico monitorado (via GitHub Actions)")

historico = carregar_historico_remoto()

if not historico:
    st.info("Nenhum histórico encontrado ainda. Aguarde a primeira execução do workflow ou configure o RAW_URL corretamente.")
else:
    itens = list(historico.values())
    itens_ordenados = sorted(itens, key=lambda x: x.get("titulo", ""), reverse=True)

    busca = st.text_input("🔍 Buscar por termo (ex: número da NT, palavra-chave)")
    if busca:
        itens_ordenados = [i for i in itens_ordenados if busca.lower() in i["titulo"].lower()]

    st.write(f"**{len(itens_ordenados)}** notas técnicas registradas")

    for item in itens_ordenados:
        with st.container(border=True):
            st.markdown(f"**{item['titulo']}**")
            st.markdown(f"🔗 [Abrir documento]({item['link']})")

st.divider()
st.caption(f"Última atualização do painel: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
