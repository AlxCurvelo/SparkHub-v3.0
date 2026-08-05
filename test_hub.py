import json
import os
import urllib.request


def build_headers():
    headers = {"Content-Type": "application/json"}
    token = os.getenv("SPARKHUB_API_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def run_tests():
    port = os.getenv("SPARKHUB_PORT", "8000")
    base_url = os.getenv("SPARKHUB_BASE_URL", f"http://localhost:{port}")
    headers = build_headers()

    print(f"[TESTE 1] GET / (Health & MCP Info Check) em {base_url}")
    try:
        req = urllib.request.Request(base_url + "/", headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("Resposta GET:", data)
            assert data.get("name") == "SparkHub MCP Server Universal"
            print("-> Teste 1 PASSOU!")
    except Exception as e:
        print("-> Teste 1 FALHOU:", e)
        return False

    print("\n[TESTE 2] MCP JSON-RPC 'tools/list'")
    payload_tools = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    try:
        req = urllib.request.Request(base_url + "/", data=json.dumps(payload_tools).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tools_list = [t["name"] for t in data["result"]["tools"]]
            print("Ferramentas encontradas (Total:", len(tools_list), "):", tools_list)
            assert "open_app" in tools_list
            assert "run_command" in tools_list
            assert "mempalace_save" in tools_list
            assert len(tools_list) >= 16
            print("-> Teste 2 PASSOU!")
    except Exception as e:
        print("-> Teste 2 FALHOU:", e)
        return False

    print("\n[TESTE 3] MCP 'open_app' (Dry Run)")
    payload_app = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "open_app", "arguments": {"app_name_or_path": "notepad"}},
    }
    try:
        req = urllib.request.Request(base_url + "/", data=json.dumps(payload_app).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("Resposta open_app:", data)
            assert "notepad" in data["result"]["content"][0]["text"]
            print("-> Teste 3 PASSOU!")
    except Exception as e:
        print("-> Teste 3 FALHOU:", e)
        return False

    print("\n[TESTE 4] MCP 'run_command' (PowerShell echo)")
    payload_cmd = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "run_command", "arguments": {"command": "Write-Output 'SparkHub v2.0 OK'"}},
    }
    try:
        req = urllib.request.Request(base_url + "/", data=json.dumps(payload_cmd).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("Resposta run_command:", data)
            assert "SparkHub v2.0 OK" in data["result"]["content"][0]["text"]
            print("-> Teste 4 PASSOU!")
    except Exception as e:
        print("-> Teste 4 FALHOU:", e)
        return False

    print("\nTodos os testes MCP Universal executados com sucesso!")
    return True


if __name__ == "__main__":
    run_tests()

