import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv(override=True)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY_RERANK") or os.environ.get("OPENROUTER_API_KEY")
# Usando o modelo nativo de Rerank da Nvidia no OpenRouter (Zero-Shot)
RERANK_MODEL = "nvidia/llama-nemotron-rerank-vl-1b-v2:free"

def rerank_mempalace_results(query: str, results: list) -> list:
    """
    Atua como Especialista 6 (Rerank).
    Lê a lista bruta de resultados (híbridos) e reordena com base na relevância real da IA.
    results: list of tuples (wing, room, content, score_type)
    Returns: list of tuples reordenada (e possivelmente filtrada)
    """
    if not results:
        return []
        
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "sua_chave_openrouter_aqui":
        # Sem chave, apenas retorna os top 5 brutos para não quebrar a busca
        return results[:5]
        
    # Prepara o payload para avaliação em Batch via LLM
    context_blocks = []
    for idx, (w, r, c, st) in enumerate(results):
        context_blocks.append(f"Documento [{idx}]:\nAla: {w} | Sala: {r}\nConteudo: {c}")
        
    documents_str = "\n\n".join(context_blocks)
    
    prompt = f"""
Você é um Reranker de extrema precisão.
Sua tarefa é avaliar a relevância dos Documentos a seguir com relação à Pergunta do usuário.
Responda APENAS com um objeto JSON, onde as chaves são os índices dos documentos (0, 1, 2...) e os valores são notas de 0 a 10 (sendo 10 resposta direta e perfeita).

Pergunta do Usuário: "{query}"

Documentos:
{documents_str}

Responda APENAS com JSON válido.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": RERANK_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0, # Zero alucinação para rerank
        "response_format": {"type": "json_object"}
    }
    
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            content = res_json["choices"][0]["message"]["content"]
            
            # Tenta parsear o JSON de notas
            scores = json.loads(content)
            
            # Associa as notas e reordena
            scored_results = []
            for idx, r_tuple in enumerate(results):
                idx_str = str(idx)
                score = float(scores.get(idx_str, 0))
                scored_results.append((score, r_tuple))
                
            # Ordena decrescente pela nota
            scored_results.sort(reverse=True, key=lambda x: x[0])
            
            # Filtra e retorna apenas os 3 melhores que tenham nota mínima
            final_top = []
            for score, r_tuple in scored_results:
                if score >= 3.0: # Relevância mínima aceitável
                    final_top.append(r_tuple)
                if len(final_top) >= 3:
                    break
                    
            return final_top if final_top else results[:3] # Fallback se tudo for ruim
            
    except Exception as e:
        print(f"[RERANKER WARN] Falha na API: {e}. Retornando resultados brutos.")
        return results[:5]
