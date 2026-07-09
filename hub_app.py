import json, os, sys, zipfile, shutil, datetime as dt, re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

APP_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
DATA_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else APP_DIR
CONFIG_DIR = DATA_DIR / 'config'; MASTERS_DIR = DATA_DIR / 'masters'; TEMPLATES_DIR = DATA_DIR / 'templates'; PROFILES_DIR = DATA_DIR / 'profiles'; LOGS_DIR = DATA_DIR / 'logs'; RECORDS_DIR = DATA_DIR / 'records'
for p in [CONFIG_DIR, MASTERS_DIR, TEMPLATES_DIR, PROFILES_DIR, LOGS_DIR, RECORDS_DIR]: p.mkdir(parents=True, exist_ok=True)
NON_ENGLISH_RE = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\u0e00-\u0e7f]')

APP_VERSION = '0.5 Alpha - Commit 0002u1'
PROGRAM_VERSION = '0.5.0002u1'
PROGRAM_COMMIT = '0002u1'

THEME = {
    'primary': '#005DAA',
    'primary_dark': '#07355F',
    'primary_mid': '#0079C2',
    'accent': '#00A4EF',
    'bg': '#F5F8FC',
    'surface': '#FFFFFF',
    'surface_2': '#EAF3FB',
    'line': '#D5E6F5',
    'text': '#1B1F2A',
    'muted': '#5D6D7E',
    'success': '#00A676',
    'warning': '#EF8A00',
    'admin': '#6A35AD'
}
FEATURES = {
    'complaint_tool': ('📝 Complaint', 'Create complaint, check English, generate Outlook mail or copy template.', '#005DAA'),
    'salesforce_auto_input': ('☁ Salesforce', 'Auto input mapped complaint fields to Salesforce on Microsoft Edge.', '#008A3D'),
    'update_master': ('📦 Update ZIP', 'Load update ZIP. Backup is created automatically.', '#EF8A00'),
    'master_zip_builder': ('🛠 Master Builder', 'Edit masters and create update ZIP package.', '#6A35AD'),
    'settings': ('⚙ Settings', 'Default country, output mode, language and paths.', '#008C9E'),
    'log_viewer': ('📋 Log Viewer', 'View application logs and operation history.', '#1976D2'),
    'about': ('ℹ About', 'Application information and version.', '#0A3A68'),
    'template_preview': ('📄 Template', 'Preview the generated mail/template content.', '#34699A'),
    'improvement_request': ('💡 Improvement', 'Create an improvement request mail/template.', '#00A4EF'),
    'system_number_request': ('➕ System No.', 'Create a system-number addition request.', '#00A676'),
}

LANGUAGES = {
    'en': 'English',
    'ja': '日本語',
    'ko': '한국어',
    'th': 'ไทย',
    'en-PH': 'English (PH)',
    'zh-TW': '繁體中文',
    'zh-CN': '简体中文'
}
COUNTRY_LANGUAGE = {
    'Japan': 'ja',
    'Korea': 'ko',
    'Thailand': 'th',
    'Philippines': 'en-PH',
    'Taiwan': 'zh-TW',
    'China': 'zh-CN',
    'India': 'en',
    'Australia': 'en',
    'Vietnam': 'en'
}
def default_language_for_company(company):
    countries = company.get('countries') or []
    if len(countries) == 1:
        return COUNTRY_LANGUAGE.get(countries[0], 'en')
    return company.get('default_language') or COUNTRY_LANGUAGE.get(countries[0], 'en') if countries else 'en'

def load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)
    except Exception: return default

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

def log_event(event, detail=''):
    with open(LOGS_DIR/'activity.log', 'a', encoding='utf-8') as f:
        f.write(f"{dt.datetime.now().isoformat(timespec='seconds')}\t{event}\t{detail}\n")

class Data:
    def __init__(self): self.reload()
    def reload(self):
        self.settings=load_json(CONFIG_DIR/'settings.json', {})
        self.users=load_json(CONFIG_DIR/'users.json', {'companies':[]})
        self.hospitals=load_json(MASTERS_DIR/'hospital_master.json', [])
        self.recipients=load_json(MASTERS_DIR/'recipients.json', {})
        self.fields=load_json(MASTERS_DIR/'field_definitions.json', {})
        self.templates=load_json(TEMPLATES_DIR/'email_template.json', {})
        self.translations=load_json(MASTERS_DIR/'translations.json', {'en': {}})
    def save_settings(self): save_json(CONFIG_DIR/'settings.json', self.settings)
    def user_key(self, session):
        try:
            return session['company']['company_id'] + '::' + session['user']['name']
        except Exception:
            return 'global'
    def user_defaults(self, session):
        return self.settings.setdefault('user_defaults', {}).setdefault(self.user_key(session), {})
    def get_default(self, session, key, fallback=None):
        return self.user_defaults(session).get(key, self.settings.get(key, fallback))
    def set_default(self, session, key, value):
        self.user_defaults(session)[key] = value
        self.settings[key] = value
        self.save_settings()

