"""
sparkhub_verify.py

Modulo de Verificacao Real do SparkHub v3.0.
Implementa as 6 tecnicas de auditoria/depuracao definidas na secao 5 do AGENTS.md:

  1. Verificacao por execucao, nao por leitura (Empirical Verification)
  2. Rastreamento de causa raiz por tras dos imports (Root Cause Tracing)
  3. Ceticismo ativo contra "otimismo do modelo" (Adversarial Self-Review)
  4. Reconhecimento de padroes de codigo suspeitos (Static Code Smell Detection)
  5. Exigencia de evidencia bruta, nao resumo (Raw Evidence over Summary)
  6. Isolamento de variaveis (Bisection / Divide-and-Conquer)

Uso:
    python sparkhub_verify.py app.py
    python sparkhub_verify.py app.py --timeout 8
    python sparkhub_verify.py app.py --no-run     (soh testa imports + smell scan)

Filosofia: este script NUNCA declara algo "operacional". Ele so imprime
evidencia bruta (tracebacks reais, output real, lista de achados) e deixa
o veredito para quem le. Isso e proposital: a decisao de "esta corrigido"
deve ser humana ou baseada em criterio explicito, nao em auto-avaliacao do
proprio codigo que gerou o problema.
"""

import argparse
import ast
import re
import subprocess
import sys
import threading
import time
from pathlib import Path


# =========================================================
# TECNICA 6: ISOLAMENTO DE VARIAVEIS (BISECTION)
# =========================================================

def extract_top_level_imports(target_file: Path):
    """Le o AST do arquivo e extrai os nomes dos modulos importados no topo,
    sem executar nada. Isso nos da a lista exata de dependencias a isolar."""
    try:
        tree = ast.parse(target_file.read_text(encoding="utf-8"), filename=str(target_file))
    except SyntaxError as e:
        return [], f"[ERRO DE SINTAXE] O proprio arquivo {target_file.name} nao compila: {e}"

    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                modules.append(node.module.split(".")[0])

    # Remove duplicados mantendo ordem
    seen = set()
    ordered = []
    for m in modules:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered, None


