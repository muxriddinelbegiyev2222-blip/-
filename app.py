import csv
from datetime import datetime
import hashlib
import os
import re
import sqlite3
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --- 1. PORTABLE TIZIM VA BAZA SOZLAMALARI ---
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(APP_DIR, 'Maxfiy_Baza')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'kadastr_komplayens.db')

CORRUPTION_ARTICLES = ['167', '168', '205', '206', '207', '208', '209', '210', '211', '212', '228']

def hash_password(password, salt='UzKadastr2026!'):
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    fullname TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS records (
                    pinfl TEXT PRIMARY KEY,
                    fullname TEXT NOT NULL,
                    birth_date TEXT NOT NULL,
                    articles TEXT NOT NULL,
                    details TEXT NOT NULL,
                    risk_level TEXT,
                    added_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    action TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password_hash, fullname, role) VALUES (?, ?, ?, ?)",
                  ('admin', hash_password('Admin123'), 'Bosh Administrator', 'ADMIN'))
    conn.commit()
    conn.close()

init_db()

def log_audit(username, action, details):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO audit_logs (username, action, details) VALUES (?, ?, ?)', (username, action, details))
        conn.commit()
        conn.close()
    except Exception: pass

# --- 2. ASOSIY GRAFIK TIZIM ---
class ProfessionalComplianceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('KADASTR AGENTLIGI - KOMPLAYENS VA ICHKI NAZORAT TIZIMI (PRO)')
        self.geometry('1200x750')
        self.minsize(1000, 700)
        self.configure(bg='#0F172A')
        
        self.current_user = None
        self.current_role = None
        
        self.setup_styles()
        self.show_login_screen()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TNotebook', background='#1E293B', borderwidth=0)
        self.style.configure('TNotebook.Tab', background='#334155', foreground='#E2E8F0', font=('Segoe UI', 10, 'bold'), padding=[15, 10])
        self.style.map('TNotebook.Tab', background=[('selected', '#2563EB')], foreground=[('selected', '#FFFFFF')])
        
        self.style.configure('Treeview', font=('Segoe UI', 10), rowheight=30, background='#1E293B', foreground='#F1F5F9', fieldbackground='#1E293B')
        self.style.map('Treeview', background=[('selected', '#3B82F6')])
        self.style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'), background='#0F172A', foreground='#38BDF8')

    def clear_window(self):
        for widget in self.winfo_children(): widget.destroy()

    # ================= LOGIN =================
    def show_login_screen(self):
        self.clear_window()
        self.configure(bg='#0F172A')
        card = tk.Frame(self, bg='#1E293B', padx=50, pady=40)
        card.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        tk.Label(card, text='TIZIMGA KIRISH', font=('Segoe UI', 18, 'bold'), fg='#38BDF8', bg='#1E293B').pack(pady=(0, 20))
        
        tk.Label(card, text='Login:', font=('Segoe UI', 11, 'bold'), fg='#F1F5F9', bg='#1E293B').pack(anchor=tk.W)
        self.ent_login = tk.Entry(card, font=('Segoe UI', 13), width=30, bg='#0F172A', fg='#FFF', insertbackground='white', relief=tk.FLAT)
        self.ent_login.pack(pady=(5, 15), ipady=8)
        
        tk.Label(card, text='Parol:', font=('Segoe UI', 11, 'bold'), fg='#F1F5F9', bg='#1E293B').pack(anchor=tk.W)
        self.ent_pwd = tk.Entry(card, font=('Segoe UI', 13), width=30, show='•', bg='#0F172A', fg='#FFF', insertbackground='white', relief=tk.FLAT)
        self.ent_pwd.pack(pady=(5, 25), ipady=8)
        self.ent_pwd.bind('<Return>', lambda e: self.process_login())

        tk.Button(card, text='KIRISH', font=('Segoe UI', 12, 'bold'), bg='#2563EB', fg='white', relief=tk.FLAT, cursor='hand2', command=self.process_login).pack(fill=tk.X, ipady=8)

    def process_login(self):
        u = self.ent_login.get().strip()
        p = self.ent_pwd.get().strip()
        if not u or not p: return messagebox.showwarning('Xato', 'Maydonlarni to‘ldiring!')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT username, role, password_hash FROM users WHERE username = ?', (u,))
        row = c.fetchone()
        conn.close()

        if row and row[2] == hash_password(p):
            self.current_user = row[0]
            self.current_role = row[1]
            log_audit(self.current_user, 'KIRISH', 'Tizimga muvaffaqiyatli kirdi')
            self.show_main_workspace()
        else:
            messagebox.showerror('Xato', 'Login yoki parol noto‘g‘ri!')

    # ================= MAIN WORKSPACE =================
    def show_main_workspace(self):
        self.clear_window()
        header = tk.Frame(self, bg='#0F172A', height=60, padx=20)
        header.pack(fill=tk.X)
        tk.Label(header, text='KADASTR TIZIMI | KOMPLAYENS NAZORAT', font=('Segoe UI', 14, 'bold'), fg='#38BDF8', bg='#0F172A').pack(side=tk.LEFT, pady=15)
        tk.Button(header, text='Tizimdan chiqish', font=('Segoe UI', 10, 'bold'), bg='#EF4444', fg='white', relief=tk.FLAT, padx=15, command=self.show_login_screen).pack(side=tk.RIGHT, pady=15)
        tk.Label(header, text=f'Foydalanuvchi: {self.current_user} ({self.current_role})', font=('Segoe UI', 11), fg='#94A3B8', bg='#0F172A').pack(side=tk.RIGHT, padx=30, pady=15)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)

        tab_dash = tk.Frame(nb, bg='#1E293B')
        tab_check = tk.Frame(nb, bg='#1E293B')
        tab_db = tk.Frame(nb, bg='#1E293B')
        
        nb.add(tab_dash, text='  📊 Dashboard (Statistika)  ')
        nb.add(tab_check, text='  🔍 Tekshiruv & Kiritish  ')
        nb.add(tab_db, text='  📁 Umumiy Baza (Tahrirlash)  ')

        self.build_dashboard(tab_dash)
        self.build_check_tab(tab_check)
        self.build_database_tab(tab_db)

        if self.current_role == 'ADMIN':
            tab_admin = tk.Frame(nb, bg='#1E293B')
            nb.add(tab_admin, text='  ⚙️ Admin Sozlamalari & Audit  ')
            self.build_admin_tab(tab_admin)

    # ================= 1. DASHBOARD =================
    def build_dashboard(self, parent):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM records')
        total_rec = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM records WHERE risk_level='YUQORI'")
        high_risk = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        conn.close()

        f = tk.Frame(parent, bg='#1E293B', padx=40, pady=40)
        f.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(f, text='TIZIM STATISTIKASI VA HOLATI', font=('Segoe UI', 16, 'bold'), fg='#F1F5F9', bg='#1E293B').grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 30))
        
        self.create_stat_card(f, 'Umumiy Sudlanganlar', total_rec, '#3B82F6', 1, 0)
        self.create_stat_card(f, 'Yuqori Korrupsion Xavf', high_risk, '#EF4444', 1, 1)
        self.create_stat_card(f, 'Faol Xodimlar', total_users, '#10B981', 1, 2)

    def create_stat_card(self, parent, title, value, color, r, c):
        card = tk.Frame(parent, bg='#0F172A', padx=30, pady=25, highlightbackground=color, highlightthickness=2)
        card.grid(row=r, column=c, padx=15, pady=10, sticky=tk.NSEW)
        tk.Label(card, text=title, font=('Segoe UI', 12), fg='#94A3B8', bg='#0F172A').pack(anchor=tk.W)
        tk.Label(card, text=str(value), font=('Segoe UI', 28, 'bold'), fg=color, bg='#0F172A').pack(anchor=tk.W, pady=(10, 0))

    # ================= 2. TEKSHIRUV VA KIRITISH =================
    def build_check_tab(self, parent):
        top_f = tk.Frame(parent, bg='#0F172A', padx=20, pady=20)
        top_f.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(top_f, text='JSHSHIR orqali qidirish (14 xonali):', font=('Segoe UI', 12, 'bold'), fg='#FFF', bg='#0F172A').pack(side=tk.LEFT, padx=10)
        self.ent_q = tk.Entry(top_f, font=('Segoe UI', 14, 'bold'), width=20)
        self.ent_q.pack(side=tk.LEFT, padx=10, ipady=5)
        
        tk.Button(top_f, text='🔍 TEKSHIRISH', font=('Segoe UI', 11, 'bold'), bg='#2563EB', fg='white', relief=tk.FLAT, padx=20, command=self.do_search).pack(side=tk.LEFT, padx=10, ipady=4)
        tk.Button(top_f, text='📄 Xulosa Chiqarish', font=('Segoe UI', 11, 'bold'), bg='#8B5CF6', fg='white', relief=tk.FLAT, padx=15, command=self.export_report).pack(side=tk.LEFT, padx=10, ipady=4)
        
        self.txt_res = tk.Text(parent, font=('Segoe UI', 12), bg='#0F172A', fg='#FFF', height=10, padx=20, pady=20, relief=tk.FLAT)
        self.txt_res.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

    def do_search(self):
        p = self.ent_q.get().strip()
        if not re.fullmatch(r'^\d{14}$', p): return messagebox.showerror('Xato', 'JSHSHIR 14 ta raqam bo‘lishi shart!')
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM records WHERE pinfl = ?', (p,))
        r = c.fetchone()
        conn.close()
        
        self.txt_res.delete('1.0', tk.END)
        self.last_search = None
        if r:
            self.last_search = r
            status = "QAT'IYAN TAVSIYA ETILMAYDI (YUQORI XAVF)" if r[5] == 'YUQORI' else "OGOHLANTIRISH (SUDLANGAN)"
            self.txt_res.insert(tk.END, f"XULOSA: {status}\n\nJSHSHIR: {r[0]}\nF.I.Sh: {r[1]}\nTug'ilgan sana: {r[2]}\nModdalar: {r[3]}\nIzoh: {r[4]}\nKiritgan xodim: {r[6]}\nKiritilgan vaqt: {r[7]}")
        else:
            self.txt_res.insert(tk.END, f"XULOSA: TOZA\n\nJSHSHIR: {p} bazada topilmadi. Qabul qilish mumkin.")
        log_audit(self.current_user, 'QIDIRUV', f'JSHSHIR: {p}')

    def export_report(self):
        if not hasattr(self, 'last_search') or not self.last_search: return messagebox.showwarning('Xato', 'Avval tekshiruv o‘tkazing!')
        path = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text Files', '*.txt')], initialfile=f"Xulosa_{self.last_search[0]}.txt")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.txt_res.get('1.0', tk.END))
            messagebox.showinfo('Saqlandi', 'Xulosa muvaffaqiyatli saqlandi!')

    # ================= 3. UMUMIY BAZA VA TAHRIRLASH (CRUD) =================
    def build_database_tab(self, parent):
        tools = tk.Frame(parent, bg='#1E293B', pady=10)
        tools.pack(fill=tk.X, padx=20)
        
        tk.Button(tools, text='🔄 Yangilash', bg='#475569', fg='white', command=self.load_grid).pack(side=tk.LEFT, padx=5)
        tk.Button(tools, text='➕ Yangi Qoshish', bg='#10B981', fg='white', command=self.open_add_window).pack(side=tk.LEFT, padx=5)
        tk.Button(tools, text='✏️ Tahrirlash', bg='#F59E0B', fg='white', command=self.open_edit_window).pack(side=tk.LEFT, padx=5)
        if self.current_role == 'ADMIN':
            tk.Button(tools, text='❌ O‘chirish', bg='#EF4444', fg='white', command=self.delete_record).pack(side=tk.LEFT, padx=5)
        tk.Button(tools, text='📥 Excel/CSV Yuklash', bg='#2563EB', fg='white', command=self.import_csv).pack(side=tk.RIGHT, padx=5)

        self.tree_db = ttk.Treeview(parent, columns=('p','f','d','a','r','by'), show='headings')
        self.tree_db.heading('p', text='JSHSHIR'); self.tree_db.column('p', width=120)
        self.tree_db.heading('f', text='F.I.Sh'); self.tree_db.column('f', width=250)
        self.tree_db.heading('d', text='Sana'); self.tree_db.column('d', width=100)
        self.tree_db.heading('a', text='Moddalar'); self.tree_db.column('a', width=150)
        self.tree_db.heading('r', text='Xavf'); self.tree_db.column('r', width=100)
        self.tree_db.heading('by', text='Kiritdi'); self.tree_db.column('by', width=100)
        self.tree_db.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.load_grid()

    def load_grid(self):
        for r in self.tree_db.get_children(): self.tree_db.delete(r)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT pinfl, fullname, birth_date, articles, risk_level, added_by FROM records ORDER BY created_at DESC')
        for row in c.fetchall(): self.tree_db.insert('', tk.END, values=row)
        conn.close()

    def open_add_window(self):
        self.record_window('Yangi Kiritish')
        
    def open_edit_window(self):
        sel = self.tree_db.selection()
        if not sel: return messagebox.showwarning('Tanlang', 'Tahrirlash uchun qatorni tanlang!')
        pinfl = self.tree_db.item(sel[0], 'values')[0]
        self.record_window('Tahrirlash', pinfl)

    def record_window(self, title, pinfl=None):
        w = tk.Toplevel(self)
        w.title(title)
        w.geometry('500x550')
        w.configure(bg='#1E293B')
        w.transient(self)
        w.grab_set()

        fields = [('JSHSHIR (14 ta raqam):', 'p'), ('F.I.Sh:', 'f'), ('Sana (KK.OO.YYYY):', 'd'), ('Moddalar:', 'a'), ('Izoh:', 'det')]
        ents = {}
        for i, (lbl, k) in enumerate(fields):
            tk.Label(w, text=lbl, fg='white', bg='#1E293B', font=('Segoe UI', 10, 'bold')).pack(pady=(15,2), anchor=tk.W, padx=30)
            ent = tk.Entry(w, font=('Segoe UI', 11), bg='#0F172A', fg='white', insertbackground='white')
            ent.pack(fill=tk.X, padx=30, ipady=4)
            ents[k] = ent

        if pinfl:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT pinfl, fullname, birth_date, articles, details FROM records WHERE pinfl=?', (pinfl,))
            r = c.fetchone()
            conn.close()
            ents['p'].insert(0, r[0]); ents['p'].config(state='disabled')
            ents['f'].insert(0, r[1]); ents['d'].insert(0, r[2]); ents['a'].insert(0, r[3]); ents['det'].insert(0, r[4])

        def save():
            v = {k: e.get().strip() for k, e in ents.items()}
            if not all([v['p'], v['f'], v['d'], v['a']]): return messagebox.showerror('Xato', 'Barcha kataklarni to‘ldiring!', parent=w)
            if not re.fullmatch(r'^\d{14}$', v['p']): return messagebox.showerror('Xato', 'JSHSHIR xato!', parent=w)
            try: datetime.strptime(v['d'], '%d.%m.%Y')
            except: return messagebox.showerror('Xato', 'Sana xato!', parent=w)
            
            risk = 'YUQORI' if any(a in v['a'] for a in CORRUPTION_ARTICLES) else 'ODDIY'
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            if pinfl:
                c.execute("UPDATE records SET fullname=?, birth_date=?, articles=?, details=?, risk_level=? WHERE pinfl=?", (v['f'], v['d'], v['a'], v['det'], risk, pinfl))
                log_audit(self.current_user, 'TAHRIR', f"JSHSHIR yangilandi: {pinfl}")
            else:
                try:
                    c.execute("INSERT INTO records (pinfl, fullname, birth_date, articles, details, risk_level, added_by) VALUES (?,?,?,?,?,?,?)", (v['p'], v['f'], v['d'], v['a'], v['det'], risk, self.current_user))
                    log_audit(self.current_user, 'QOSHISH', f"Yangi yozuv: {v['p']}")
                except: return messagebox.showerror('Xato', 'Bu JSHSHIR mavjud!', parent=w)
            conn.commit(); conn.close()
            self.load_grid(); w.destroy(); messagebox.showinfo('Tayyor', 'Saqlandi!')

        tk.Button(w, text='SAQLASH', bg='#10B981', fg='white', font=('Segoe UI', 11, 'bold'), command=save).pack(pady=25, fill=tk.X, padx=30, ipady=5)

    def delete_record(self):
        sel = self.tree_db.selection()
        if not sel: return
        pinfl = self.tree_db.item(sel[0], 'values')[0]
        if messagebox.askyesno('Tasdiq', 'O‘chirilsinmi?'):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('DELETE FROM records WHERE pinfl=?', (pinfl,))
            conn.commit(); conn.close()
            log_audit(self.current_user, 'OCHIRISH', f'O‘chirildi: {pinfl}')
            self.load_grid()

    def import_csv(self):
        p = filedialog.askopenfilename(filetypes=[('CSV Fayl', '*.csv')])
        if not p: return
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        s = 0
        with open(p, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=';')
            next(reader, None)
            for r in reader:
                if len(r) >= 5 and re.fullmatch(r'^\d{14}$', r[0].strip()):
                    risk = 'YUQORI' if any(a in r[3] for a in CORRUPTION_ARTICLES) else 'ODDIY'
                    c.execute("INSERT OR REPLACE INTO records (pinfl, fullname, birth_date, articles, details, risk_level, added_by) VALUES (?,?,?,?,?,?,?)",
                              (r[0].strip(), r[1].strip(), r[2].strip(), r[3].strip(), r[4].strip(), risk, self.current_user))
                    s += 1
        conn.commit(); conn.close()
        log_audit(self.current_user, 'IMPORT', f'{s} ta yozuv yuklandi')
        self.load_grid()
        messagebox.showinfo('Tayyor', f'{s} ta ma‘lumot yuklandi!')

    # ================= 4. ADMIN VA AUDIT PANELI =================
    def build_admin_tab(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tab_users = tk.Frame(nb, bg='#0F172A')
        tab_pwd = tk.Frame(nb, bg='#0F172A')
        tab_audit = tk.Frame(nb, bg='#0F172A')
        
        nb.add(tab_users, text=' Xodimlarni Boshqarish ')
        nb.add(tab_pwd, text=' Mening Parolim ')
        nb.add(tab_audit, text=' Audit Jurnali (Loglar) ')

        # --- Mening Parolim ---
        f_pwd = tk.Frame(tab_pwd, bg='#0F172A', padx=50, pady=40)
        f_pwd.pack(anchor=tk.W)
        tk.Label(f_pwd, text='O‘z parolingizni yangilash', font=('Segoe UI', 14, 'bold'), fg='#FFF', bg='#0F172A').pack(anchor=tk.W, pady=(0,20))
        tk.Label(f_pwd, text='Eski parol:', fg='#FFF', bg='#0F172A').pack(anchor=tk.W)
        e_old = tk.Entry(f_pwd, show='*', width=30); e_old.pack(pady=5, ipady=4)
        tk.Label(f_pwd, text='Yangi parol:', fg='#FFF', bg='#0F172A').pack(anchor=tk.W)
        e_new = tk.Entry(f_pwd, show='*', width=30); e_new.pack(pady=5, ipady=4)
        
        def change_pwd():
            old, new = e_old.get(), e_new.get()
            if not old or not new: return messagebox.showwarning('Xato', 'To‘ldiring!')
            conn = sqlite3.connect(DB_PATH); c = conn.cursor()
            c.execute('SELECT password_hash FROM users WHERE username=?', (self.current_user,))
            if c.fetchone()[0] == hash_password(old):
                c.execute('UPDATE users SET password_hash=? WHERE username=?', (hash_password(new), self.current_user))
                conn.commit()
                messagebox.showinfo('Tayyor', 'Parol muvaffaqiyatli o‘zgardi!')
                e_old.delete(0, tk.END); e_new.delete(0, tk.END)
                log_audit(self.current_user, 'PAROL_YANGILANDI', 'Admin o‘z parolini o‘zgartirdi')
            else:
                messagebox.showerror('Xato', 'Eski parol noto‘g‘ri!')
            conn.close()
        tk.Button(f_pwd, text='Yangilash', bg='#2563EB', fg='white', command=change_pwd).pack(pady=15, ipady=4, fill=tk.X)

        # --- Audit Logs ---
        self.tree_audit = ttk.Treeview(tab_audit, columns=('id','user','act','det','time'), show='headings')
        self.tree_audit.heading('user', text='Xodim'); self.tree_audit.heading('act', text='Harakat'); self.tree_audit.heading('det', text='Tafsilot'); self.tree_audit.heading('time', text='Vaqti')
        self.tree_audit.column('id', width=0, stretch=tk.NO); self.tree_audit.column('user', width=100); self.tree_audit.column('act', width=120); self.tree_audit.column('det', width=300); self.tree_audit.column('time', width=150)
        self.tree_audit.pack(fill=tk.BOTH, expand=True, pady=10)
        tk.Button(tab_audit, text='🔄 Yangilash', command=self.load_audit).pack(pady=10)
        self.load_audit()

    def load_audit(self):
        for r in self.tree_audit.get_children(): self.tree_audit.delete(r)
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 200')
        for row in c.fetchall(): self.tree_audit.insert('', tk.END, values=row)
        conn.close()

if __name__ == '__main__':
    app = ProfessionalComplianceApp()
    app.mainloop()
