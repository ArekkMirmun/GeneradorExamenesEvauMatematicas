"""
Generador de Examenes Selectividad - Version PUBLICA
Genera examenes aleatorios SIN soluciones.
"""

import os
import sys
import ctypes
import random
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import date

import fitz  # PyMuPDF

# Import engine - handle both script and frozen modes
if getattr(sys, "frozen", False):
    _base = Path(sys.executable).parent
    sys.path.insert(0, str(_base))
else:
    _base = Path(__file__).parent

from motor_examenes import (
    load_exercises, get_available_temas, generate_cii_exam,
    generate_ccss_exam, _generate_mixed, generate_mixed_both_exam,
    generate_fisica_exam, generate_quimica_exam,
    build_exam_pdf, get_next_exam_id,
    CII_TEMAS, CCSS_TEMAS, FISICA_TEMAS, QUIMICA_TEMAS,
)

BASE_PATH = _base

# --- Color palette ---
BG = "#f5f6fa"
CARD = "#ffffff"
BORDER = "#e0e3eb"
TEXT = "#1e293b"
TEXT_SEC = "#64748b"
ACCENT = "#3b82f6"      # Blue
ACCENT_DARK = "#2563eb"
SUCCESS = "#22c55e"
SUCCESS_DARK = "#16a34a"
DANGER = "#ef4444"
HDR_BG = "#1e293b"
HDR_FG = "#ffffff"
HDR_SUB = "#94a3b8"
LOG_BG = "#1e1e2e"
LOG_FG = "#cdd6f4"
TAB_BG = "#f1f5f9"
TAB_SEL = ACCENT


def _setup_dpi():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def _setup_style(style):
    style.theme_use("clam")

    # General
    style.configure(".", font=("Segoe UI", 10), background=BG, foreground=TEXT)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD, relief="solid", borderwidth=1)
    style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("Header.TLabel", background=HDR_BG, foreground=HDR_FG,
                     font=("Segoe UI", 17, "bold"))
    style.configure("SubHeader.TLabel", background=HDR_BG, foreground=HDR_SUB,
                     font=("Segoe UI", 9))
    style.configure("Section.TLabel", background=CARD, foreground=TEXT,
                     font=("Segoe UI", 10, "bold"))
    style.configure("CardBody.TLabel", background=CARD, foreground=TEXT,
                     font=("Segoe UI", 10))
    style.configure("Status.TLabel", background=BG, foreground=TEXT_SEC,
                     font=("Segoe UI", 9))

    # Notebook
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
    style.configure("TNotebook.Tab", background=TAB_BG, foreground=TEXT_SEC,
                     font=("Segoe UI", 10, "bold"), padding=[18, 8],
                     borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", CARD)],
              foreground=[("selected", ACCENT)],
              bordercolor=[("selected", ACCENT)])
    style.layout("TNotebook.Tab", [
        ("Notebook.tab", {"sticky": "nswe", "children": [
            ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [
                ("Notebook.label", {"side": "top", "sticky": ""})
            ]})
        ]})
    ])

    # Checkbutton
    style.configure("TCheckbutton", background=CARD, foreground=TEXT,
                     font=("Segoe UI", 9), focuscolor="")
    style.map("TCheckbutton", background=[("active", CARD)])

    # Radiobutton
    style.configure("TRadiobutton", background=CARD, foreground=TEXT,
                     font=("Segoe UI", 9), focuscolor="")
    style.map("TRadiobutton", background=[("active", CARD)])

    # Entry
    style.configure("TEntry", fieldbackground="white", foreground=TEXT,
                     bordercolor=BORDER, lightcolor=BORDER,
                     font=("Segoe UI", 10), padding=4)
    style.map("TEntry", bordercolor=[("focus", ACCENT)],
              lightcolor=[("focus", ACCENT)])

    # Spinbox
    style.configure("TSpinbox", fieldbackground="white", foreground=TEXT,
                     bordercolor=BORDER, lightcolor=BORDER,
                     arrowcolor=TEXT_SEC, padding=4)
    style.map("TSpinbox", bordercolor=[("focus", ACCENT)])

    # Buttons
    style.configure("Accent.TButton",
                     background=ACCENT, foreground="white",
                     font=("Segoe UI", 10, "bold"), padding=[16, 8],
                     borderwidth=0)
    style.map("Accent.TButton",
              background=[("active", ACCENT_DARK), ("disabled", BORDER)],
              foreground=[("disabled", TEXT_SEC)])

    style.configure("Success.TButton",
                     background=SUCCESS, foreground="white",
                     font=("Segoe UI", 9, "bold"), padding=[10, 5],
                     borderwidth=0)
    style.map("Success.TButton",
              background=[("active", SUCCESS_DARK), ("disabled", BORDER)])

    style.configure("Secondary.TButton",
                     background="#e2e8f0", foreground=TEXT,
                     font=("Segoe UI", 10), padding=[14, 8],
                     borderwidth=0)
    style.map("Secondary.TButton",
              background=[("active", "#cbd5e1"), ("disabled", BORDER)])

    style.configure("Small.TButton",
                     background="#e2e8f0", foreground=TEXT,
                     font=("Segoe UI", 9), padding=[6, 3],
                     borderwidth=0)
    style.map("Small.TButton", background=[("active", "#cbd5e1")])

    # Progressbar
    style.configure("Accent.Horizontal.TProgressbar",
                     troughcolor=BORDER, background=ACCENT,
                     borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)

    # Separator
    style.configure("TSeparator", background=BORDER)


