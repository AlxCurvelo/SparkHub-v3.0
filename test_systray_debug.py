# test_systray_debug.py
# Script de diagnóstico - roda o systray e salva tudo num arquivo de log
import sys
import os
import time

LOG_FILE = r"D:\SparkHub\systray_debug.log"

# Redireciona stdout e stderr para arquivo
import io
log_f = open(LOG_FILE, "w", encoding="utf-8", buffering=1)
sys.stdout = log_f
sys.stderr = log_f

print(f"=== SparkHub Systray Debug Log ===")
print(f"Python: {sys.version}")
print(f"Plataforma: {sys.platform}")
print(f"Hora: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Testa imports
try:
    from PIL import Image, ImageDraw
    print("[OK] PIL/Pillow importado")
except Exception as e:
    print(f"[ERRO] PIL: {e}")

try:
    import ctypes
    import ctypes.wintypes as wt
    print("[OK] ctypes importado")
except Exception as e:
    print(f"[ERRO] ctypes: {e}")

try:
    shell32  = ctypes.windll.shell32
    user32   = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    print("[OK] DLLs Win32 carregadas")
except Exception as e:
    print(f"[ERRO] DLLs: {e}")

# Testa criação de ícone
try:
    TEMP = os.environ.get("TEMP", "C:\\Temp")
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((2, 2, 30, 30), fill=(46, 160, 67), outline=(255, 255, 255), width=2)
    ico_path = os.path.join(TEMP, "sparkhub_test.ico")
    img.save(ico_path, format="ICO", sizes=[(32, 32)])
    print(f"[OK] Ícone ICO criado em: {ico_path}")
    
    hicon = user32.LoadImageW(None, ico_path, 1, 32, 32, 0x10)
    print(f"[OK] HICON carregado: {hicon}")
    if not hicon:
        err = kernel32.GetLastError()
        print(f"[AVISO] LoadImageW retornou 0, erro Win32={err}")
        hicon = user32.LoadIconW(None, 32512)  # IDI_APPLICATION
        print(f"[FALLBACK] Usando ícone padrão: {hicon}")
except Exception as e:
    print(f"[ERRO] Ícone: {e}")

# Testa criação de janela e ícone na bandeja
try:
    WM_USER = 0x0400
    WM_TRAY = WM_USER + 20
    NIM_ADD = 0
    NIF_MESSAGE = 1
    NIF_ICON = 2
    NIF_TIP = 4

    _LRESULT = ctypes.c_ssize_t
    _WPARAM  = ctypes.c_ssize_t
    _LPARAM  = ctypes.c_ssize_t

    user32.DefWindowProcW.restype  = _LRESULT
    user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, _WPARAM, _LPARAM]
    print("[OK] argtypes definidos")

    WNDPROCTYPE = ctypes.WINFUNCTYPE(_LRESULT, wt.HWND, wt.UINT, _WPARAM, _LPARAM)

    def wnd_proc(hwnd, msg, wparam, lparam):
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    WndProc = WNDPROCTYPE(wnd_proc)

    class WNDCLASSEX(ctypes.Structure):
        _fields_ = [
            ("cbSize",        wt.UINT),
            ("style",         wt.UINT),
            ("lpfnWndProc",   WNDPROCTYPE),
            ("cbClsExtra",    ctypes.c_int),
            ("cbWndExtra",    ctypes.c_int),
            ("hInstance",     wt.HINSTANCE),
            ("hIcon",         wt.HICON),
            ("hCursor",       wt.HANDLE),
            ("hbrBackground", wt.HBRUSH),
            ("lpszMenuName",  wt.LPCWSTR),
            ("lpszClassName", wt.LPCWSTR),
            ("hIconSm",       wt.HICON),
        ]

    hInstance = kernel32.GetModuleHandleW(None)
    class_name = "SparkHubTestClass999"

    wcx = WNDCLASSEX()
    wcx.cbSize        = ctypes.sizeof(WNDCLASSEX)
    wcx.style         = 0
    wcx.lpfnWndProc   = WndProc
    wcx.hInstance     = hInstance
    wcx.hIcon         = hicon
    wcx.hCursor       = user32.LoadCursorW(None, 32512)
    wcx.lpszClassName = class_name
    wcx.hIconSm       = hicon

    atom = user32.RegisterClassExW(ctypes.byref(wcx))
    err = kernel32.GetLastError()
    print(f"[OK] Classe registrada: atom={atom}, LastError={err}")

    hwnd = user32.CreateWindowExW(
        0, class_name, "SparkHub Test",
        0, 0, 0, 0, 0, 0, 0, hInstance, None
    )
    err2 = kernel32.GetLastError()
    print(f"[OK] HWND={hwnd}, LastError={err2}")

    # Cria struct NOTIFYICONDATA
    class NOTIFYICONDATA(ctypes.Structure):
        _fields_ = [
            ("cbSize",           wt.DWORD),
            ("hWnd",             wt.HWND),
            ("uID",              wt.UINT),
            ("uFlags",           wt.UINT),
            ("uCallbackMessage", wt.UINT),
            ("hIcon",            wt.HICON),
            ("szTip",            ctypes.c_wchar * 128),
        ]

    nid = NOTIFYICONDATA()
    nid.cbSize           = ctypes.sizeof(NOTIFYICONDATA)
    nid.hWnd             = hwnd
    nid.uID              = 1
    nid.uFlags           = NIF_ICON | NIF_MESSAGE | NIF_TIP
    nid.uCallbackMessage = WM_TRAY
    nid.hIcon            = hicon
    nid.szTip            = "SparkHub Teste"

    result = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
    err3 = kernel32.GetLastError()
    print(f"[RESULTADO] Shell_NotifyIconW ADD = {result}, LastError={err3}")
    
    if result:
        print("[✅ SUCESSO] Ícone adicionado à bandeja!")
        print("  > Procure na bandeja do sistema (seta ^ na barra de tarefas)")
        log_f.flush()
        time.sleep(15)  # Mantém o ícone visível por 15 segundos
    else:
        print(f"[❌ FALHA] Shell_NotifyIconW retornou {result}")
        print(f"  LastError Win32 = {err3}")

except Exception as e:
    import traceback
    print(f"[ERRO CRÍTICO]: {e}")
    traceback.print_exc()

print()
print("=== Fim do diagnóstico ===")
log_f.flush()
log_f.close()
