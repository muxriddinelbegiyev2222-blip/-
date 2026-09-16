import os
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "baza.db")


def init_db():
  conn = sqlite3.connect(DB_PATH)
  c = conn.cursor()
  c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS records (
            pinfl TEXT PRIMARY KEY,
            fullname TEXT,
            birth_date TEXT,
            articles TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
  c.execute("SELECT * FROM users WHERE username = 'admin'")
  if not c.fetchone():
    c.execute(
        "INSERT INTO users (username, password) VALUES ('admin', '1234')"
    )
  conn.commit()
  conn.close()


init_db()


class SudlanganlikApp(tk.Tk):

  def __init__(self):
    super().__init__()
    self.title("Ichki nazorat - Nomzodlarni tekshirish")
    self.geometry("800x600")
    self.resizable(False, False)
    self.show_login()

  def clear(self):
    for w in self.winfo_children():
      w.destroy()

  def show_login(self):
    self.clear()
    f = tk.Frame(self, padx=30, pady=30)
    f.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    tk.Label(
        f, text="TIZIMGA KIRISH", font=("Arial", 16, "bold"), fg="#1A365D"
    ).pack(pady=15)
    tk.Label(f, text="Login:", font=("Arial", 11)).pack(anchor=tk.W)
    self.u_ent = tk.Entry(f, font=("Arial", 12), width=28)
    self.u_ent.pack(pady=5)
    self.u_ent.insert(0, "admin")

    tk.Label(f, text="Parol:", font=("Arial", 11)).pack(anchor=tk.W)
    self.p_ent = tk.Entry(f, font=("Arial", 12), width=28, show="*")
    self.p_ent.pack(pady=5)
    self.p_ent.insert(0, "1234")

    tk.Button(
        f,
        text="Kirish",
        font=("Arial", 11, "bold"),
        bg="#2B6CB0",
        fg="white",
        width=25,
        command=self.login,
    ).pack(pady=20)

  def login(self):
    u = self.u_ent.get().strip()
    p = self.p_ent.get().strip()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?", (u, p)
    )
    ok = c.fetchone()
    conn.close()
    if ok:
      self.show_main()
    else:
      messagebox.showerror("Xato", "Login yoki parol noto'g'ri!")

  def show_main(self):
    self.clear()
    nb = ttk.Notebook(self)
    nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    tab1 = tk.Frame(nb, bg="#F7FAFC")
    tab2 = tk.Frame(nb, bg="#F7FAFC")
    nb.add(tab1, text="  Nomzodni tekshirish (Qidiruv)  ")
    nb.add(tab2, text="  Yangi ma'lumot kiritish  ")

    # Qidiruv qismi
    top = tk.Frame(tab1, bg="#EDF2F7", pady=15, padx=15)
    top.pack(fill=tk.X, padx=10, pady=10)
    tk.Label(
        top,
        text="JSHSHIR (PINFL):",
        font=("Arial", 12, "bold"),
        bg="#EDF2F7",
    ).pack(side=tk.LEFT, padx=5)
    self.q_pinfl = tk.Entry(top, font=("Arial", 13), width=20)
    self.q_pinfl.pack(side=tk.LEFT, padx=5)
    tk.Button(
        top,
        text="Tekshirish",
        font=("Arial", 11, "bold"),
        bg="#3182CE",
        fg="white",
        command=self.search,
    ).pack(side=tk.LEFT, padx=10)

    self.res_box = tk.Text(
        tab1, font=("Arial", 11), wrap=tk.WORD, bg="white", relief=tk.SOLID, bd=1
    )
    self.res_box.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

    # Kiritish qismi
    form = tk.Frame(tab2, bg="#F7FAFC", padx=30, pady=20)
    form.pack(fill=tk.BOTH, expand=True)

    lbls = [
        ("JSHSHIR (PINFL - 14 xonali raqam):", "pinfl"),
        ("F.I.Sh. (Familiya Ism Sharif):", "fullname"),
        ("Tug'ilgan sana (kun.oy.yil):", "birth_date"),
        ("Sudlangan moddalari (masalan: 168, 210):", "articles"),
        ("Qo'shimcha izoh / Sud qarori tafsilotlari:", "details"),
    ]
    self.inputs = {}
    for idx, (txt, key) in enumerate(lbls):
      tk.Label(
          form, text=txt, font=("Arial", 10, "bold"), bg="#F7FAFC"
      ).grid(row=idx, column=0, sticky=tk.W, pady=8)
      ent = tk.Entry(form, font=("Arial", 11), width=45)
      ent.grid(row=idx, column=1, pady=8, padx=10)
      self.inputs[key] = ent

    tk.Button(
        form,
        text="Bazaga saqlash",
        font=("Arial", 11, "bold"),
        bg="#38A169",
        fg="white",
        padx=20,
        pady=6,
        command=self.save,
    ).grid(row=len(lbls), column=1, sticky=tk.E, pady=15)

  def search(self):
    p = self.q_pinfl.get().strip()
    if not p:
      messagebox.showwarning("Ogohlantirish", "JSHSHIR raqamini kiriting!")
      return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT fullname, birth_date, articles, details, created_at FROM"
        " records WHERE pinfl = ?",
        (p,),
    )
    r = c.fetchone()
    conn.close()

    self.res_box.delete("1.0", tk.END)
    if r:
      txt = (
          f" DIQQAT: NOMZOD SUDLANGANLIK BAZASIDA MAVJUD!\n\n"
          f" JSHSHIR: {p}\n"
          f" F.I.Sh.: {r[0]}\n"
          f" Tug'ilgan sana: {r[1]}\n"
          f" Sudlangan moddalari: {r[2]}\n"
          f" Izoh / Tafsilotlar: {r[3]}\n"
          f" Bazaga kiritilgan vaqt: {r[4]}\n"
          f"---------------------------------------------------\n"
          f" Kadastr sohasiga tavsiya etishda ushbu moddalarni inobatga oling!"
      )
      self.res_box.insert(tk.END, txt)
    else:
      self.res_box.insert(
          tk.END,
          f" MA'LUMOT TOPILMADI.\n\nJSHSHIR: {p}\nUshbu fuqaro bazada"
          " mavjud emas (toza).",
      )

  def save(self):
    vals = {k: v.get().strip() for k, v in self.inputs.items()}
    if not vals["pinfl"] or not vals["fullname"]:
      messagebox.showwarning(
          "Xato", "JSHSHIR va F.I.Sh. kiritilishi majburiy!"
      )
      return
    try:
      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()
      c.execute(
          """
                INSERT INTO records (pinfl, fullname, birth_date, articles, details)
                VALUES (?, ?, ?, ?, ?)
            """,
          (
              vals["pinfl"],
              vals["fullname"],
              vals["birth_date"],
              vals["articles"],
              vals["details"],
          ),
      )
      conn.commit()
      conn.close()
      messagebox.showinfo("Tayyor", "Ma'lumot bazaga kiritildi!")
      for v in self.inputs.values():
        v.delete(0, tk.END)
    except sqlite3.IntegrityError:
      messagebox.showerror(
          "Mavjud", "Ushbu JSHSHIR (PINFL) bazada allaqachon mavjud!"
      )


if __name__ == "__main__":
  app = SudlanganlikApp()
  app.mainloop()