class LoginDialog(tk.Toplevel):
    def __init__(self, master, data):
        super().__init__(master); self.data=data; self.result=None; self.title('Startup Selection'); self.geometry('620x500'); self.resizable(False,False); self.configure(bg='#f3f8fd'); self.transient(master); self.grab_set(); self.protocol('WM_DELETE_WINDOW', self.cancel); self.after(50, self.bring_to_front)
        self.company_var=tk.StringVar(); self.password_var=tk.StringVar(); self.user_var=tk.StringVar(); self.actual_user_var=tk.StringVar()
        tk.Frame(self,bg=THEME['primary_dark'],height=76).pack(fill='x')
        hdr=tk.Label(self,text='InSightec Complaint Service Hub',fg='white',bg=THEME['primary_dark'],font=('Segoe UI',18,'bold')); hdr.place(x=24,y=18)
        body=ttk.Frame(self,padding=24); body.pack(fill='both',expand=True)
        ttk.Label(body,text='Company').grid(row=0,column=0,sticky='w',pady=8)
        self.company_cb=ttk.Combobox(body,textvariable=self.company_var,state='readonly',width=38,values=[c['display_name'] for c in data.users.get('companies',[])])
        self.company_cb.grid(row=0,column=1,sticky='ew',pady=8); self.company_cb.bind('<<ComboboxSelected>>', lambda e:self.on_company())
        ttk.Label(body,text='Password (InSightec only)').grid(row=1,column=0,sticky='w',pady=8)
        self.pw=ttk.Entry(body,textvariable=self.password_var,show='*',width=40); self.pw.grid(row=1,column=1,sticky='ew',pady=8)
        ttk.Label(body,text='User').grid(row=2,column=0,sticky='w',pady=8)
        self.user_cb=ttk.Combobox(body,textvariable=self.user_var,state='readonly',width=38); self.user_cb.grid(row=2,column=1,sticky='ew',pady=8)
        ttk.Label(body,text='Actual personal user\n(for shared users)').grid(row=3,column=0,sticky='w',pady=8)
        self.actual=ttk.Entry(body,textvariable=self.actual_user_var,width=40); self.actual.grid(row=3,column=1,sticky='ew',pady=8)
        info='Shared company users can log in, but Complaint input requires identifying the actual personal user before proceeding.'
        ttk.Label(body,text=info,wraplength=470,foreground='#345').grid(row=4,column=0,columnspan=2,sticky='w',pady=10)
        btns=ttk.Frame(body); btns.grid(row=5,column=0,columnspan=2,sticky='e',pady=18)
        ttk.Button(btns,text='Start',command=self.submit).pack(side='right',padx=4)
        ttk.Button(btns,text='Cancel',command=self.cancel).pack(side='right',padx=4)
        last=data.settings.get('last_company','InSightec'); self.company_var.set(last); self.on_company()

    def bring_to_front(self):
        try:
            self.lift()
            self.focus_force()
            self.attributes('-topmost', True)
            self.after(1500, lambda: self.attributes('-topmost', False))
        except Exception:
            pass
    def selected_company(self):
        return next((c for c in self.data.users.get('companies',[]) if c['display_name']==self.company_var.get()), None)
    def on_company(self):
        c=self.selected_company(); users=[u['name'] for u in (c or {}).get('users',[])]
        self.user_cb.configure(values=users); last_user=self.data.settings.get('last_user',''); self.user_var.set(last_user if last_user in users else (users[0] if users else ''))
    def submit(self):
        c=self.selected_company()
        if not c: return messagebox.showerror('Required','Select company.')
        if c.get('requires_password') and self.password_var.get()!=c.get('password'):
            return messagebox.showerror('Password','Password is incorrect.')
        u=next((u for u in c.get('users',[]) if u['name']==self.user_var.get()), None)
        if not u: return messagebox.showerror('Required','Select user.')
        if u.get('role')=='shared' and not self.actual_user_var.get().strip():
            return messagebox.showerror('Required','Please enter actual personal user before proceeding.')
        self.result={'company':c,'user':u,'actual_user':self.actual_user_var.get().strip()}
        self.destroy()
    def cancel(self): self.result=None; self.destroy()

