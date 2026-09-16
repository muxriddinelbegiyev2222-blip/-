import csv
from datetime import datetime
import hashlib
import os
import re
import sqlite3
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --- 1. PORTABLE BAZA VA PAPKA JOYLASHUVI ---
if getattr(sys, 'frozen', False):
  APP_DIR = os.path.dirname(sys.executable)
else:
  APP_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(APP_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'compliance_master.db')

# Kadastr tizimi uchun xavfli bo'lgan korrupsiyaviy moddalar
CORRUPTION_ARTICLES = [
    '167',
    '168',
    '205',
    '206',
    '207',
    '208',
    '209',
    '210',
    '211',
    '212',
    '228',
]


# --- 2. XAVFSIZLIK VA SHIFRLASH ---
def hash_password(password, salt='KadastrCompliance2026'):
  return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()


def init_db():
  conn = sqlite3.connect(DB_PATH)
  c = conn.cursor()

  # Foydalanuvchilar jadvali
  c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            fullname TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  # Sudlanganlik va nozik ma'lumotlar bazasi
  c.execute("""
        CREATE TABLE IF NOT EXISTS records (
            pinfl TEXT PRIMARY KEY,
            fullname TEXT NOT NULL,
            birth_date TEXT NOT NULL,
            articles TEXT NOT NULL,
            details TEXT NOT NULL,
            risk_level TEXT,
            added_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  # Harakatlar jurnali (Audit Log)
  c.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

  # Standart boshlang'ich admin (agar mavjud bo'lmasa)
  c.execute("SELECT * FROM users WHERE username = 'admin'")
  if not c.fetchone():
    c.execute(
        """
            INSERT INTO users (username, password_hash, fullname, role)
            VALUES (?, ?, ?, ?)
        """,
        (
            'admin',
            hash_password('Admin@2026'),
            'Tizim Administratori',
            'ADMIN',
        ),
    )

  conn.commit()
  conn.close()


init_db()


def log_audit(username, action, details):
  try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'INSERT INTO audit_logs (username, action, details) VALUES (?, ?, ?)',
        (username, action, details),
    )
    conn.commit()
    conn.close()
  except Exception:
    pass


# --- 3. ASOSIY GRAFIK ILОVA ---
class ProfessionalComplianceApp(tk.Tk):

  def __init__(self):
    super().__init__()
    self.title('KADASTR AGENTLIGI - ICHKI NAZORAT VA KOMPLAYENS TIZIMI')
    self.geometry('1050x700')
    self.minsize(980, 650)
    self.configure(bg='#0F172A')

    self.current_user = None
    self.current_role = None

    self.setup_styles()
    self.show_login_screen()

  def setup_styles(self):
    self.style = ttk.Style()
    self.style.theme_use('clam')
    self.style.configure(
        'TNotebook', background='#1E293B', borderwidth=0, tabmargins=[5, 5, 5, 0]
    )
    self.style.configure(
        'TNotebook.Tab',
        background='#334155',
        foreground='#E2E8F0',
        font=('Segoe UI', 10, 'bold'),
        padding=[15, 8],
    )
    self.style.map(
        'TNotebook.Tab',
        background=[('selected', '#2563EB')],
        foreground=[('selected', '#FFFFFF')],
    )

  def clear_window(self):
    for widget in self.winfo_children():
      widget.destroy()

  # ==================== A) LOGIN OYNASI ====================
  def show_login_screen(self):
    self.clear_window()
    self.configure(bg='#0F172A')

    card = tk.Frame(
        self, bg='#1E293B', padx=40, pady=35, relief=tk.FLAT, bd=0
    )
    card.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    tk.Label(
        card,
        text='XAVFSIZLIK VA ICHKI NAZORAT',
        font=('Segoe UI', 16, 'bold'),
        fg='#38BDF8',
        bg='#1E293B',
    ).pack(pady=(0, 5))
    tk.Label(
        card,
        text='Kadastr sohasida nomzodlarni tekshirish bazasi',
        font=('Segoe UI', 9),
        fg='#94A3B8',
        bg='#1E293B',
    ).pack(pady=(0, 25))

    tk.Label(
        card,
        text='Foydalanuvchi logini:',
        font=('Segoe UI', 10, 'bold'),
        fg='#F1F5F9',
        bg='#1E293B',
    ).pack(anchor=tk.W)
    self.ent_login_user = tk.Entry(
        card,
        font=('Segoe UI', 11),
        width=30,
        bg='#0F172A',
        fg='#FFFFFF',
        insertbackground='white',
        relief=tk.FLAT,
    )
    self.ent_login_user.pack(pady=(5, 15), ipady=5)
    self.ent_login_user.focus()

    tk.Label(
        card,
        text='Maxfiy parol:',
        font=('Segoe UI', 10, 'bold'),
        fg='#F1F5F9',
        bg='#1E293B',
    ).pack(anchor=tk.W)
    self.ent_login_pwd = tk.Entry(
        card,
        font=('Segoe UI', 11),
        width=30,
        show='•',
        bg='#0F172A',
        fg='#FFFFFF',
        insertbackground='white',
        relief=tk.FLAT,
    )
    self.ent_login_pwd.pack(pady=(5, 20), ipady=5)

    btn_login = tk.Button(
        card,
        text='TIZIMGA KIRISH',
        font=('Segoe UI', 11, 'bold'),
        bg='#2563EB',
        fg='white',
        activebackground='#1D4ED8',
        activeforeground='white',
        relief=tk.FLAT,
        cursor='hand2',
        command=self.process_login,
    )
    btn_login.pack(fill=tk.X, ipady=6)

    tk.Label(
        card,
        text='*Standart profil: admin | Admin@2026',
        font=('Segoe UI', 8, 'italic'),
        fg='#64748B',
        bg='#1E293B',
    ).pack(pady=(15, 0))

  def process_login(self):
    u = self.ent_login_user.get().strip()
    p = self.ent_login_pwd.get().strip()

    if not u or not p:
      messagebox.showwarning(
          'Ogohlantirish', 'Login va parolni to‘liq kiriting!'
      )
      return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'SELECT username, fullname, role, password_hash FROM users WHERE'
        ' username = ?',
        (u,),
    )
    row = c.fetchone()
    conn.close()

    if row and row[3] == hash_password(p):
      self.current_user = row[0]
      self.current_role = row[2]
      log_audit(self.current_user, 'KIRISH', 'Tizimga muvaffaqiyatli kirdi')
      self.show_main_workspace()
    else:
      messagebox.showerror('Rad etildi', 'Login yoki maxfiy parol noto‘g‘ri!')

  # ==================== B) ASOSIY ISH MAYDONI ====================
  def show_main_workspace(self):
    self.clear_window()
    self.configure(bg='#0F172A')

    # Tepki sarlavha paneli
    header = tk.Frame(self, bg='#1E293B', height=50, padx=20)
    header.pack(fill=tk.X)

    tk.Label(
        header,
        text='KADASTR TIZIMI | KOMPLAYENS-NAZORAT',
        font=('Segoe UI', 12, 'bold'),
        fg='#38BDF8',
        bg='#1E293B',
    ).pack(side=tk.LEFT, pady=12)

    user_info = f'Foydalanuvchi: {self.current_user} ({self.current_role})'
    tk.Label(
        header,
        text=user_info,
        font=('Segoe UI', 10),
        fg='#94A3B8',
        bg='#1E293B',
    ).pack(side=tk.LEFT, padx=30)

    tk.Button(
        header,
        text='Chiqish',
        font=('Segoe UI', 9, 'bold'),
        bg='#EF4444',
        fg='white',
        relief=tk.FLAT,
        padx=10,
        command=self.show_login_screen,
    ).pack(side=tk.RIGHT, pady=10)

    # Varoqlar (Tabs)
    notebook = ttk.Notebook(self)
    notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    tab_search = tk.Frame(notebook, bg='#1E293B')
    tab_insert = tk.Frame(notebook, bg='#1E293B')
    tab_batch = tk.Frame(notebook, bg='#1E293B')

    notebook.add(tab_search, text='  Nomzodni tekshirish (Qidiruv)  ')
    notebook.add(tab_insert, text='  Qat‘iy norma bilan kiritish  ')
    notebook.add(tab_batch, text='  Excel/CSV Shabloni va Import  ')

    if self.current_role == 'ADMIN':
      tab_admin = tk.Frame(notebook, bg='#1E293B')
      notebook.add(tab_admin, text='  Admin Paneli & Xodimlar  ')
      self.build_admin_tab(tab_admin)

    self.build_search_tab(tab_search)
    self.build_insert_tab(tab_insert)
    self.build_batch_tab(tab_batch)

  # ==================== 1-TAB: TEKSHIRUV PANELI ====================
  def build_search_tab(self, parent):
    panel = tk.Frame(parent, bg='#334155', padx=20, pady=15)
    panel.pack(fill=tk.X, padx=15, pady=15)

    tk.Label(
        panel,
        text='JSHSHIR (PINFL) kiriting:',
        font=('Segoe UI', 11, 'bold'),
        fg='#FFFFFF',
        bg='#334155',
    ).pack(side=tk.LEFT, padx=(0, 10))

    self.ent_search_pinfl = tk.Entry(
        panel,
        font=('Segoe UI', 13, 'bold'),
        width=20,
        bg='#0F172A',
        fg='#38BDF8',
        insertbackground='white',
        relief=tk.FLAT,
    )
    self.ent_search_pinfl.pack(side=tk.LEFT, ipady=4)
    self.ent_search_pinfl.bind('<Return>', lambda e: self.execute_search())

    tk.Button(
        panel,
        text='TEKSHIRISH (ENTER)',
        font=('Segoe UI', 10, 'bold'),
        bg='#0284C7',
        fg='white',
        relief=tk.FLAT,
        padx=15,
        command=self.execute_search,
    ).pack(side=tk.LEFT, padx=15)

    # Natija ko'rsatish
    self.txt_search_result = tk.Text(
        parent,
        font=('Segoe UI', 11),
        bg='#0F172A',
        fg='#F1F5F9',
        wrap=tk.WORD,
        relief=tk.FLAT,
        padx=20,
        pady=15,
    )
    self.txt_search_result.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

    self.txt_search_result.tag_config(
        'danger',
        foreground='#EF4444',
        font=('Segoe UI', 13, 'bold'),
        spacing1=5,
        spacing3=5,
    )
    self.txt_search_result.tag_config(
        'clean',
        foreground='#22C55E',
        font=('Segoe UI', 13, 'bold'),
        spacing1=5,
        spacing3=5,
    )
    self.txt_search_result.tag_config(
        'label', foreground='#94A3B8', font=('Segoe UI', 10, 'bold')
    )
    self.txt_search_result.tag_config(
        'val', foreground='#FFFFFF', font=('Segoe UI', 11)
    )

  def execute_search(self):
    p = self.ent_search_pinfl.get().strip()

    if not re.fullmatch(r'^\d{14}$', p):
      messagebox.showerror(
          'Norma talabi buzildi',
          'JSHSHIR aynan 14 ta raqamdan iborat bo‘lishi shart!',
      )
      return

    log_audit(
        self.current_user, 'TEKSHIRUV', f'JSHSHIR qidirildi: {p}'
    )

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'SELECT fullname, birth_date, articles, details, risk_level, added_by,'
        ' created_at FROM records WHERE pinfl = ?',
        (p,),
    )
    row = c.fetchone()
    conn.close()

    self.txt_search_result.delete('1.0', tk.END)

    if row:
      is_high_risk = any(
          art in str(row[2]) for art in CORRUPTION_ARTICLES
      )

      if is_high_risk:
        self.txt_search_result.insert(
            tk.END,
            ' DIQQAT! NOMZOD SUDLANGANLIK BAZASIDA MAVJUD — YUQORI XAVF!\n',
            'danger',
        )
        self.txt_search_result.insert(
            tk.END,
            'Kadastr tizimi uchun xavfli bo‘lgan korrupsiyaviy moddalar'
            ' aniqlandi. Ishga qabul qilish qat‘iyan tavsiya etilmaydi!\n\n',
            'danger',
        )
      else:
        self.txt_search_result.insert(
            tk.END,
            ' OGOHLANTIRISH: NOMZOD SUDLANGANLIK BAZASIDA MAVJUD!\n\n',
            'danger',
        )

      fields = [
          ('JSHSHIR (PINFL):', p),
          ('Fuqaroning F.I.Sh.:', row[0]),
          ('Tug‘ilgan sanasi:', row[1]),
          ('Sudlangan moddalari:', row[2]),
          ('Qo‘shimcha izoh / Sud qarori:', row[3]),
          ('Tizimga kiritgan xodim:', row[5]),
          ('Bazaga kiritilgan vaqti:', row[6]),
      ]

      for lbl, v in fields:
        self.txt_search_result.insert(tk.END, f'{lbl:<30} ', 'label')
        self.txt_search_result.insert(tk.END, f'{v}\n', 'val')
    else:
      self.txt_search_result.insert(
          tk.END,
          ' MA‘LUMOT TOPILMADI (NOMZOD TOZA)\n\n',
          'clean',
      )
      self.txt_search_result.insert(
          tk.END,
          f'JSHSHIR: {p}\nUshbu fuqaro ichki nazorat va sudlanganlik'
          ' bazasida mavjud emas.',
          'val',
      )

  # ==================== 2-TAB: MA'LUMOT KIRITISH (SMART MASK) ====================
  def build_insert_tab(self, parent):
    frame = tk.Frame(parent, bg='#1E293B', padx=30, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        frame,
        text='YANGI FUQARONI BAZAGA QAT‘IY STANDART BILAN KIRITISH',
        font=('Segoe UI', 12, 'bold'),
        fg='#38BDF8',
        bg='#1E293B',
    ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))

    # 1. JSHSHIR (Faqat raqam, max 14)
    tk.Label(
        frame,
        text='JSHSHIR (PINFL - Aniq 14 ta raqam)*:',
        font=('Segoe UI', 10, 'bold'),
        fg='#F1F5F9',
        bg='#1E293B',
    ).grid(row=1, column=0, sticky=tk.W, pady=6)
    self.ent_in_pinfl = tk.Entry(
        frame,
        font=('Segoe UI', 11),
        width=40,
        bg='#0F172A',
        fg='#FFFFFF',
        insertbackground='white',
        relief=tk.FLAT,
    )
    self.ent_in_pinfl.grid(row=1, column=1, sticky=tk.W, pady=6, ipady=3)
    self.ent_in_pinfl.bind('<KeyRelease>', self.mask_pinfl)

    # 2. FISH
    tk.Label(
        frame,
        text='F.I.Sh. (To‘liq yozilishi shart)*:',
        font=('Segoe UI', 10, 'bold'),
        fg='#F1F5F9',
        bg='#1E293B',
    ).grid(row=2, column=0, sticky=tk.W, pady=6)
    self.ent_in_fullname = tk.Entry(
        frame,
        font=('Segoe UI', 11),
        width=40,
        bg='#0F172A',
        fg='#FFFFFF',
        insertbackground='white',
        relief=tk.FLAT,
    )
    self.ent_in_fullname.grid(row=2, column=1, sticky=tk.W, pady=6, ipady=3)

    # 3. Sana (Avtomatik nuqtali Smart Mask)
    tk.Label(
        frame,
        text='Tug‘ilgan sana (Avto format: KK.OO.YYYY)*:',
        font=('Segoe UI', 10, 'bold'),
        fg='#F1F5F9',
        bg='#1E293B',
    ).grid(row=3, column=0, sticky=tk.W, pady=6)
    self.ent_in_date = tk.Entry(
        frame,
        font=('Segoe UI', 11),
        width=40,
        bg='#0F172A',
        fg='#FFFFFF',
        insertbackground='white',
        relief=tk.FLAT,
    )
    self.ent_in_date.grid(row=3, column=1, sticky=tk.W, pady=6, ipady=3)
    self.ent_in_date.bind('<KeyRelease>', self.mask_date)

    # 4. Moddalar
    tk.Label(
        frame,
        text='Sudlangan JK moddalari (Masalan: 168, 205, 210)*:',
        font=('Segoe UI', 10, 'bold'),
        fg='#F1F5F9',
        bg='#1E293B',
    ).grid(row=4, column=0, sticky=tk.W, pady=6)
    self.ent_in_articles = tk.Entry(
        frame,
        font=('Segoe UI', 11),
        width=40,
        bg='#0F172A',
        fg='#FFFFFF',
        insertbackground='white',
        relief=tk.FLAT,
    )
    self.ent_in_articles.grid(row=4, column=1, sticky=tk.W, pady=6, ipady=3)

    # 5. Izoh
    tk.Label(
        frame,
        text='Tafsilotlar va sud qarori izohi*:',
        font=('Segoe UI', 10, 'bold'),
        fg='#F1F5F9',
        bg='#1E293B',
    ).grid(row=5, column=0, sticky=tk.NW, pady=6)
    self.txt_in_details = tk.Text(
        frame,
        font=('Segoe UI', 10),
        width=40,
        height=4,
        bg='#0F172A',
        fg='#FFFFFF',
        insertbackground='white',
        relief=tk.FLAT,
    )
    self.txt_in_details.grid(row=5, column=1, sticky=tk.W, pady=6)

    btn_save = tk.Button(
        frame,
        text='BAZAGA XAVFSIZ SAQLASH',
        font=('Segoe UI', 10, 'bold'),
        bg='#059669',
        fg='white',
        relief=tk.FLAT,
        padx=20,
        command=self.save_single_record,
    )
    btn_save.grid(row=6, column=1, sticky=tk.E, pady=15, ipady=5)

  def mask_pinfl(self, event):
    # Faqat raqam qoldirish va 14 ta bilan cheklash
    val = re.sub(r'\D', '', self.ent_in_pinfl.get())[:14]
    self.ent_in_pinfl.delete(0, tk.END)
    self.ent_in_pinfl.insert(0, val)

  def mask_date(self, event):
    if event.keysym == 'BackSpace':
      return
    val = re.sub(r'\D', '', self.ent_in_date.get())[:8]
    formatted = ''
    if len(val) > 0:
      formatted = val[:2]
    if len(val) >= 2:
      formatted += '.' + val[2:4]
    if len(val) >= 4:
      formatted += '.' + val[4:8]
    self.ent_in_date.delete(0, tk.END)
    self.ent_in_date.insert(0, formatted)

  def save_single_record(self):
    p = self.ent_in_pinfl.get().strip()
    f = self.ent_in_fullname.get().strip()
    d = self.ent_in_date.get().strip()
    a = self.ent_in_articles.get().strip()
    det = self.txt_in_details.get('1.0', tk.END).strip()

    # Majburiy maydonlar va qat'iy norma tekshiruvi
    if not (p and f and d and a and det):
      messagebox.showerror(
          'Majburiy talab', 'Barcha kataklar to‘ldirilishi majburiy!'
      )
      return

    if not re.fullmatch(r'^\d{14}$', p):
      messagebox.showerror(
          'Xato', 'JSHSHIR aynan 14 ta raqam bo‘lishi shart!'
      )
      return

    try:
      datetime.strptime(d, '%d.%m.%Y')
    except ValueError:
      messagebox.showerror(
          'Sana xatosi', 'Tug‘ilgan sana KK.OO.YYYY normasida to‘liq bo‘lsin!'
      )
      return

    risk = (
        'YUQORI'
        if any(art in a for art in CORRUPTION_ARTICLES)
        else 'ODDIY'
    )

    try:
      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()
      c.execute(
          """
                INSERT INTO records (pinfl, fullname, birth_date, articles, details, risk_level, added_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
          (p, f, d, a, det, risk, self.current_user),
      )
      conn.commit()
      conn.close()

      log_audit(
          self.current_user, 'QO‘SHISH', f'Yangi fuqaro kiritildi: {p} - {f}'
      )
      messagebox.showinfo('Muvaffaqiyatli', 'Ma‘lumot bazaga kiritildi!')

      self.ent_in_pinfl.delete(0, tk.END)
      self.ent_in_fullname.delete(0, tk.END)
      self.ent_in_date.delete(0, tk.END)
      self.ent_in_articles.delete(0, tk.END)
      self.txt_in_details.delete('1.0', tk.END)
    except sqlite3.IntegrityError:
      messagebox.showerror(
          'Mavjud', f'Ushbu JSHSHIR ({p}) bazada allaqachon mavjud!'
      )

  # ==================== 3-TAB: SHABLON VA EXCEL/CSV IMPORT ====================
  def build_batch_tab(self, parent):
    box = tk.Frame(parent, bg='#1E293B', padx=30, pady=25)
    box.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        box,
        text='OMMAVIY YUKLASH VA EXCEL SHABLON TIZIMI',
        font=('Segoe UI', 12, 'bold'),
        fg='#38BDF8',
        bg='#1E293B',
    ).pack(anchor=tk.W, pady=(0, 10))

    tk.Label(
        box,
        text=(
            'Tizim adashmasdan o‘qishi uchun maxsus shablondan foydalaning.'
            ' Shablonni yuklab olib, ma‘lumotlarni\nExcelda to‘ldirasiz va'
            ' bitta tugma bilan 100 lab yozuvlarni yuklaysiz.'
        ),
        font=('Segoe UI', 10),
        fg='#94A3B8',
        bg='#1E293B',
        justify=tk.LEFT,
    ).pack(anchor=tk.W, pady=(0, 20))

    btn_f = tk.Frame(box, bg='#1E293B')
    btn_f.pack(anchor=tk.W, pady=10)

    tk.Button(
        btn_f,
        text='1. Tayyor Shablonni Yuklab Olish',
        font=('Segoe UI', 10, 'bold'),
        bg='#475569',
        fg='white',
        relief=tk.FLAT,
        padx=15,
        command=self.download_template,
    ).pack(side=tk.LEFT, padx=(0, 10), ipady=5)

    tk.Button(
        btn_f,
        text='2. To‘ldirilgan Shablonni Bazaga Yuklash',
        font=('Segoe UI', 10, 'bold'),
        bg='#2563EB',
        fg='white',
        relief=tk.FLAT,
        padx=15,
        command=self.import_template_file,
    ).pack(side=tk.LEFT, padx=10, ipady=5)

    tk.Button(
        btn_f,
        text='3. Bazani Excel (CSV) Qilib Eksport Qilish',
        font=('Segoe UI', 10, 'bold'),
        bg='#059669',
        fg='white',
        relief=tk.FLAT,
        padx=15,
        command=self.export_full_database,
    ).pack(side=tk.LEFT, padx=10, ipady=5)

    self.lbl_batch_status = tk.Label(
        box, text='', font=('Segoe UI', 10, 'bold'), bg='#1E293B'
    )
    self.lbl_batch_status.pack(anchor=tk.W, pady=20)

  def download_template(self):
    path = filedialog.asksaveasfilename(
        defaultextension='.csv',
        filetypes=[('CSV Fayl (Excel ochadi)', '*.csv')],
        initialfile='Shablon_Sudlanganlik_Yuklash.csv',
    )
    if not path:
      return
    try:
      with open(path, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(
            ['JSHSHIR', 'FISH', 'TUGILGAN_SANA', 'MODDALAR', 'IZOH']
        )
        writer.writerow([
            '12345678901234',
            'Aliyev Vali Karimovich',
            '15.04.1988',
            '168, 205',
            'Firibgarlik va mansab vakolati',
        ])
      messagebox.showinfo(
          'Tayyor',
          'Shablon saqlandi! Excelda ochib qatorlarni to‘ldirishingiz'
          ' mumkin.',
      )
    except Exception as e:
      messagebox.showerror('Xatolik', f'Shablon saqlanmadi: {e}')

  def import_template_file(self):
    path = filedialog.askopenfilename(
        filetypes=[('CSV / Jadval fayllari', '*.csv *.txt')]
    )
    if not path:
      return

    try:
      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()
      success = 0
      skipped = 0

      with open(path, mode='r', encoding='utf-8-sig') as f:
        first_line = f.readline()
        delimiter = ';' if ';' in first_line else ','
        f.seek(0)
        reader = csv.reader(f, delimiter=delimiter)
        next(reader, None)  # Sarlavhani tashlab o'tish

        for r in reader:
          if len(r) >= 5:
            p, fish, dt, arts, det = (
                r[0].strip(),
                r[1].strip(),
                r[2].strip(),
                r[3].strip(),
                r[4].strip(),
            )
            # Qat'iy normadan o'tkazish
            if re.fullmatch(r'^\d{14}$', p) and fish:
              risk = (
                  'YUQORI'
                  if any(art in arts for art in CORRUPTION_ARTICLES)
                  else 'ODDIY'
              )
              c.execute(
                  """
                                INSERT OR REPLACE INTO records (pinfl, fullname, birth_date, articles, details, risk_level, added_by)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                  (p, fish, dt, arts, det, risk, self.current_user),
              )
              success += 1
            else:
              skipped += 1

      conn.commit()
      conn.close()

      log_audit(
          self.current_user,
          'IMPORT',
          f'Fayldan yuklandi: {success} ta, xato/o‘tkazildi: {skipped} ta',
      )
      self.lbl_batch_status.config(
          text=(
              f' Natija: {success} ta nomzod yuklandi. Standartga to‘g‘ri'
              f' kelmagan {skipped} ta qator tashlandi.'
          ),
          fg='#38BDF8',
      )
      messagebox.showinfo(
          'Tugallandi',
          f'Yuklandi: {success} ta yozuv!\nXato JSHSHIR tufayli tashlab'
          f' ketildi: {skipped} ta.',
      )
    except Exception as e:
      messagebox.showerror('Xatolik', f'Yuklashda xatolik: {e}')

  def export_full_database(self):
    path = filedialog.asksaveasfilename(
        defaultextension='.csv',
        filetypes=[('CSV Fayli (Excel)', '*.csv')],
        initialfile='Baza_Eksport_Toligicha.csv',
    )
    if not path:
      return

    try:
      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()
      c.execute(
          'SELECT pinfl, fullname, birth_date, articles, details, risk_level,'
          ' added_by, created_at FROM records'
      )
      rows = c.fetchall()
      conn.close()

      with open(path, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow([
            'JSHSHIR',
            'FISH',
            'TUGILGAN_SANA',
            'MODDALAR',
            'IZOH',
            'XAVF_DARAJASI',
            'KIRITDI',
            'VAQTI',
        ])
        writer.writerows(rows)

      log_audit(
          self.current_user, 'EKSPORT', 'Bazani to‘liq faylga yuklab oldi'
      )
      messagebox.showinfo(
          'Muvaffaqiyatli',
          'Baza to‘liq saqlandi! Excelda ochishingiz mumkin.',
      )
    except Exception as e:
      messagebox.showerror('Xatolik', f'Eksportda xatolik: {e}')

  # ==================== 4-TAB: ADMIN PANELI ====================
  def build_admin_tab(self, parent):
    frame = tk.Frame(parent, bg='#1E293B', padx=25, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        frame,
        text='XODIMLAR (FOYDALANUVCHILAR) BOSHQARUVI',
        font=('Segoe UI', 12, 'bold'),
        fg='#38BDF8',
        bg='#1E293B',
    ).pack(anchor=tk.W, pady=(0, 10))

    # Yangi xodim qo'shish formasi
    f_add = tk.LabelFrame(
        frame,
        text=' Yangi xodimga ruxsat berish ',
        font=('Segoe UI', 9, 'bold'),
        fg='#FFFFFF',
        bg='#1E293B',
        padx=15,
        pady=10,
    )
    f_add.pack(fill=tk.X, pady=(0, 15))

    tk.Label(
        f_add,
        text='Login:',
        fg='#F1F5F9',
        bg='#1E293B',
        font=('Segoe UI', 9, 'bold'),
    ).grid(row=0, column=0, padx=5, pady=5)
    self.ent_adm_user = tk.Entry(
        f_add,
        font=('Segoe UI', 10),
        width=15,
        bg='#0F172A',
        fg='#FFFFFF',
        insertbackground='white',
    )
    self.ent_adm_user.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(
        f_add,
        text='Parol:',
        fg='#F1F5F9',
        bg='#1E293B',
        font=('Segoe UI', 9, 'bold'),
    ).grid(row=0, column=2, padx=5, pady=5)
    self.ent_adm_pwd = tk.Entry(
        f_add,
        font=('Segoe UI', 10),
        width=15,
        bg='#0F172A',
        fg='#FFFFFF',
        insertbackground='white',
    )
    self.ent_adm_pwd.grid(row=0, column=3, padx=5, pady=5)

    tk.Label(
        f_add,
        text='F.I.Sh:',
        fg='#F1F5F9',
        bg='#1E293B',
        font=('Segoe UI', 9, 'bold'),
    ).grid(row=0, column=4, padx=5, pady=5)
    self.ent_adm_fn = tk.Entry(
        f_add,
        font=('Segoe UI', 10),
        width=20,
        bg='#0F172A',
        fg='#FFFFFF',
        insertbackground='white',
    )
    self.ent_adm_fn.grid(row=0, column=5, padx=5, pady=5)

    tk.Label(
        f_add,
        text='Roli:',
        fg='#F1F5F9',
        bg='#1E293B',
        font=('Segoe UI', 9, 'bold'),
    ).grid(row=0, column=6, padx=5, pady=5)
    self.cmb_adm_role = ttk.Combobox(
        f_add,
        values=['OPERATOR', 'ADMIN'],
        state='readonly',
        width=10,
        font=('Segoe UI', 9),
    )
    self.cmb_adm_role.set('OPERATOR')
    self.cmb_adm_role.grid(row=0, column=7, padx=5, pady=5)

    tk.Button(
        f_add,
        text='Qo‘shish',
        font=('Segoe UI', 9, 'bold'),
        bg='#0284C7',
        fg='white',
        relief=tk.FLAT,
        command=self.admin_add_user,
    ).grid(row=0, column=8, padx=10, pady=5)

    # Foydalanuvchilar jadvali
    self.tree_users = ttk.Treeview(
        frame,
        columns=('id', 'user', 'fn', 'role', 'date'),
        show='headings',
        height=8,
    )
    self.tree_users.heading('id', text='ID')
    self.tree_users.heading('user', text='Login')
    self.tree_users.heading('fn', text='Xodim F.I.Sh')
    self.tree_users.heading('role', text='Roli')
    self.tree_users.heading('date', text='Ochilgan sana')

    self.tree_users.column('id', width=40)
    self.tree_users.column('user', width=120)
    self.tree_users.column('fn', width=250)
    self.tree_users.column('role', width=100)
    self.tree_users.column('date', width=150)
    self.tree_users.pack(fill=tk.BOTH, expand=True, pady=10)

    btn_del = tk.Button(
        frame,
        text='Tanlangan xodimni o‘chirish',
        font=('Segoe UI', 9, 'bold'),
        bg='#EF4444',
        fg='white',
        relief=tk.FLAT,
        command=self.admin_delete_user,
    )
    btn_del.pack(anchor=tk.E)

    self.load_users_table()

  def load_users_table(self):
    for r in self.tree_users.get_children():
      self.tree_users.delete(r)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, username, fullname, role, created_at FROM users')
    for row in c.fetchall():
      self.tree_users.insert('', tk.END, values=row)
    conn.close()

  def admin_add_user(self):
    u = self.ent_adm_user.get().strip()
    p = self.ent_adm_pwd.get().strip()
    fn = self.ent_adm_fn.get().strip()
    role = self.cmb_adm_role.get()

    if not (u and p and fn):
      messagebox.showwarning(
          'Ogohlantirish', 'Yangi xodim ma‘lumotlarini to‘liq kiriting!'
      )
      return

    try:
      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()
      c.execute(
          """
                INSERT INTO users (username, password_hash, fullname, role)
                VALUES (?, ?, ?, ?)
            """,
          (u, hash_password(p), fn, role),
      )
      conn.commit()
      conn.close()
      log_audit(
          self.current_user,
          'XODIM_QO‘SHILDI',
          f'Yangi xodim: {u}, Roli: {role}',
      )
      messagebox.showinfo(
          'Muvaffaqiyatli', f'Yangi profil yaratildi: {u} | Parol: {p}'
      )

      self.ent_adm_user.delete(0, tk.END)
      self.ent_adm_pwd.delete(0, tk.END)
      self.ent_adm_fn.delete(0, tk.END)
      self.load_users_table()
    except sqlite3.IntegrityError:
      messagebox.showerror('Mavjud', 'Ushbu login band! Boshqa login tanlang.')

  def admin_delete_user(self):
    selected = self.tree_users.selection()
    if not selected:
      messagebox.showwarning('Tanlang', 'O‘chirmoqchi bo‘lgan xodimni tanlang!')
      return

    val = self.tree_users.item(selected[0], 'values')
    u_id, username = val[0], val[1]

    if username == 'admin':
      messagebox.showerror('Taqiqlangan', 'Bosh adminni o‘chirib bo‘lmaydi!')
      return

    if messagebox.askyesno(
        'Tasdiqlash',
        f'Haqiqatan ham {username} profilini o‘chirmoqchimisiz?',
    ):
      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()
      c.execute('DELETE FROM users WHERE id = ?', (u_id,))
      conn.commit()
      conn.close()
      log_audit(
          self.current_user,
          'XODIM_OCHIRILDI',
          f'O‘chirilgan profil: {username}',
      )
      self.load_users_table()


if __name__ == '__main__':
  app = ProfessionalComplianceApp()
  app.mainloop()
