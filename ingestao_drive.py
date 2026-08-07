"""
ingestao_drive.py — Ingestão em Massa (Fase 1 / Caminho 1)

Varre Drive e Gmail (todas as contas conectadas via workspace_agent.py) e
grava resumos no MemPalace, pra que o ask_ai passe a "conhecer" esse
conteúdo sem precisar consultar a API do Google a cada pergunta.
"""

import argparse
import sys
import textwrap
import io
import pypdf
import docx

import workspace_agent as wa
from sparkhub_db import save_memory
from sparkhub_logger import logger

# ---------------------------------------------------------------------------
# PLACEHOLDER — substituir pela chamada real ao MemPalace
# ---------------------------------------------------------------------------

def mempalace_save(texto: str, categoria: str, origem: str):
    """
    Chamada real para salvar no banco de dados MemPalace.
    A API real usa: save_memory(wing, room, content)
    """
    wing = categoria.capitalize()
    room = origem
    save_memory(wing=wing, room=room, content=texto)
    logger.info(f"[MemPalace] Gravado: Asa={wing} | Sala={room}")
    logger.info(f"    {texto[:150]}{'...' if len(texto) > 150 else ''}\n")


# ---------------------------------------------------------------------------
# Resumo simples (sem chamar IA externa por item, pra não gastar tokens à toa
# numa ingestão em massa — trunca por tamanho. Trocar por chamada ao ask_ai
# depois, se quiser resumos mais inteligentes).
# ---------------------------------------------------------------------------

def resumir(texto: str, limite: int = 800) -> str:
    texto = " ".join(texto.split())  # normaliza espaços/quebras de linha
    if len(texto) <= limite:
        return texto
    return textwrap.shorten(texto, width=limite, placeholder=" [...]")


# ---------------------------------------------------------------------------
# Ingestão de Gmail
# ---------------------------------------------------------------------------

def ingerir_gmail(query: str = "", max_por_conta: int = 25):
    # Filtro antifrágil: remove promoções, spam e noreplys do escopo para manter o MemPalace limpo
    filtros_padrao = "-category:promotions -category:social -from:noreply -from:no-reply -from:newsletters"
    query_final = f"{query} {filtros_padrao}".strip()

    tokens = wa.get_all_tokens()
    if not tokens:
        logger.error("[ERRO] Nenhuma conta conectada. Rode: python workspace_agent.py --add-account <alias>")
        return

    for token_path in tokens:
        label = wa.get_account_label(token_path)
        logger.info(f"\n=== Gmail [{label}] ===")
        try:
            ids = wa.list_recent_gmail_ids(token_path, max_results=max_por_conta, query=query_final)
        except Exception as e:
            logger.error(f"[WARN] Falha ao listar e-mails de {label}: {e}")
            continue

        for msg_id in ids:
            try:
                msg = wa.get_gmail_full_message(msg_id, token_path)
                if not msg["body"]:
                    logger.info(f"[SKIP] E-mail {msg_id} ignorado: sem corpo de texto (apenas HTML/anexos).")
                    continue  # pula e-mails só com HTML/anexo, sem corpo texto
                texto_completo = (
                    f"De: {msg['from']}\n"
                    f"Assunto: {msg['subject']}\n"
                    f"Data: {msg['date']}\n\n"
                    f"{msg['body']}"
                )
                resumo = resumir(texto_completo)
                mempalace_save(
                    texto=resumo,
                    categoria="email",
                    origem=f"gmail:{label}:{msg_id}",
                )
            except Exception as e:
                logger.error(f"[WARN] Falha ao processar e-mail {msg_id} ({label}): {e}")


# ---------------------------------------------------------------------------
# Ingestão de Drive
# ---------------------------------------------------------------------------

# Tipos que sabemos extrair texto puro sem depender de parser binário extra.
MIME_TEXTAVEIS = {
    "application/vnd.google-apps.document",  # Google Docs -> export text/plain
    "application/pdf",                       # PDF via pypdf
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", # DOCX via docx
}

