import sys
import re

from sparkhub_paths import get_path

def main():
    app_path = get_path('app.py')
    try:
        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 1. Add argparse to imports
        if 'import argparse' not in content:
            content = content.replace('import sys', 'import sys\nimport argparse')

        # 2. Add proactive_memory_check function just before execute_tool
        proactive_func = '''
# =========================================================
# CONSULTA PROATIVA AO MEMPALACE
# =========================================================
def proactive_memory_check(tool_name, args):
    if tool_name not in ["create_structure", "macro_setup_project", "run_command"]:
        return ""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT wing, room, content FROM memories WHERE wing IN ('Projetos', 'Geral') ORDER BY id DESC LIMIT 5")
            rows = cursor.fetchall()
        if not rows:
            return ""
        res = "\\n".join([f"• [{r['wing']} -> {r['room']}]: {r['content']}" for r in rows])
        return f"\\n\\n[💡 Contexto Proativo do MemPalace]:\\n{res}"
    except Exception:
        return ""

'''
        if 'def proactive_memory_check' not in content:
            target = 'def execute_tool(name, args):'
            content = content.replace(target, proactive_func + target)

        # 3. Replace execute_tool and everything until LocalHubMCPHandler
        # We'll use regex to isolate the execute_tool block
        pattern = re.compile(r'def execute_tool\(name, args\):.*?(?=class LocalHubMCPHandler)', re.DOTALL)
        
        new_execute_tool = '''def execute_tool(name, args):
    """Executa as acoes nativas no Windows e MemPalace v3.0 com os.startfile(), Auto-Discovery, Auditoria e Contexto Proativo"""
    
    # 1. Recuperar contexto proativo
    proactive_context = proactive_memory_check(name, args)
    
    # Função auxiliar para injetar contexto
    def finalize(msg):
        return msg + proactive_context

    if name == "find_app":
        query = args.get("app_query", "")
        res_path = find_executable_or_shortcut(query)
        update_state("find_app", app_name=query)
        return finalize(f"Auto-Discovery encontrou para '{query}': {res_path}")

    if name == "list_recycle_bin":
        return finalize(get_recycle_bin_items())

    app_target = args.get("app_name_or_path", "") or args.get("command", "") or name
    if "lixeira" in str(app_target).lower() or "recycle.bin" in str(app_target).lower():
        return finalize(get_recycle_bin_items())

    folder_res = parse_and_create_folder(app_target)
    if folder_res:
        return finalize(folder_res)

    if name == "open_app":
        extra_args = args.get("args", "")
        parsed = parse_and_create_folder(f"{app_target} {extra_args}")
        if parsed: return finalize(parsed)
            
        resolved_app = find_executable_or_shortcut(app_target)
        if not os.path.exists(resolved_app) and not resolved_app.startswith("http"):
            return finalize(f"[❌ AUDITORIA FALHA] O executável/atalho não foi encontrado no disco: {resolved_app}")
            
        cmd = [resolved_app]
        if extra_args: cmd.append(str(extra_args))
        launch_gui_app(cmd)
        update_state("open_app", project_name=str(extra_args), app_name=resolved_app)
        return finalize(f"[✅ AUDITORIA SUCESSO] Programa '{app_target}' (ShellExecute: {resolved_app}) aceito pelo Windows e iniciado visível.")

    elif name == "run_command":
        cmd_str = args.get("command", "")
        if "lixeira" in cmd_str.lower() or "recycle" in cmd_str.lower():
            return finalize(get_recycle_bin_items())
            
        parsed = parse_and_create_folder(cmd_str)
        if parsed: return finalize(parsed)

        proc = subprocess.run(["powershell", "-Command", cmd_str], capture_output=True, text=True, timeout=30)
        out = proc.stdout.strip() or proc.stderr.strip() or "Comando executado com sucesso."
        update_state("run_command", app_name="PowerShell")
        return finalize(f"[✅ AUDITORIA (Exit Code: {proc.returncode})]:\\n{out}")

    elif name == "mempalace_save":
        return finalize(mempalace_save(args.get("wing", "Geral"), args.get("room", "Geral"), args.get("content", "")))

    elif name == "mempalace_search":
        return finalize(mempalace_search(args.get("query", ""), wing=args.get("wing")))

    elif name == "mempalace_list":
        return finalize(mempalace_list(wing=args.get("wing"), room=args.get("room"), limit=args.get("limit", 10)))

    elif name == "open_kdenlive":
        path = args.get("path", "")
        target = find_executable_or_shortcut("kdenlive")
        kdenlive_cmd = [target, path] if path else [target]
        launch_gui_app(kdenlive_cmd)
        update_state("open_kdenlive", project_name=path, app_name="Kdenlive")
        return finalize(f"[✅ AUDITORIA] Kdenlive iniciado visível{' em: ' + path if path else ''}.")

    elif name == "open_tiktok_live":
        path = args.get("path", "")
        target = find_executable_or_shortcut("TikTok LIVE Studio")
        cmd = [path] if path else [target]
        launch_gui_app(cmd)
        update_state("open_tiktok_live", app_name="TikTok LIVE Studio")
        return finalize("[✅ AUDITORIA] TikTok LIVE Studio iniciado visível.")

    elif name == "open_tikfinity":
        path = args.get("path", "")
        cmd = [path] if path else ["https://tikfinity.zerody.one/"]
        launch_gui_app(cmd)
        update_state("open_tikfinity", app_name="TikFinity")
        return finalize("[✅ AUDITORIA] TikFinity iniciado visível.")

    elif name == "open_vscode":
        path = args.get("path", ".")
        target = find_executable_or_shortcut("code")
        launch_gui_app([target, path])
        update_state("open_vscode", project_name=path, app_name="VS Code")
        return finalize(f"[✅ AUDITORIA] VS Code aberto visível em: {path}")

    elif name == "open_godot":
        path = args.get("path", "")
        target = find_executable_or_shortcut("godot")
        godot_cmd = [target, "--path", path] if path else [target]
        launch_gui_app(godot_cmd)
        update_state("open_godot", project_name=path, app_name="Godot")
        return finalize(f"[✅ AUDITORIA] Godot iniciado visível em: {path}")

    elif name == "run_blender_script":
        script_path = args.get("script_path", "")
        file_path = args.get("file_path", "")
        target = find_executable_or_shortcut("blender")
        cmd = [target]
        if file_path: cmd.append(file_path)
        if script_path: cmd.extend(["-P", script_path])
        launch_gui_app(cmd)
        update_state("run_blender_script", project_name=file_path, app_name="Blender")
        return finalize("[✅ AUDITORIA] Comando do Blender executado visível.")

    elif name == "create_structure":
        base_dir = Path(args.get("base_dir", "."))
        folders = args.get("folders", [])
        files = args.get("files", {})

        total_items = len(folders) + len(files)
        created_count = 0
        failed_items = []

        for folder in folders:
            folder_path = base_dir / folder
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                if folder_path.exists(): created_count += 1
                else: failed_items.append(f"Pasta: {folder}")
            except Exception as e:
                failed_items.append(f"Pasta: {folder} ({e})")

        for file_rel_path, content in files.items():
            file_full_path = base_dir / file_rel_path
            try:
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                if file_full_path.exists(): created_count += 1
                else: failed_items.append(f"Arquivo: {file_rel_path}")
            except Exception as e:
                failed_items.append(f"Arquivo: {file_rel_path} ({e})")

        update_state("create_structure", project_name=str(base_dir))
        
        audit_msg = f"[✅ AUDITORIA SINTÉTICA] {created_count}/{total_items} itens criados com sucesso em {base_dir}"
        if failed_items:
            audit_msg += "\\nFalhas:\\n- " + "\\n- ".join(failed_items)
            
        return finalize(f"Estrutura processada.\\n{audit_msg}")

    elif name == "macro_setup_project":
        base_dir = Path(args.get("base_dir", "D:/Projetos/NovoProjeto"))
        folders = args.get("folders", ["scripts", "scenes", "assets"])
        files = args.get("files", {"README.md": "# Projeto Criado via Spark\\n"})

        total_items = len(folders) + len(files)
        created_count = 0
        failed_items = []

        for folder in folders:
            folder_path = base_dir / folder
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                if folder_path.exists(): created_count += 1
                else: failed_items.append(f"Pasta: {folder}")
            except Exception as e:
                failed_items.append(f"Pasta: {folder} ({e})")

        for file_rel_path, content in files.items():
            file_full_path = base_dir / file_rel_path
            try:
                file_full_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                if file_full_path.exists(): created_count += 1
                else: failed_items.append(f"Arquivo: {file_rel_path}")
            except Exception as e:
                failed_items.append(f"Arquivo: {file_rel_path} ({e})")

        target = find_executable_or_shortcut("code")
        launch_gui_app([target, str(base_dir)])
        update_state("macro_setup_project", project_name=str(base_dir), app_name="VS Code")
        
        audit_msg = f"[✅ AUDITORIA SINTÉTICA] {created_count}/{total_items} itens criados com sucesso. VS Code aberto em {base_dir}"
        if failed_items:
            audit_msg += "\\nFalhas:\\n- " + "\\n- ".join(failed_items)
            
        return finalize(f"Macro concluida.\\n{audit_msg}")

    else:
        parsed = parse_and_create_folder(name)
        if parsed:
            return finalize(parsed)
        raise ValueError(f"Ferramenta desconhecida: {name}")

'''
        content = re.sub(pattern, new_execute_tool, content)

        # 4. Modify the __main__ block to add CLI support
        main_pattern = re.compile(r'if __name__ == "__main__":.*?$', re.DOTALL)
        
        new_main = '''if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SparkHub v3.0 - CLI e Servidor MCP")
    parser.add_argument("tool", nargs="?", help="Nome da ferramenta para executar via CLI (ex: open_app, run_command)")
    parser.add_argument("args", nargs="*", help="Argumentos da ferramenta em formato chave=valor ou string direta")
    
    cli_args = parser.parse_args()
    
    if cli_args.tool:
        # Modo CLI
        print(f"=== SPARKHUB v3.0 MODO CLI ===")
        tool_name = cli_args.tool
        # Parse simple arguments
        tool_kwargs = {}
        if len(cli_args.args) == 1 and "=" not in cli_args.args[0]:
            # Guess mapping based on tool
            if tool_name == "run_command": tool_kwargs["command"] = cli_args.args[0]
            elif tool_name == "open_app": tool_kwargs["app_name_or_path"] = cli_args.args[0]
            elif tool_name == "mempalace_search": tool_kwargs["query"] = cli_args.args[0]
            else: tool_kwargs["path"] = cli_args.args[0]
        else:
            for arg in cli_args.args:
                if "=" in arg:
                    k, v = arg.split("=", 1)
                    tool_kwargs[k] = v
        
        print(f"Executando ferramenta: {tool_name} com args: {tool_kwargs}\\n")
        try:
            result = execute_tool(tool_name, tool_kwargs)
            print("=== RESULTADO ===")
            print(result)
        except Exception as e:
            print(f"[ERRO] {e}")
    else:
        # Modo Servidor MCP Original
        print(f"=== SERVIDOR SPARKHUB v3.0 (SHELLEXECUTE / AUTO-DISCOVERY / CLI) RODANDO NA PORTA {PORT} ===")
        print("Execucao nativa na sessao interativa com os.startfile() e auditoria pos-acao.")
        with socketserver.TCPServer(("", PORT), LocalHubMCPHandler) as httpd:
            httpd.serve_forever()
'''
        content = re.sub(main_pattern, new_main, content)

        # Update version strings in LocalHubMCPHandler
        content = content.replace('"version": "2.4.0"', '"version": "2.5.0"')
        content = content.replace('SparkHub v2.5.0', 'SparkHub v3.0')
        
        with open(app_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("Modificacoes aplicadas com sucesso.")
    except Exception as e:
        print(f"Erro ao modificar arquivo: {e}")

if __name__ == "__main__":
    main()