class ExamApp(tk.Tk):
    def __init__(self):
        _setup_dpi()
        super().__init__()
        self.title("Generador de Examenes Selectividad")
        self.resizable(False, False)
        self.configure(bg=BG)

        icon_path = BASE_PATH / "icon.ico"
        if icon_path.exists():
            self.iconbitmap(str(icon_path))

        self._style = ttk.Style(self)
        _setup_style(self._style)

        self._exercises = {}
        self._tema_vars = {}
        self._build_ui()
        self._center_window()

    def _build_ui(self):
        # ===== Header =====
        hdr = tk.Frame(self, bg=HDR_BG, height=70)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        hdr_inner = tk.Frame(hdr, bg=HDR_BG)
        hdr_inner.pack(expand=True)
        tk.Label(hdr_inner, text="Generador de Examenes Selectividad",
                 font=("Segoe UI", 17, "bold"), fg=HDR_FG, bg=HDR_BG
                 ).pack(pady=(12, 0))
        tk.Label(hdr_inner, text="Version publica  \u2022  sin soluciones",
                 font=("Segoe UI", 9), fg=HDR_SUB, bg=HDR_BG).pack()

        # ===== Main container =====
        outer = ttk.Frame(self, style="TFrame")
        outer.pack(fill="both", expand=True, padx=20, pady=(12, 20))

        # --- Exercises folder card ---
        dir_card = tk.Frame(outer, bg=CARD, bd=1, relief="solid",
                            highlightbackground=BORDER, highlightthickness=1)
        dir_card.pack(fill="x", pady=(0, 10))
        dir_inner = tk.Frame(dir_card, bg=CARD)
        dir_inner.pack(fill="x", padx=14, pady=10)

        ttk.Label(dir_inner, text="Carpeta de ejercicios",
                  style="Section.TLabel").pack(anchor="w")
        row_f = tk.Frame(dir_inner, bg=CARD)
        row_f.pack(fill="x", pady=(6, 0))
        self.var_ex_dir = tk.StringVar(value=str(BASE_PATH / "ejercicios"))
        entry = ttk.Entry(row_f, textvariable=self.var_ex_dir, width=52,
                          font=("Segoe UI", 9), style="TEntry")
        entry.pack(side="left", fill="x", expand=True)
        ttk.Button(row_f, text="...", width=3, style="Small.TButton",
                   command=lambda: self._browse("var_ex_dir")).pack(side="left", padx=(6, 4))
        self.btn_load = ttk.Button(row_f, text="Cargar", style="Success.TButton",
                                   command=self._load)
        self.btn_load.pack(side="left")

        # --- Notebook ---
        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="x", pady=(0, 10))

        # Tab: Matematicas
        self.tab_mat = tk.Frame(self.notebook, bg=CARD)
        self.notebook.add(self.tab_mat, text="  \U0001F4D0  Matematicas  ")
        asig_frame = tk.Frame(self.tab_mat, bg=CARD)
        asig_frame.pack(anchor="w", padx=14, pady=(10, 0))
        self.var_asig = tk.StringVar(value="CII_y_CCSS")
        for val, txt in [("CII", "Mat. II"), ("CCSS", "Mat. CCSS"), ("CII_y_CCSS", "Ambas")]:
            ttk.Radiobutton(asig_frame, text=txt, variable=self.var_asig, value=val,
                            style="TRadiobutton",
                            command=self._on_asig_change).pack(side="left", padx=(0, 14))
        self.temas_frame_mat = tk.Frame(self.tab_mat, bg=CARD)
        self.temas_frame_mat.pack(anchor="w", padx=14, pady=(4, 10))

        # Tab: Fisica
        self.tab_fis = tk.Frame(self.notebook, bg=CARD)
        self.notebook.add(self.tab_fis, text="  \u269B  Fisica  ")
        self.temas_frame_fis = tk.Frame(self.tab_fis, bg=CARD)
        self.temas_frame_fis.pack(anchor="w", padx=14, pady=10)

        # Tab: Quimica
        self.tab_qui = tk.Frame(self.notebook, bg=CARD)
        self.notebook.add(self.tab_qui, text="  \u2697  Quimica  ")
        self.temas_frame_qui = tk.Frame(self.tab_qui, bg=CARD)
        self.temas_frame_qui.pack(anchor="w", padx=14, pady=10)

        # --- Options row ---
        opt_card = tk.Frame(outer, bg=CARD, bd=1, relief="solid",
                            highlightbackground=BORDER, highlightthickness=1)
        opt_card.pack(fill="x", pady=(0, 10))
        opt_inner = tk.Frame(opt_card, bg=CARD)
        opt_inner.pack(fill="x", padx=14, pady=10)

        opt_row = tk.Frame(opt_inner, bg=CARD)
        opt_row.pack(fill="x")
        ttk.Label(opt_row, text="N\u00ba examenes:", style="CardBody.TLabel").pack(side="left")
        self.var_num = tk.IntVar(value=1)
        ttk.Spinbox(opt_row, from_=1, to=100, textvariable=self.var_num,
                     width=5, font=("Segoe UI", 10)).pack(side="left", padx=(6, 20))
        ttk.Label(opt_row, text="Semilla:", style="CardBody.TLabel").pack(side="left")
        self.var_seed = tk.StringVar()
        ttk.Entry(opt_row, textvariable=self.var_seed, width=10,
                  font=("Segoe UI", 10)).pack(side="left", padx=(6, 0))
        ttk.Label(opt_row, text="(vacio = aleatorio)", style="Status.TLabel"
                  ).pack(side="left", padx=(6, 0))

        # --- Action bar ---
        action_frame = ttk.Frame(outer)
        action_frame.pack(fill="x", pady=(0, 10))

        self.btn_gen = ttk.Button(
            action_frame, text="\u25B6  Generar examenes", style="Accent.TButton",
            command=self._start_gen, state="disabled")
        self.btn_gen.pack(side="left")

        self.btn_open = ttk.Button(
            action_frame, text="\U0001F4C2  Abrir carpeta", style="Secondary.TButton",
            command=self._open_folder, state="disabled")
        self.btn_open.pack(side="left", padx=(8, 0))

        # Status + progress on right
        status_frame = ttk.Frame(action_frame)
        status_frame.pack(side="right")
        self.lbl_status = ttk.Label(status_frame, text="Ejercicios no cargados",
                                    style="Status.TLabel")
        self.lbl_status.pack(anchor="e")
        self.progress = ttk.Progressbar(status_frame, length=180, mode="determinate",
                                         style="Accent.Horizontal.TProgressbar")
        self.progress.pack(anchor="e", pady=(2, 0))

        # --- Log ---
        log_frame = tk.Frame(outer, bg=LOG_BG, bd=1, relief="solid",
                              highlightbackground="#313244", highlightthickness=1)
        log_frame.pack(fill="both", expand=True)

        log_header = tk.Frame(log_frame, bg="#181825")
        log_header.pack(fill="x")
        tk.Label(log_header, text="  Registro", bg="#181825", fg="#a6adc8",
                 font=("Segoe UI", 8)).pack(anchor="w", padx=4, pady=2)

        log_body = tk.Frame(log_frame, bg=LOG_BG)
        log_body.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_body, height=9, font=("Cascadia Code", 9),
                                bg=LOG_BG, fg=LOG_FG, insertbackground=LOG_FG,
                                state="disabled", wrap="word", bd=0,
                                highlightthickness=0, padx=8, pady=6,
                                selectbackground="#45475a", selectforeground=LOG_FG)
        self.log_text.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(log_body, orient="vertical", command=self.log_text.yview)
        sb.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=sb.set)

    def _center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"+{x}+{y}")

    def _log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.update_idletasks()

    def _set_status(self, msg, color=TEXT_SEC):
        self.lbl_status.configure(text=msg, foreground=color)
        self.update_idletasks()

    def _browse(self, var_name):
        d = filedialog.askdirectory()
        if d:
            getattr(self, var_name).set(d)

    def _on_asig_change(self):
        if self._exercises:
            self._update_temas()

    def _update_temas(self):
        self._tema_vars.clear()
        info = get_available_temas(self._exercises)

        # --- Math tab ---
        for w in self.temas_frame_mat.winfo_children():
            w.destroy()
        asig = self.var_asig.get()
        asigs = []
        if asig in ("CII", "CII_y_CCSS"):
            asigs.append("CII")
        if asig in ("CCSS", "CII_y_CCSS"):
            asigs.append("CCSS")
        for col_idx, a in enumerate(asigs):
            if a not in info:
                continue
            col_frame = tk.Frame(self.temas_frame_mat, bg=CARD)
            col_frame.grid(row=0, column=col_idx, sticky="nw", padx=(0, 24))
            lbl = "Mat. II" if a == "CII" else "Mat. CCSS"
            tk.Label(col_frame, text=f"{lbl}:", bg=CARD, fg=ACCENT,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            for tema_key, tema_info in info[a].items():
                var = tk.BooleanVar(value=True)
                key = f"{a}_{tema_key}"
                self._tema_vars[key] = var
                ttk.Checkbutton(
                    col_frame,
                    text=f"  {tema_info['display']} ({tema_info['count']})",
                    variable=var, style="TCheckbutton"
                ).pack(anchor="w")

        # --- Physics tab ---
        for w in self.temas_frame_fis.winfo_children():
            w.destroy()
        if "FISICA" in info:
            for tema_key, tema_info in info["FISICA"].items():
                var = tk.BooleanVar(value=True)
                key = f"FISICA_{tema_key}"
                self._tema_vars[key] = var
                ttk.Checkbutton(
                    self.temas_frame_fis,
                    text=f"  {tema_info['display']} ({tema_info['count']})",
                    variable=var, style="TCheckbutton"
                ).pack(anchor="w")

        # --- Chemistry tab ---
        for w in self.temas_frame_qui.winfo_children():
            w.destroy()
        if "QUIMICA" in info:
            for tema_key, tema_info in info["QUIMICA"].items():
                var = tk.BooleanVar(value=True)
                key = f"QUIMICA_{tema_key}"
                self._tema_vars[key] = var
                ttk.Checkbutton(
                    self.temas_frame_qui,
                    text=f"  {tema_info['display']} ({tema_info['count']})",
                    variable=var, style="TCheckbutton"
                ).pack(anchor="w")

    def _load(self):
        ex_dir = Path(self.var_ex_dir.get())
        try:
            self._exercises = load_exercises(ex_dir)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if not self._exercises:
            messagebox.showerror("Error", f"No se encontraron ejercicios en:\n{ex_dir}")
            return

        total = sum(len(f) for asig in self._exercises.values() for f in asig.values())
        self._log(f"Cargados: {total} ejercicios")
        for asig in sorted(self._exercises):
            for tema, files in sorted(self._exercises[asig].items()):
                self._log(f"  {asig}/{tema}: {len(files)}")

        self._set_status(f"\u2714  {total} ejercicios cargados", SUCCESS)
        self._update_temas()
        self.btn_gen.configure(state="normal")

    def _get_output_dir(self):
        today = date.today().strftime("%Y-%m-%d")
        return str(BASE_PATH / "examenes_generados" / today)

    def _get_active_temas(self, asig):
        active = []
        temas_maps = {
            "CII": CII_TEMAS, "CCSS": CCSS_TEMAS,
            "FISICA": FISICA_TEMAS, "QUIMICA": QUIMICA_TEMAS,
        }
        temas_map = temas_maps.get(asig, {})
        for tema_key in temas_map:
            key = f"{asig}_{tema_key}"
            if key in self._tema_vars and self._tema_vars[key].get():
                active.append(tema_key)
        return active

    def _get_active_tab(self):
        return self.notebook.index(self.notebook.select())

    def _start_gen(self):
        tab_idx = self._get_active_tab()
        asig = self.var_asig.get()
        num = self.var_num.get()
        seed_str = self.var_seed.get().strip()
        seed = int(seed_str) if seed_str.isdigit() else None

        self.btn_gen.configure(state="disabled")
        self.btn_load.configure(state="disabled")
        self.progress["value"] = 0
        self.progress["maximum"] = num

        self._last_paths = []
        t = threading.Thread(
            target=self._gen_worker,
            args=(tab_idx, asig, num, seed),
            daemon=True)
        t.start()

    def _gen_worker(self, tab_idx, asig, num, seed):
        try:
            output_dir = self._get_output_dir()
            start_id = get_next_exam_id(output_dir)

            for i in range(num):
                exam_id = start_id + i
                s = (seed + i) if seed is not None else None

                if tab_idx == 0:
                    if asig == "CII":
                        temas = self._get_active_temas("CII")
                        sections, labels = generate_cii_exam(self._exercises, temas, s)
                        tag = "CII"
                    elif asig == "CCSS":
                        temas = self._get_active_temas("CCSS")
                        sections, labels = generate_ccss_exam(self._exercises, temas, s)
                        tag = "CCSS"
                    else:
                        temas_cii = self._get_active_temas("CII")
                        temas_ccss = self._get_active_temas("CCSS")
                        sections, labels = generate_mixed_both_exam(
                            self._exercises, temas_cii, temas_ccss, 6, s)
                        tag = "CII_y_CCSS"
                elif tab_idx == 1:
                    temas = self._get_active_temas("FISICA")
                    sections, labels = generate_fisica_exam(self._exercises, temas, s)
                    tag = "FISICA"
                else:
                    temas = self._get_active_temas("QUIMICA")
                    sections, labels = generate_quimica_exam(self._exercises, temas, s)
                    tag = "QUIMICA"

                path = build_exam_pdf(sections, labels, exam_id, output_dir, tag, solved=False)
                self._last_paths.append(path)
                self.after(0, self._log, f"Examen {exam_id}: {Path(path).name}")
                self.after(0, self._update_progress, i + 1)

            self.after(0, self._gen_done, num)
        except Exception as e:
            self.after(0, self._gen_error, str(e))

    def _update_progress(self, val):
        self.progress["value"] = val

    def _gen_done(self, count):
        self._set_status(f"\u2714  {count} examenes generados", SUCCESS)
        self._log(f"\n{count} examenes generados correctamente.")
        self.btn_gen.configure(state="normal")
        self.btn_load.configure(state="normal")
        self.btn_open.configure(state="normal")
        if len(self._last_paths) == 1 and Path(self._last_paths[0]).exists():
            os.startfile(self._last_paths[0])
        else:
            folder = Path(self._get_output_dir())
            if folder.exists():
                os.startfile(str(folder))

    def _gen_error(self, msg):
        self._set_status(f"\u2716  Error", DANGER)
        self._log(f"ERROR: {msg}")
        messagebox.showerror("Error", msg)
        self.btn_gen.configure(state="normal")
        self.btn_load.configure(state="normal")

    def _open_folder(self):
        folder = Path(self._get_output_dir())
        if folder.exists():
            os.startfile(str(folder))
        else:
            parent = folder.parent
            if parent.exists():
                os.startfile(str(parent))


if __name__ == "__main__":
    app = ExamApp()
    app.mainloop()