def ingerir_drive(max_por_conta: int = 50):
    tokens = wa.get_all_tokens()
    if not tokens:
        logger.error("[ERRO] Nenhuma conta conectada.")
        return

    for token_path in tokens:
        label = wa.get_account_label(token_path)
        logger.info(f"\n=== Drive [{label}] ===")
        try:
            arquivos = wa.list_recent_drive_files(token_path, max_results=max_por_conta)
        except Exception as e:
            logger.error(f"[WARN] Falha ao listar arquivos de {label}: {e}")
            continue

        vistos = {}
        for f in arquivos:
            nome_arquivo = f.get("name", "").lower()
            if nome_arquivo in vistos:
                id_original = vistos[nome_arquivo]
                logger.info(f"[SKIP] Arquivo '{f.get('name')}' ignorado (duplicata de nome na conta {label}). ID Mantido: {id_original} | ID Skiped: {f.get('id')}")
                continue
            vistos[nome_arquivo] = f.get("id")
            
            termos_sensiveis = ["laudo", "perícia", "pericial", "confidencial", "rh", "contrato", "extrato", "sigiloso"]
            match_termo = next((t for t in termos_sensiveis if t in nome_arquivo), None)
            if label.lower() == "trabalho":
                logger.info(f"[SECURITY] Arquivo '{f.get('name')}' marcado como sensível (Origem: conta Trabalho).")
            elif match_termo:
                logger.info(f"[SECURITY] Arquivo '{f.get('name')}' marcado como sensível (Keyword no nome: '{match_termo}').")
            else:
                pass # não é sensível

            mime = f.get("mimeType", "")
            if mime not in MIME_TEXTAVEIS:
                # PDF/DOCX/etc: pulamos por ora (precisam de pypdf/python-docx
                # pra extrair texto — deixado de fora pra manter a primeira
                # versão simples e fácil de debugar).
                continue
            try:
                texto_raw = wa.get_drive_file_fulltext(f["id"], mime, token_path)
                
                texto = ""
                if mime == "application/pdf":
                    try:
                        reader = pypdf.PdfReader(io.BytesIO(texto_raw))
                        # Limit to 50 pages to prevent memory exhaustion, per user feedback concern
                        for i, page in enumerate(reader.pages):
                            if i > 50:
                                break
                            t = page.extract_text()
                            if t: texto += t + "\n"
                    except Exception as parse_e:
                        logger.error(f"[PARSE ERROR] Falha ao extrair texto do PDF '{f.get('name')}': {parse_e}")
                        continue
                elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    try:
                        doc = docx.Document(io.BytesIO(texto_raw))
                        texto = "\n".join([p.text for p in doc.paragraphs])
                    except Exception as parse_e:
                        logger.error(f"[PARSE ERROR] Falha ao extrair texto do DOCX '{f.get('name')}': {parse_e}")
                        continue
                else:
                    texto = texto_raw

                resumo = resumir(texto)
                mempalace_save(
                    texto=f"Documento: {f['name']}\n\n{resumo}",
                    categoria="documento",
                    origem=f"drive:{label}:{f['id']}",
                )
            except Exception as e:
                logger.error(f"[WARN] Falha ao processar '{f.get('name')}' ({label}): {e}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ingestão em massa: Drive + Gmail -> MemPalace")
    parser.add_argument("--fonte", choices=["drive", "gmail", "tudo"], default="tudo")
    parser.add_argument("--query", default="", help="Filtro opcional pro Gmail (sintaxe de busca do Gmail)")
    parser.add_argument("--max", type=int, default=25, help="Máximo de itens por conta")
    args = parser.parse_args()

    if args.fonte in ("gmail", "tudo"):
        ingerir_gmail(query=args.query, max_por_conta=args.max)
    if args.fonte in ("drive", "tudo"):
        ingerir_drive(max_por_conta=args.max)

    logger.info("\n[OK] Ingestão concluída.")


if __name__ == "__main__":
    sys.exit(main())