def test_imports_isolated(target_file: Path):
    """Tenta importar cada dependencia LOCAL (arquivo .py no mesmo diretorio)
    isoladamente, em um subprocesso proprio, para que uma falha em um modulo
    nao mascare o resultado dos outros. Modulos padrao/externos (os, json,
    sqlite3, etc.) sao pulados -- assumimos que o interpretador ja os resolve."""
    project_dir = target_file.parent
    modules, syntax_err = extract_top_level_imports(target_file)
    if syntax_err:
        return [{"module": target_file.name, "ok": False, "detail": syntax_err}]

    results = []
    for mod_name in modules:
        candidate = project_dir / f"{mod_name}.py"
        if not candidate.exists():
            # Nao e um modulo local do projeto -- provavelmente stdlib ou
            # pacote instalado via pip. Nao testamos isoladamente aqui.
            continue

        proc = subprocess.run(
            [sys.executable, "-c", f"import {mod_name}"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        ok = proc.returncode == 0
        results.append({
            "module": mod_name,
            "ok": ok,
            "detail": proc.stderr.strip() if not ok else "Import isolado OK.",
        })
    return results


# =========================================================
# TECNICA 1 + 5: EXECUCAO REAL COM CAPTURA DE EVIDENCIA BRUTA
# =========================================================

# Frases que indicam "subiu e ficou escutando para sempre" -- nesse caso,
# esperar o processo terminar sozinho e um erro de metodologia, nao um bug
# do app. Detectamos esse padrao e encerramos deliberadamente apos capturar
# a evidencia de que subiu, em vez de deixar o processo travar a auditoria.
LONG_RUNNING_SIGNALS = [
    "rodando na porta", "listening on", "serve_forever", "server running",
    "rodando em http", "servidor iniciado", "watching for changes",
]


def run_and_capture(target_file: Path, timeout: int = 10):
    """Executa o script real, captura stdout+stderr linha a linha em tempo
    real (nunca resumido), e decide sozinho quando parar:
      - Se o processo terminar sozinho -> reporta exit code + output completo.
      - Se detectar sinal de "processo de longa duracao" (servidor) -> aguarda
        um pouco mais para garantir estabilidade, depois encerra e reporta
        que SUBIU COM SUCESSO (nao que "terminou"), o que e a leitura correta
        para um daemon/servidor.
      - Se o timeout estourar sem nenhum sinal -> reporta como INCONCLUSIVO,
        nunca como sucesso.
    """
    proc = subprocess.Popen(
        [sys.executable, "-u", str(target_file.name)],
        cwd=str(target_file.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    lines = []
    long_running_detected = False
    lock = threading.Lock()

    def reader():
        nonlocal long_running_detected
        for line in proc.stdout:
            with lock:
                lines.append(line.rstrip("\n"))
                if any(sig in line.lower() for sig in LONG_RUNNING_SIGNALS):
                    long_running_detected = True

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    start = time.time()
    verdict = "INCONCLUSIVO"
    while time.time() - start < timeout:
        if proc.poll() is not None:
            verdict = "TERMINOU_SOZINHO"
            break
        if long_running_detected:
            # Da mais 1.5s para capturar qualquer erro tardio (ex: falha ao
            # bindar segunda porta, erro assincrono) antes de declarar sucesso.
            time.sleep(1.5)
            verdict = "SERVIDOR_ATIVO"
            break
        time.sleep(0.1)

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()

    exit_code = proc.returncode
    with lock:
        full_output = "\n".join(lines)

    return {
        "verdict": verdict,
        "exit_code": exit_code,
        "output": full_output,
    }


# =========================================================
# TECNICA 4: SCANNER DE PADROES SUSPEITOS (COM AUTO-EXCLUSAO)
# =========================================================

EXCLUDE_DIR_NAMES = {
    ".git", "node_modules", "venv", "env", "__pycache__",
    ".idea", ".vscode", ".wwebjs_auth", ".eggs", "dist", "build",
}
TEXT_EXTENSIONS = {".py", ".json", ".ini", ".cfg", ".env.example"}

SUSPECT_PATTERNS = {
    "Asteriscos_Mascarados": re.compile(r'f?["\']?\*{6,}["\']?'),
    "FString_Vazio": re.compile(r'f["\'][^{}"\']*["\']'),  # f-string sem {}
}


def scan_for_smells(project_dir: Path, self_path: Path):
    findings = []
    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.resolve() == self_path.resolve():
            continue  # nunca auditar a si mesmo (evita o loop que ja vimos)
        if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
            continue
        if path.suffix not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, pattern in SUSPECT_PATTERNS.items():
                if pattern.search(line):
                    findings.append({
                        "file": str(path),
                        "line": lineno,
                        "type": label,
                        "snippet": line.strip()[:160],
                    })
    return findings


# =========================================================
# TECNICA 3 + 5: RELATORIO -- SEMPRE EVIDENCIA, NUNCA VEREDITO PRONTO
# =========================================================

def build_report(target_file: Path, import_results, run_result, smells):
    lines = []
    lines.append(f"# Relatorio de Verificacao Real -- {target_file.name}")
    lines.append("")
    lines.append("> Este relatorio contem apenas evidencia bruta coletada por execucao")
    lines.append("> real. Nenhuma linha abaixo declara \"operacional\" ou \"corrigido\" --")
    lines.append("> essa e uma decisao humana, a ser tomada lendo a evidencia.")
    lines.append("")

    lines.append("## 1. Teste isolado de imports locais (Bisection)")
    if not import_results:
        lines.append("- Nenhuma dependencia local (.py no mesmo diretorio) encontrada nos imports.")
    for r in import_results:
        status = "OK" if r["ok"] else "FALHOU"
        lines.append(f"- `{r['module']}`: **{status}**")
        if not r["ok"]:
            lines.append("  ```")
            lines.append(f"  {r['detail']}")
            lines.append("  ```")
    lines.append("")

    lines.append("## 2. Execucao real")
    lines.append(f"- Veredito de execucao: **{run_result['verdict']}**")
    lines.append(f"- Exit code: `{run_result['exit_code']}`")
    lines.append("- Output bruto capturado:")
    lines.append("```")
    lines.append(run_result["output"] or "(nenhuma saida produzida)")
    lines.append("```")
    lines.append("")

    lines.append("## 3. Scanner de padroes suspeitos")
    if not smells:
        lines.append("- Nenhum padrao suspeito encontrado no codigo de producao.")
    else:
        for i, s in enumerate(smells, start=1):
            lines.append(f"### Achado {i}")
            lines.append(f"- Arquivo: `{s['file']}`")
            lines.append(f"- Linha: {s['line']}")
            lines.append(f"- Tipo: {s['type']}")
            lines.append(f"- Trecho: `{s['snippet']}`")
    lines.append("")

    lines.append("## Leitura sugerida (nao e veredito automatico)")
    problems = [r for r in import_results if not r["ok"]]
    if problems:
        lines.append("- Ha falhas de import isolado acima -- comece a correcao por elas,")
        lines.append("  na ordem em que aparecem, antes de investigar o script principal.")
    elif run_result["verdict"] == "SERVIDOR_ATIVO":
        lines.append("- O processo subiu e emitiu um sinal de servidor/daemon ativo; foi")
        lines.append("  encerrado deliberadamente por este script apos a confirmacao (exit")
        lines.append("  code negativo aqui e esperado -- e o sinal de terminate, nao um erro).")
        lines.append("  Isso NAO prova que os endpoints respondem corretamente -- teste-os")
        lines.append("  com uma chamada real (ex: curl) enquanto o processo estiver rodando.")
    elif run_result["verdict"] == "INCONCLUSIVO":
        lines.append("- A execucao nao terminou nem deu sinal de servidor ativo dentro do")
        lines.append("  timeout. Aumente o --timeout ou verifique se o processo esta preso")
        lines.append("  em alguma chamada bloqueante (ex: input(), rede sem timeout).")
    elif run_result["exit_code"] not in (0, None):
        lines.append("- O processo terminou com erro. Leia o output bruto na secao 2 --")
        lines.append("  a ultima parte do traceback normalmente aponta a linha exata.")
    else:
        lines.append("- Sem falhas de import e execucao chegou a um estado terminal/estavel.")
        lines.append("  Isso e evidencia favoravel, mas so cobre esta execucao especifica --")
        lines.append("  nao substitui testar os fluxos/ferramentas MCP individualmente.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="SparkHub v3.0 - Verificacao Real (nao apenas estatica)")
    parser.add_argument("target", help="Arquivo .py a verificar (ex: app.py)")
    parser.add_argument("--timeout", type=int, default=10, help="Segundos de espera antes de INCONCLUSIVO")
    parser.add_argument("--no-run", action="store_true", help="Pula a execucao real, so testa imports + smells")
    args = parser.parse_args()

    target_file = Path(args.target).resolve()
    if not target_file.exists():
        print(f"[ERRO] Arquivo nao encontrado: {target_file}")
        sys.exit(2)

    print(f"[1/3] Testando imports isolados de {target_file.name}...")
    import_results = test_imports_isolated(target_file)

    if args.no_run:
        run_result = {"verdict": "PULADO (--no-run)", "exit_code": None, "output": ""}
    else:
        print(f"[2/3] Executando {target_file.name} de verdade (timeout {args.timeout}s)...")
        run_result = run_and_capture(target_file, timeout=args.timeout)

    print("[3/3] Escaneando padroes suspeitos no diretorio do projeto...")
    smells = scan_for_smells(target_file.parent, Path(__file__))

    report = build_report(target_file, import_results, run_result, smells)
    report_path = target_file.parent / f"verify_report_{target_file.stem}.md"
    report_path.write_text(report, encoding="utf-8")

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)
    print(f"\nRelatorio tambem salvo em: {report_path}")


if __name__ == "__main__":
    main()
