import os
import re
import sys
from pathlib import Path

# Configuration
ROOT_DIR = Path(r'D:\\SparkHub')
TEXT_EXTENSIONS = {'.py', '.js', '.ts', '.json', '.yaml', '.yml', '.txt', '.ini', '.cfg'}
# Diretórios que devem ser ignorados durante o escaneamento
EXCLUDE_DIRS = {'.git', 'node_modules', 'venv', '__pycache__', '.idea', '.vscode', '.eggs', '.dist-info', 'env', 'mempalace.db', '.wwebjs_auth', 'audit_full.py'}
PATTERNS = {
    'Asteriscos': re.compile(r'\*{6,}'),
    'TODO': re.compile(r'\bTODO\b'),
    'PLACEHOLDER': re.compile(r'\bPLACEHOLDER\b'),
    'FIXME': re.compile(r'\bFIXME\b'),
    'FStringEmpty': re.compile(r'f"[^\"]*\{\s*\}\s*"'),
}

findings = []

for file_path in ROOT_DIR.rglob('*'):
    # Ignorar diretórios e arquivos excluídos
    if any(part in EXCLUDE_DIRS for part in file_path.parts):
        continue
    if file_path.is_file() and file_path.suffix.lower() in TEXT_EXTENSIONS:
        try:
            text = file_path.read_text(encoding='utf-8')
        except Exception:
            continue
        for name, regex in PATTERNS.items():
            for match in regex.finditer(text):
                line_no = text[:match.start()].count('\n') + 1
                snippet = text.split('\n')[line_no-1].strip()
                findings.append({
                    'file': str(file_path),
                    'line': line_no,
                    'type': name,
                    'snippet': snippet,
                })

report_path = ROOT_DIR / 'audit_report.md'
with report_path.open('w', encoding='utf-8') as f:
    f.write('# Audit Report – Full System Scan\n\n')
    if not findings:
        f.write('No issues found.\n')
    else:
        for i, item in enumerate(findings, 1):
            f.write(f"## Issue {i}\n")
            f.write(f"- **File:** `{item['file']}`\n")
            f.write(f"- **Line:** {item['line']}\n")
            f.write(f"- **Type:** {item['type']}\n")
            f.write(f"- **Snippet:** `{item['snippet']}`\n\n")

print('Audit completed. Findings written to', report_path)
