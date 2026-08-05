import json
from sparkhub_core_mcp import search_mempalace, sync_data, open_os_app
from sparkhub_core_mcp import MemorySearchContract, SyncRequestContract, AppOpenContract

print("=== TESTE SINTÉTICO DO CORE AI MCP SERVER (Porta Dinâmica via SPARKHUB_PORT) ===")

print("\n1. Teste de Busca no MemPalace:")
search_params = MemorySearchContract(query="Jubileu", limit=1)
res_search = search_mempalace(search_params)
print(res_search)

print("\n2. Teste de Ação de Sync:")
sync_params = SyncRequestContract(scope="sheets", force=True)
res_sync = sync_data(sync_params)
print(res_sync)

print("\n3. Teste de OS App:")
app_params = AppOpenContract(app_name="notepad")
res_app = open_os_app(app_params)
print(res_app)