class Hub(tk.Tk):
    def __init__(self):
        super().__init__(); self.withdraw(); self.data=Data(); self.session=None; self.admin_mode=False; self._closed_by_startup_cancel=False
        self.configure_ttk_style()
        self.title('InSightec Complaint Service Hub'); self.geometry('1320x850'); self.minsize(1120,700); self.configure(bg=THEME['bg'])
        if not self.login():
            self._closed_by_startup_cancel=True
            self.after(0, self.destroy)
            return
        self.language_var=tk.StringVar(self,value=self.current_language()); self.output_var=tk.StringVar(self,value=self.data.get_default(self.session,'default_output_mode','Copy Template'))
        self.deiconify(); self.lift(); self.focus_force(); self.build()

    def configure_ttk_style(self):
        style=ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('TFrame', background=THEME['bg'])
        style.configure('TLabel', background=THEME['bg'], foreground=THEME['text'], font=('Segoe UI',10))
        style.configure('TButton', font=('Segoe UI',10,'bold'), padding=(10,6))
        style.configure('TCombobox', padding=4)
    def current_language(self):
        if not self.session:
            return self.data.settings.get('default_language','en')
        if self.data.settings.get('language_mode') == 'manual':
            return self.data.settings.get('default_language','en')
        return default_language_for_company(self.session['company'])
    def tr(self, key, fallback=None):
        lang = self.language_var.get() if hasattr(self, 'language_var') else 'en'
        return self.data.translations.get(lang, self.data.translations.get('en', {})).get(key, fallback or key)
    def set_language(self, event=None):
        lang = self.language_var.get()
        self.data.settings['default_language'] = lang
        self.data.settings['language_mode'] = 'manual'
        self.data.set_default(self.session, 'default_language', lang)
        log_event('Language changed', lang)
        self.build()


    def feature_text(self, key):
        base_title, base_desc, color = FEATURES[key]
        title_map = {
            'complaint_tool': 'feature_complaint',
            'salesforce_auto_input': 'feature_salesforce',
            'update_master': 'feature_update',
            'master_zip_builder': 'feature_builder',
            'settings': 'feature_settings',
            'log_viewer': 'feature_log',
            'about': 'feature_about',
            'template_preview': 'feature_template',
            'improvement_request': 'feature_improvement',
            'system_number_request': 'feature_system'
        }
        desc_map = {
            'complaint_tool': 'desc_complaint',
            'salesforce_auto_input': 'desc_salesforce',
            'update_master': 'desc_update',
            'master_zip_builder': 'desc_builder',
            'settings': 'desc_settings',
            'log_viewer': 'desc_log',
            'about': 'desc_about',
            'template_preview': 'desc_template',
            'improvement_request': 'desc_improvement',
            'system_number_request': 'desc_system'
        }
        icon = base_title.split(' ', 1)[0]
        return icon + ' ' + self.tr(title_map.get(key,''), base_title.split(' ',1)[-1]), self.tr(desc_map.get(key,''), base_desc), color

    def set_output_mode(self, event=None):
        mode = self.output_var.get()
        self.data.set_default(self.session, 'default_output_mode', mode)
        log_event('Output mode changed', mode)

    def login(self):
        dlg=LoginDialog(self,self.data); self.wait_window(dlg)
        if not dlg.result:
            return False
        self.session=dlg.result; self.data.settings['last_company']=self.session['company']['display_name']; self.data.settings['last_user']=self.session['user']['name']
        if self.data.settings.get('language_mode','auto') == 'auto':
            self.data.settings['default_language'] = default_language_for_company(self.session['company'])
        self.data.save_settings(); log_event('Login', f"{self.session['company']['display_name']} / {self.session['user']['name']}")
        return True
    def get_features(self):
        c=self.session['company']; u=self.session['user']
        if c['company_id']=='insightec' and u.get('admin_switch_allowed') and self.admin_mode:
            feats = list(c.get('features_admin', []))
        else:
            feats = list(c.get('features_user', []))
        for k in ['settings', 'template_preview', 'improvement_request', 'system_number_request']:
            if k not in feats:
                feats.append(k)
        return feats
    def clear(self):
        for w in self.winfo_children(): w.destroy()
    def build(self):
        if not self.session: return
        self.clear()
        self.sidebar=tk.Frame(self,bg=THEME['primary_dark'],width=260); self.sidebar.pack(side='left',fill='y'); self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar,text='InSightec',bg=THEME['primary_dark'],fg='white',font=('Segoe UI',30,'bold italic')).pack(anchor='w',padx=22,pady=(26,0))
        tk.Label(self.sidebar,text='Bringing therapy into focus',bg=THEME['primary_dark'],fg='#D7ECFF',font=('Segoe UI',10,'bold italic')).pack(anchor='w',padx=28,pady=(0,22))
        box=tk.Frame(self.sidebar,bg='#0B4A82',highlightbackground=THEME['accent'],highlightthickness=1); box.pack(fill='x',padx=18,pady=12)
        tk.Label(box,text='Complaint Service Hub\n'+APP_VERSION,justify='left',bg='#0B4A82',fg='white',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=14,pady=12)
        for key in self.get_features():
            name=self.feature_text(key)[0]; b=tk.Button(self.sidebar,text='  '+name,anchor='w',relief='flat',bg=THEME['primary_dark'],fg='white',activebackground=THEME['primary_mid'],activeforeground='white',font=('Segoe UI',11),command=lambda k=key:self.open_feature(k)); b.pack(fill='x',padx=14,pady=3,ipady=8)
        tk.Label(self.sidebar,text='\nCompany: '+self.session['company']['display_name']+'\nUser: '+self.session['user']['name']+'\nOutput: '+self.output_var.get(),bg=THEME['primary_dark'],fg='#D7ECFF',justify='left',font=('Segoe UI',9)).pack(side='bottom',anchor='w',padx=18,pady=18)
        self.main=tk.Frame(self,bg=THEME['bg']); self.main.pack(side='left',fill='both',expand=True)
        self.home()
    def header(self):
        h=tk.Frame(self.main,bg=THEME['bg']); h.pack(fill='x',padx=30,pady=(22,8))
        title=tk.Frame(h,bg=THEME['bg']); title.pack(side='left')
        tk.Label(title,text='InSightec',fg=THEME['primary'],bg=THEME['bg'],font=('Segoe UI',30,'bold')).pack(side='left')
        tk.Label(title,text=' '+self.tr('title','Complaint Service Hub'),fg=THEME['text'],bg=THEME['bg'],font=('Segoe UI',22,'bold')).pack(side='left',padx=10)
        tk.Label(title,text=APP_VERSION,fg=THEME['muted'],bg=THEME['bg'],font=('Segoe UI',10,'bold')).pack(side='left',padx=8)
        ctrl=tk.Frame(h,bg=THEME['bg']); ctrl.pack(side='right')
        if self.session['company']['company_id']=='insightec' and self.session['user'].get('admin_switch_allowed'):
            txt='Admin Mode: ON' if self.admin_mode else 'Admin Mode: OFF'
            tk.Button(ctrl,text=txt,bg='#FFD24A' if self.admin_mode else 'white',fg=THEME['primary_dark'],command=self.toggle_admin,relief='solid',bd=1).pack(side='right',padx=5,ipadx=10,ipady=7)
        ttk.Label(ctrl,text=self.tr('output','Output')).pack(side='left',padx=(10,4))
        out_cb=ttk.Combobox(ctrl,textvariable=self.output_var,state='readonly',width=15,values=['Outlook','Copy Template'])
        out_cb.pack(side='left'); out_cb.bind('<<ComboboxSelected>>', self.set_output_mode)
        ttk.Label(ctrl,text=self.tr('language','Language')).pack(side='left',padx=(14,4))
        lang_cb=ttk.Combobox(ctrl,textvariable=self.language_var,state='readonly',width=8,values=list(LANGUAGES.keys()))
        lang_cb.pack(side='left'); lang_cb.bind('<<ComboboxSelected>>', self.set_language)
        tk.Label(ctrl,text=self.session['user']['name'],fg=THEME['primary_dark'],bg='white',font=('Segoe UI',10,'bold'),relief='solid',bd=1,padx=14,pady=8).pack(side='left',padx=(14,0))
        sub=tk.Frame(self.main,bg=THEME['bg']); sub.pack(fill='x',padx=34)
        tk.Label(sub,text=self.tr('company','Company')+': '+self.session['company']['display_name']+'   |   '+self.tr('language','Language')+': '+LANGUAGES.get(self.language_var.get(), self.language_var.get())+'   |   '+self.tr('output','Output')+': '+self.output_var.get(),bg=THEME['bg'],fg=THEME['text'],font=('Segoe UI',11)).pack(side='left')
        tk.Frame(self.main,bg='#B6D4EE',height=1).pack(fill='x',padx=30,pady=14)
    def home(self):
        for w in self.main.winfo_children(): w.destroy()
        self.header()
        canvas=tk.Canvas(self.main,bg=THEME['bg'],highlightthickness=0)
        vsb=ttk.Scrollbar(self.main,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side='left',fill='both',expand=True,padx=(28,0),pady=4)
        vsb.pack(side='right',fill='y')
        wrap=tk.Frame(canvas,bg=THEME['bg'])
        canvas_window=canvas.create_window((0,0),window=wrap,anchor='nw')
        def _on_config(event=None):
            canvas.configure(scrollregion=canvas.bbox('all'))
            try: canvas.itemconfigure(canvas_window, width=canvas.winfo_width())
            except Exception: pass
        wrap.bind('<Configure>', _on_config); canvas.bind('<Configure>', _on_config)
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))
        feats=self.get_features()
        user_feats=[f for f in feats if f not in ['master_zip_builder','log_viewer','about']]
        admin_feats=[f for f in feats if f in ['master_zip_builder','log_viewer','about']]
        tk.Label(wrap,text=self.tr('launch_pad','Launch Pad'),bg=THEME['bg'],fg=THEME['primary_dark'],font=('Segoe UI',17,'bold')).grid(row=0,column=0,columnspan=3,sticky='w',padx=12,pady=(0,4))
        row=1
        for i,key in enumerate(user_feats): self.card(wrap,key,row+i//3,i%3)
        row += (len(user_feats)+2)//3
        if admin_feats:
            sep=tk.Label(wrap,text=self.tr('admin_only','Admin Only'),bg=THEME['bg'],fg=THEME['admin'],font=('Segoe UI',13,'bold'))
            sep.grid(row=row,column=0,columnspan=3,sticky='w',padx=12,pady=(18,4)); row+=1
            for i,key in enumerate(admin_feats): self.card(wrap,key,row+i//3,i%3,admin=True)
        foot=tk.Frame(self.main,bg=THEME['primary_dark'],height=48); foot.pack(fill='x',side='bottom')
        status='  ✓ Ready     Program: '+APP_VERSION+'     Master Update: '+self.data.settings.get('last_master_update','Initial')+'     Language: '+LANGUAGES.get(self.language_var.get(), self.language_var.get())+'     Output: '+self.output_var.get()
        tk.Label(foot,text=status,bg=THEME['primary_dark'],fg='white',font=('Segoe UI',10)).pack(side='left',pady=13)
    def card(self,parent,key,r,c,admin=False):
        title,desc,color=self.feature_text(key)
        f=tk.Frame(parent,bg='white',highlightbackground=THEME['line'],highlightthickness=1,width=335,height=205,cursor='hand2')
        f.grid(row=r,column=c,sticky='nsew',padx=10,pady=10)
        f.grid_propagate(False)
        parent.columnconfigure(c,weight=1)
        parent.rowconfigure(r,weight=1)
        tk.Frame(f,bg=color,height=5).grid(row=0,column=0,sticky='ew')
        f.columnconfigure(0,weight=1)
        f.rowconfigure(2,weight=1)
        title_lbl=tk.Label(f,text=title,bg='white',fg=color,font=('Segoe UI',15,'bold'),anchor='w')
        title_lbl.grid(row=1,column=0,sticky='ew',padx=18,pady=(14,6))
        desc_lbl=tk.Label(f,text=desc,bg='white',fg=THEME['text'],wraplength=280,justify='left',font=('Segoe UI',10),anchor='nw')
        desc_lbl.grid(row=2,column=0,sticky='nsew',padx=18,pady=2)
        badge=self.tr('available_all','Available to all users') if key=='settings' else (self.tr('admin_only','Admin only') if admin else self.tr('user_tool','User tool'))
        badge_lbl=tk.Label(f,text=badge,bg=THEME['surface_2'],fg=THEME['primary_dark'],font=('Segoe UI',9,'bold'),padx=8,pady=3,anchor='w')
        badge_lbl.grid(row=3,column=0,sticky='w',padx=18,pady=(0,6))
        btn=tk.Button(f,text='Start  ›',bg=color,fg='white',activebackground=color,activeforeground='white',font=('Segoe UI',11,'bold'),relief='flat',command=lambda:self.open_feature(key),cursor='hand2')
        btn.grid(row=4,column=0,sticky='ew',padx=18,pady=(0,14),ipady=5)
        def click_anywhere(event=None):
            self.open_feature(key)
        for w in (f,title_lbl,desc_lbl,badge_lbl):
            w.bind('<Button-1>', click_anywhere)
    def toggle_admin(self): self.admin_mode=not self.admin_mode; self.build()
    def open_feature(self,key):
        if key=='complaint_tool': return ComplaintWindow(self,self.data,self.session)
        if key=='update_master': return self.update_master()
        if key=='salesforce_auto_input': return SalesforceWindow(self,self.session)
        if key=='master_zip_builder': return MasterBuilderWindow(self)
        if key=='log_viewer': return LogWindow(self)
        if key=='settings': return SettingsWindow(self,self.data,self.session,lambda: self.build())
        if key=='template_preview': return TemplatePreviewWindow(self,self.data,self.output_var.get())
        if key=='improvement_request': return RequestWindow(self,self.data,self.session,self.output_var.get(),'Improvement Request')
        if key=='system_number_request': return RequestWindow(self,self.data,self.session,self.output_var.get(),'System Number Addition Request')
        messagebox.showinfo(FEATURES[key][0], 'Prototype screen. Detailed function will be added in the next build.')
    def update_master(self):
        path=filedialog.askopenfilename(title='Select update ZIP',filetypes=[('ZIP','*.zip')])
        if not path: return
        try:
            manifest={}
            with zipfile.ZipFile(path) as z:
                if 'update_manifest.json' in z.namelist():
                    manifest=json.loads(z.read('update_manifest.json').decode('utf-8'))
                elif 'manifest.json' in z.namelist():
                    manifest=json.loads(z.read('manifest.json').decode('utf-8'))
                update_type=manifest.get('update_type','master')
            if update_type == 'program':
                updates_dir=DATA_DIR/'updates'; updates_dir.mkdir(exist_ok=True)
                pending=updates_dir/'pending_program_update.zip'
                shutil.copy2(path,pending)
                self.data.settings.setdefault('update_history',[]).append({'type':'program','file':Path(path).name,'status':'pending_restart','time':dt.datetime.now().isoformat(timespec='seconds')})
                self.data.settings['pending_program_update']='updates/pending_program_update.zip'
                self.data.save_settings()
                messagebox.showinfo('Program Update','Program update is staged. Please close and restart the Hub/Launcher to apply it safely.')
                log_event('Program update staged', path)
                return
            self.apply_master_update(path, manifest)
        except Exception as e:
            messagebox.showerror('Update failed', str(e))

    def apply_master_update(self, path, manifest=None):
        allowed_prefixes=['config/','masters/','templates/','profiles/','resources/']
        backup=DATA_DIR/'backups'/f"master_backup_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"; backup.mkdir(parents=True,exist_ok=True)
        for d in ['config','masters','templates','profiles','resources']:
            if (DATA_DIR/d).exists(): shutil.copytree(DATA_DIR/d, backup/d, dirs_exist_ok=True)
        changed=[]
        try:
            with zipfile.ZipFile(path) as z:
                names=[n for n in z.namelist() if not n.endswith('/')]
                for n in names:
                    if n in ['update_manifest.json','manifest.json']:
                        continue
                    if not any(n.startswith(p) for p in allowed_prefixes):
                        continue
                    z.extract(n, DATA_DIR); changed.append(n)
            hist=self.data.settings.setdefault('update_history',[])
            hist.append({'type':'master','file':Path(path).name,'status':'applied','changed':len(changed),'time':dt.datetime.now().isoformat(timespec='seconds'),'version':(manifest or {}).get('version','')})
            self.data.settings['last_master_update']=(manifest or {}).get('version') or Path(path).stem
            self.data.save_settings(); self.data.reload(); log_event('Master update applied', f"{path} ({len(changed)} files)")
            messagebox.showinfo('Master Update',f'Master update completed.\nChanged files: {len(changed)}\nBackup: {backup}')
            self.build()
        except Exception as e:
            restore=messagebox.askyesno('Update failed', f'{e}\n\nRestore backup?')
            if restore:
                for d in ['config','masters','templates','profiles','resources']:
                    src=backup/d; dst=DATA_DIR/d
                    if src.exists():
                        if dst.exists(): shutil.rmtree(dst)
                        shutil.copytree(src,dst)
                self.data.reload(); self.build()
            raise

class ComplaintWindow(tk.Toplevel):
    def __init__(self,master,data,session):
        super().__init__(master); self.data=data; self.session=session; self.title('Complaint Tool'); self.geometry('950x720'); self.configure(bg='#f6fbff')
        default_country=data.get_default(session,'default_country') if data.get_default(session,'default_country') in session['company'].get('countries',[]) else (session['company'].get('countries') or ['India'])[0]
        self.country=tk.StringVar(value=default_country); self.hospital=tk.StringVar(value=data.get_default(session,'default_hospital','')); self.serial=tk.StringVar(value=data.get_default(session,'default_serial','')); self.output=tk.StringVar(value=data.get_default(session,'default_output_mode','Copy Template'))
        frm=ttk.Frame(self,padding=14); frm.pack(fill='both',expand=True); frm.columnconfigure(1,weight=1); frm.rowconfigure(7,weight=1)
        ttk.Label(frm,text='Complaint Tool',font=('Segoe UI',18,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=8)
        self.combo(frm,1,'Country',self.country,session['company'].get('countries',[]),self.refresh_hospitals)
        self.hcb=self.combo(frm,2,'Hospital Name',self.hospital,[],self.on_hospital)
        self.scb=self.combo(frm,3,'System Serial',self.serial,[],self.on_serial)
        self.subject=tk.StringVar(); ttk.Label(frm,text='Subject').grid(row=4,column=0,sticky='w'); ttk.Entry(frm,textvariable=self.subject).grid(row=4,column=1,sticky='ew',pady=4)
        ttk.Label(frm,text='Description (English only)').grid(row=5,column=0,sticky='nw'); self.desc=scrolledtext.ScrolledText(frm,height=10,wrap='word'); self.desc.grid(row=5,column=1,sticky='nsew',pady=4)
        self.combo(frm,6,'Output Mode',self.output,['Outlook','Copy Template'],None)
        self.preview=scrolledtext.ScrolledText(frm,height=12,wrap='word'); self.preview.grid(row=7,column=0,columnspan=2,sticky='nsew',pady=8)
        btn=ttk.Frame(frm); btn.grid(row=8,column=0,columnspan=2,sticky='e')
        ttk.Button(btn,text='Generate Mail / Template',command=self.generate).pack(side='right',padx=4); ttk.Button(btn,text='Save Record',command=self.save).pack(side='right',padx=4)
        self.refresh_hospitals()
    def combo(self,p,r,l,v,vals,cmd):
        ttk.Label(p,text=l).grid(row=r,column=0,sticky='w',pady=4); cb=ttk.Combobox(p,textvariable=v,values=vals,state='normal'); cb.grid(row=r,column=1,sticky='ew',pady=4)
        if cmd: cb.bind('<<ComboboxSelected>>',lambda e:cmd())
        return cb
    def remember_defaults(self):
        self.data.set_default(self.session, 'default_country', self.country.get())
        self.data.set_default(self.session, 'default_hospital', self.hospital.get())
        self.data.set_default(self.session, 'default_serial', self.serial.get())
        self.data.set_default(self.session, 'default_output_mode', self.output.get())

    def refresh_hospitals(self):
        self.remember_defaults()
        hs=[h for h in self.data.hospitals if h.get('country')==self.country.get()]
        self.hcb.configure(values=[h.get('hospital_name','') for h in hs]); self.scb.configure(values=[h.get('system_serial','') for h in hs])
    def on_hospital(self):
        self.remember_defaults()
        m=[h for h in self.data.hospitals if h.get('country')==self.country.get() and h.get('hospital_name')==self.hospital.get()]
        if len(m)==1: self.serial.set(m[0].get('system_serial',''))
    def on_serial(self):
        self.remember_defaults()
        m=[h for h in self.data.hospitals if h.get('country')==self.country.get() and h.get('system_serial')==self.serial.get()]
        if len(m)==1: self.hospital.set(m[0].get('hospital_name',''))
    def values(self): return {'country':self.country.get(),'hospital':self.hospital.get(),'serial':self.serial.get(),'subject':self.subject.get(),'description':self.desc.get('1.0','end').strip(),'user':self.session['actual_user'] or self.session['user']['name'],'company':self.session['company']['display_name']}
    def generate(self):
        v=self.values(); txt=v['subject']+'\n'+v['description']
        if NON_ENGLISH_RE.search(txt): return messagebox.showerror('English check','Non-English characters were detected. Please write in English.')
        body=f"Complaint Subject: {v['subject']}\n\nDescription:\n{v['description']}\n\nCountry: {v['country']}\nHospital: {v['hospital']}\nSerial: {v['serial']}\nReporter: {v['user']}\nCompany: {v['company']}"
        self.preview.delete('1.0','end'); self.preview.insert('1.0',body); log_event('Complaint template generated', v['subject'])
        if self.output.get()=='Outlook': messagebox.showinfo('Outlook','Outlook creation is enabled in Windows build. Preview was generated here.')
    def save(self):
        v=self.values(); path=RECORDS_DIR/f"complaint_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"; save_json(path,v); messagebox.showinfo('Saved',str(path)); log_event('Record saved',str(path))

class SalesforceWindow(tk.Toplevel):
    def __init__(self,master,session):
        super().__init__(master); self.title('Salesforce Auto Input'); self.geometry('720x420')
        txt='Open Salesforce in Microsoft Edge, open the input form, click anywhere inside the editable form, then this tool will input all mapped fields. Submit/Save is not clicked automatically.'
        ttk.Label(self,text='Salesforce Auto Input',font=('Segoe UI',18,'bold')).pack(anchor='w',padx=18,pady=18); ttk.Label(self,text=txt,wraplength=650).pack(anchor='w',padx=18); ttk.Button(self,text='Start Auto Input Prototype',command=lambda:messagebox.showinfo('Prototype','Auto input engine placeholder. Screenshot-based mapping will be added after Salesforce screenshots are provided.')).pack(pady=30)
class MasterBuilderWindow(tk.Toplevel):
    def __init__(self,master): super().__init__(master); self.title('Master ZIP Builder'); self.geometry('650x380'); ttk.Label(self,text='Master ZIP Builder',font=('Segoe UI',18,'bold')).pack(padx=18,pady=18); ttk.Button(self,text='Create Update ZIP from current config/masters/templates/profiles',command=self.make_zip).pack(pady=20)
    def make_zip(self):
        out=DATA_DIR/f"master_update_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for d in ['config','masters','templates','profiles']:
                for p in (DATA_DIR/d).rglob('*'):
                    if p.is_file(): z.write(p,p.relative_to(DATA_DIR))
        messagebox.showinfo('Created',str(out))
class LogWindow(tk.Toplevel):
    def __init__(self,master): super().__init__(master); self.title('Log Viewer'); self.geometry('800x500'); t=scrolledtext.ScrolledText(self); t.pack(fill='both',expand=True); t.insert('1.0',(LOGS_DIR/'activity.log').read_text(encoding='utf-8') if (LOGS_DIR/'activity.log').exists() else '')

class TemplatePreviewWindow(tk.Toplevel):
    def __init__(self,master,data,mode):
        super().__init__(master); self.title('Template Preview'); self.geometry('820x560'); self.configure(bg='#F5F8FC')
        frm=ttk.Frame(self,padding=18); frm.pack(fill='both',expand=True); frm.rowconfigure(2,weight=1); frm.columnconfigure(0,weight=1)
        ttk.Label(frm,text='Template Preview',font=('Segoe UI',18,'bold')).grid(row=0,column=0,sticky='w')
        ttk.Label(frm,text=f'Current Output Mode: {mode}').grid(row=1,column=0,sticky='w',pady=8)
        t=scrolledtext.ScrolledText(frm,wrap='word'); t.grid(row=2,column=0,sticky='nsew')
        sample = 'To: [country recipients]\nCC: [country cc]\nSubject: Complaint - [Hospital] - [Serial] - [Subject]\n\nDear Team,\n\nPlease find the complaint details below.\n\nComplaint Subject: [Subject]\nDescription: [English description]\nCountry: [Country]\nHospital: [Hospital]\nSerial: [Serial]\nReporter: [User]\n\nBest regards,'
        t.insert('1.0',sample)
        ttk.Button(frm,text='Copy to Clipboard',command=lambda:(self.clipboard_clear(),self.clipboard_append(t.get('1.0','end').strip()),messagebox.showinfo('Copied','Template copied.'))).grid(row=3,column=0,sticky='e',pady=10)

class RequestWindow(tk.Toplevel):
    def __init__(self,master,data,session,mode,title):
        super().__init__(master); self.data=data; self.session=session; self.mode=mode; self.title(title); self.geometry('840x620'); self.configure(bg='#F5F8FC')
        frm=ttk.Frame(self,padding=18); frm.pack(fill='both',expand=True); frm.columnconfigure(1,weight=1); frm.rowconfigure(4,weight=1)
        ttk.Label(frm,text=title,font=('Segoe UI',18,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,12))
        self.subject=tk.StringVar(value=title)
        self.category=tk.StringVar(value='Master / Specification')
        ttk.Label(frm,text='Category').grid(row=1,column=0,sticky='w',pady=5)
        ttk.Combobox(frm,textvariable=self.category,values=['Master / Specification','UI Improvement','Bug Report','System Number Addition','Other'],state='readonly').grid(row=1,column=1,sticky='ew',pady=5)
        ttk.Label(frm,text='Subject').grid(row=2,column=0,sticky='w',pady=5)
        ttk.Entry(frm,textvariable=self.subject).grid(row=2,column=1,sticky='ew',pady=5)
        ttk.Label(frm,text='Details (English)').grid(row=3,column=0,sticky='nw',pady=5)
        self.details=scrolledtext.ScrolledText(frm,height=12,wrap='word'); self.details.grid(row=4,column=0,columnspan=2,sticky='nsew')
        self.preview=scrolledtext.ScrolledText(frm,height=8,wrap='word'); self.preview.grid(row=5,column=0,columnspan=2,sticky='ew',pady=8)
        btn=ttk.Frame(frm); btn.grid(row=6,column=0,columnspan=2,sticky='e')
        ttk.Button(btn,text='Generate Request',command=self.generate).pack(side='right',padx=4)
    def generate(self):
        details=self.details.get('1.0','end').strip()
        if NON_ENGLISH_RE.search(details+self.subject.get()):
            return messagebox.showerror('English check','Non-English characters were detected. Please write request details in English.')
        body=f"Request Type: {self.category.get()}\nSubject: {self.subject.get()}\n\nDetails:\n{details}\n\nCompany: {self.session['company']['display_name']}\nUser: {self.session.get('actual_user') or self.session['user']['name']}\nOutput Mode: {self.mode}"
        self.preview.delete('1.0','end'); self.preview.insert('1.0',body)
        log_event('Request generated', self.subject.get())
        if self.mode=='Outlook': messagebox.showinfo('Outlook','Outlook creation is enabled in Windows build. Preview was generated here.')

class SettingsWindow(tk.Toplevel):
    def __init__(self,master,data,session,on_saved=None):
        super().__init__(master); self.data=data; self.session=session; self.on_saved=on_saved
        self.title('Settings'); self.geometry('720x460'); self.configure(bg='#f6fbff')
        self.lang_mode=tk.StringVar(value=data.settings.get('language_mode','auto'))
        self.lang=tk.StringVar(value=data.get_default(session,'default_language', default_language_for_company(session['company'])))
        self.country=tk.StringVar(value=data.get_default(session,'default_country', (session['company'].get('countries') or [''])[0]))
        self.output=tk.StringVar(value=data.get_default(session,'default_output_mode','Copy Template'))
        frm=ttk.Frame(self,padding=24); frm.pack(fill='both',expand=True); frm.columnconfigure(1,weight=1)
        ttk.Label(frm,text='Settings',font=('Segoe UI',18,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,18))
        ttk.Label(frm,text='Language Mode').grid(row=1,column=0,sticky='w',pady=8)
        ttk.Combobox(frm,textvariable=self.lang_mode,state='readonly',values=['auto','manual']).grid(row=1,column=1,sticky='ew',pady=8)
        ttk.Label(frm,text='UI Language').grid(row=2,column=0,sticky='w',pady=8)
        ttk.Combobox(frm,textvariable=self.lang,state='readonly',values=list(LANGUAGES.keys())).grid(row=2,column=1,sticky='ew',pady=8)
        ttk.Label(frm,text='Default Country').grid(row=3,column=0,sticky='w',pady=8)
        ttk.Combobox(frm,textvariable=self.country,state='readonly',values=session['company'].get('countries',[])).grid(row=3,column=1,sticky='ew',pady=8)
        ttk.Label(frm,text='Default Output Mode').grid(row=4,column=0,sticky='w',pady=8)
        ttk.Combobox(frm,textvariable=self.output,state='readonly',values=['Outlook','Copy Template']).grid(row=4,column=1,sticky='ew',pady=8)
        info='Auto language uses company/country default. You can switch language anytime from the top dropdown or set manual language here.\nInstalled updates: '+str(len(data.settings.get('update_history', [])))
        ttk.Label(frm,text=info,wraplength=620,foreground='#345').grid(row=5,column=0,columnspan=2,sticky='w',pady=18)
        ttk.Button(frm,text='Save Settings',command=self.save).grid(row=6,column=1,sticky='e',pady=18)
    def save(self):
        self.data.settings['language_mode']=self.lang_mode.get()
        self.data.set_default(self.session, 'default_language', self.lang.get())
        self.data.set_default(self.session, 'default_country', self.country.get())
        self.data.set_default(self.session, 'default_output_mode', self.output.get())
        self.data.save_settings(); log_event('Settings saved', self.lang.get())
        if hasattr(self.master, 'language_var'):
            self.master.language_var.set(self.lang.get())
        if hasattr(self.master, 'output_var'):
            self.master.output_var.set(self.output.get())
        messagebox.showinfo('Settings','Settings saved.')
        if self.on_saved: self.on_saved()
        self.destroy()

if __name__=='__main__':
    Hub().mainloop()
