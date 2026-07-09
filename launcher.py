import json, os, sys, zipfile, shutil, runpy, datetime as dt
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk, filedialog, scrolledtext  # keep Tk submodules bundled by PyInstaller

BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
SETTINGS = BASE_DIR / 'config' / 'settings.json'
APP_FILE = BASE_DIR / 'hub_app.py'

def load_settings():
    try:
        return json.loads(SETTINGS.read_text(encoding='utf-8'))
    except Exception:
        return {}

def save_settings(s):
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding='utf-8')

def apply_pending_program_update():
    s = load_settings()
    rel = s.get('pending_program_update')
    if not rel:
        return
    zpath = BASE_DIR / rel
    if not zpath.exists():
        s.pop('pending_program_update', None)
        save_settings(s)
        return
    backup = BASE_DIR / 'backups' / f"program_backup_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup.mkdir(parents=True, exist_ok=True)
    try:
        for name in ['hub_app.py','launcher.py','main.py','manifest.json','app_version.json']:
            p = BASE_DIR / name
            if p.exists():
                shutil.copy2(p, backup / name)
        for d in ['modules','resources']:
            if (BASE_DIR/d).exists():
                shutil.copytree(BASE_DIR/d, backup/d, dirs_exist_ok=True)
        with zipfile.ZipFile(zpath) as z:
            names = z.namelist()
            # Program update may contain files either at root or under payload/
            for n in names:
                if n.endswith('/') or n in ['update_manifest.json','manifest.json']:
                    continue
                target_name = n
                if n.startswith('payload/'):
                    target_name = n[len('payload/'):]
                if not target_name:
                    continue
                # only allow application files; no arbitrary parent traversal
                if '..' in Path(target_name).parts:
                    continue
                if target_name.startswith(('config/','masters/','templates/','profiles/')):
                    # Program update may include defaults, but skip user data by default
                    continue
                dest = BASE_DIR / target_name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(n) as src, open(dest, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
        s.pop('pending_program_update', None)
        hist = s.setdefault('update_history', [])
        hist.append({'type':'program','file':zpath.name,'status':'applied','time':dt.datetime.now().isoformat(timespec='seconds')})
        s['last_program_update'] = zpath.stem
        save_settings(s)
        try: zpath.unlink()
        except Exception: pass
    except Exception as e:
        root=tk.Tk(); root.withdraw()
        messagebox.showerror('Program Update Failed', f'{e}\n\nBackup folder:\n{backup}')
        root.destroy()

def main():
    apply_pending_program_update()
    if not APP_FILE.exists():
        root=tk.Tk(); root.withdraw()
        messagebox.showerror('Startup Error', f'hub_app.py was not found.\n{APP_FILE}')
        return
    runpy.run_path(str(APP_FILE), run_name='__main__')

if __name__ == '__main__':
    main()
