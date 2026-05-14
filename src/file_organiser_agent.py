import json
import os
import re
import shutil
import threading
import tkinter as tk
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_NAME = "Offline File Organiser Agent"
APP_VERSION = "1.1"


C = {
    "bg": "#080a0f",
    "bg2": "#0a0f16",
    "surface": "#0d1017",
    "surface2": "#111925",
    "card": "#0f1520",
    "card2": "#151e2c",
    "border": "#1a2030",
    "border2": "#26344a",
    "cyan": "#00e5ff",
    "blue": "#5aa7ff",
    "green": "#39ff14",
    "amber": "#ffb300",
    "red": "#ff3d5a",
    "violet": "#b58cff",
    "text": "#e8edf5",
    "muted": "#7d8798",
    "muted2": "#aab4c3",
    "white": "#ffffff",
}

FONT_TITLE = ("Courier", 34, "bold")
FONT_SUBTITLE = ("Courier", 11)
FONT_HEAD = ("Courier", 13, "bold")
FONT_BODY = ("Courier", 10)
FONT_SMALL = ("Courier", 9)
FONT_MONO = ("Courier", 10)
FONT_STAT = ("Courier", 18, "bold")


CATEGORY_RULES = {
    "Documents": {
        "extensions": {
            ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".md", ".pages"
        },
        "keywords": {"document", "letter", "notes", "draft", "manual", "guide"},
    },
    "Spreadsheets": {
        "extensions": {".xls", ".xlsx", ".csv", ".tsv", ".ods", ".numbers"},
        "keywords": {"spreadsheet", "budget", "ledger", "sales", "report", "sheet"},
    },
    "Images": {
        "extensions": {
            ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff",
            ".heic", ".svg", ".psd", ".ai"
        },
        "keywords": {"image", "photo", "screenshot", "picture", "scan", "logo"},
    },
    "Videos": {
        "extensions": {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm", ".m4v"},
        "keywords": {"video", "clip", "recording", "screenrecord"},
    },
    "Audio": {
        "extensions": {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"},
        "keywords": {"audio", "music", "voice", "podcast", "recording"},
    },
    "Archives": {
        "extensions": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
        "keywords": {"archive", "backup", "compressed"},
    },
    "Installers": {
        "extensions": {".exe", ".msi", ".dmg", ".pkg", ".appinstaller", ".deb", ".rpm"},
        "keywords": {"setup", "installer", "install", "update"},
    },
    "Code": {
        "extensions": {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".json",
            ".xml", ".yaml", ".yml", ".sql", ".ps1", ".bat", ".sh", ".java", ".cs",
            ".cpp", ".c", ".h", ".go", ".rs", ".php", ".rb"
        },
        "keywords": {"code", "script", "source", "project", "config"},
    },
    "Design": {
        "extensions": {".fig", ".sketch", ".xd", ".indd", ".eps", ".blend", ".obj", ".fbx"},
        "keywords": {"design", "mockup", "wireframe", "brand", "asset"},
    },
}

PROTECTED_NAMES = {
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
}

DEFAULT_INSTRUCTIONS = (
    "Sort my desktop into clear folders by file type. Keep screenshots together. "
    "Put invoices, receipts, and tax files into Finance. Put resumes and job files "
    "into Career. Do not delete anything."
)


@dataclass
class MovePlan:
    source: str
    target: str
    category: str
    reason: str
    status: str = "Ready"


def desktop_path():
    return Path.home() / "Desktop"


def safe_folder_name(name):
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:80] or "Other"


def tokenize(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def parse_instruction_profile(instructions):
    text = instructions.lower()
    custom = {}
    ignored = set()

    if any(word in text for word in ("date", "month", "year")):
        mode = "date"
    elif any(word in text for word in ("client", "project", "job", "case")):
        mode = "project"
    else:
        mode = "type"

    folder_match = re.search(r"(?:folders|categories)\s*:\s*([^\n.]+)", instructions, re.I)
    if folder_match:
        for item in re.split(r"[,;|]", folder_match.group(1)):
            name = safe_folder_name(item)
            if name:
                custom[name] = tokenize(name)

    for line in instructions.splitlines():
        if "->" in line:
            left, right = line.split("->", 1)
            folder = safe_folder_name(right)
            words = tokenize(left)
            if folder and words:
                custom.setdefault(folder, set()).update(words)

    for phrase, folder in {
        "invoice": "Finance",
        "receipt": "Finance",
        "tax": "Finance",
        "bank": "Finance",
        "resume": "Career",
        "cv": "Career",
        "job": "Career",
        "contract": "Legal",
        "agreement": "Legal",
        "screenshot": "Screenshots",
        "screen shot": "Screenshots",
    }.items():
        if phrase in text:
            custom.setdefault(folder, set()).add(phrase.replace(" ", ""))

    ignore_match = re.search(r"(?:ignore|leave|skip)\s*:\s*([^\n.]+)", instructions, re.I)
    if ignore_match:
        ignored.update(tokenize(ignore_match.group(1)))

    return mode, custom, ignored


def category_by_type(path, custom_categories):
    ext = path.suffix.lower()
    name_tokens = tokenize(path.stem)
    best_name = "Other"
    best_score = 0
    reason = "No strong match, placed in Other"

    for category, keywords in custom_categories.items():
        score = len(name_tokens & keywords) * 10
        if score > best_score:
            best_name = category
            best_score = score
            reason = f"Matched instruction keywords for {category}"

    for category, rule in CATEGORY_RULES.items():
        score = 0
        if ext in rule["extensions"]:
            score += 5
        score += len(name_tokens & rule["keywords"]) * 2
        if score > best_score:
            best_name = category
            best_score = score
            if ext in rule["extensions"]:
                reason = f"Matched {ext or 'file'} type"
            else:
                reason = f"Matched name keywords for {category}"

    return best_name, reason


def category_by_date(path):
    try:
        stamp = datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        stamp = datetime.now()
    return stamp.strftime("%Y-%m"), "Grouped by modified month"


def category_by_project(path, custom_categories):
    name_tokens = [t for t in re.findall(r"[A-Za-z0-9]+", path.stem) if len(t) >= 3]
    for category, keywords in custom_categories.items():
        if tokenize(path.stem) & keywords:
            return category, f"Matched instruction keywords for {category}"
    if name_tokens:
        return safe_folder_name(name_tokens[0].title()), "Grouped by first project-like word"
    return "Other", "No project-like word found"


def unique_target(target):
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    counter = 2
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def is_relative_to(path, parent):
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def build_plan(source_dir, dest_dir, instructions):
    source_dir = Path(source_dir).resolve()
    dest_dir = Path(dest_dir).resolve()
    mode, custom_categories, ignored = parse_instruction_profile(instructions)
    plans = []

    for path in sorted(source_dir.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file():
            continue
        if path.name.lower() in PROTECTED_NAMES:
            continue
        if is_relative_to(path, dest_dir):
            continue
        if tokenize(path.name) & ignored:
            continue

        if mode == "date":
            category, reason = category_by_date(path)
        elif mode == "project":
            category, reason = category_by_project(path, custom_categories)
        else:
            category, reason = category_by_type(path, custom_categories)

        category = safe_folder_name(category)
        target_dir = dest_dir / category
        target = unique_target(target_dir / path.name)
        if path.resolve() == target.resolve():
            continue
        plans.append(MovePlan(str(path), str(target), category, reason))

    return plans


class FileOrganiserApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1160x760")
        self.minsize(980, 660)
        self.configure(bg=C["bg"])
        self.plans = []
        self.last_manifest = None

        self.source_var = tk.StringVar(value=str(desktop_path()))
        self.dest_var = tk.StringVar(value=str(desktop_path() / "Sorted Files"))
        self.status_var = tk.StringVar(value="Ready. Preview the plan before sorting.")
        self.count_var = tk.StringVar(value="0 files")
        self.folder_var = tk.StringVar(value="0 folders")
        self.safety_var = tk.StringVar(value="Preview mode")

        self._build_styles()
        self._build_ui()

    def _build_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", background=C["surface"], foreground=C["text"],
                        fieldbackground=C["surface"], rowheight=32, borderwidth=0,
                        font=FONT_BODY)
        style.configure("Treeview.Heading", background=C["card2"], foreground=C["cyan"],
                        font=FONT_HEAD, relief="flat")
        style.map("Treeview", background=[("selected", "#123344")],
                  foreground=[("selected", C["white"])])
        style.configure("Horizontal.TProgressbar", background=C["cyan"],
                        troughcolor=C["surface"], bordercolor=C["border"])

    def _panel(self, parent, **grid):
        frame = tk.Frame(parent, bg=C["surface"], highlightbackground=C["border"],
                         highlightthickness=1)
        frame.grid(**grid)
        return frame

    def _button(self, parent, text, command, fg=None):
        button = tk.Button(parent, text=text, command=command, bg=C["card2"],
                           fg=fg or C["text"], activebackground="#1b2b40",
                           activeforeground=C["white"], relief="flat", bd=0,
                           padx=16, pady=10, font=FONT_HEAD, cursor="hand2")
        button.bind("<Enter>", lambda _event: button.configure(bg="#1b2b40"))
        button.bind("<Leave>", lambda _event: button.configure(bg=C["card2"]))
        return button

    def _entry(self, parent, variable):
        return tk.Entry(parent, textvariable=variable, bg=C["bg2"], fg=C["text"],
                        insertbackground=C["cyan"], relief="flat", font=FONT_MONO,
                        highlightbackground=C["border"], highlightcolor=C["cyan"],
                        highlightthickness=1)

    def _stat_card(self, parent, title, variable, accent, column):
        card = tk.Frame(parent, bg=C["surface2"], highlightbackground=C["border2"],
                        highlightthickness=1)
        card.grid(row=0, column=column, sticky="ew", padx=(0, 10))
        tk.Frame(card, bg=accent, height=4).grid(row=0, column=0, sticky="ew")
        tk.Label(card, text=title, bg=C["surface2"], fg=C["muted2"], font=FONT_SMALL).grid(
            row=1, column=0, sticky="w", padx=12, pady=(10, 0))
        tk.Label(card, textvariable=variable, bg=C["surface2"], fg=accent, font=FONT_STAT).grid(
            row=2, column=0, sticky="w", padx=12, pady=(0, 12))
        return card

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        accent_bar = tk.Frame(self, bg=C["cyan"], height=5)
        accent_bar.grid(row=0, column=0, sticky="ew")

        header = tk.Frame(self, bg=C["bg2"], highlightbackground=C["border"],
                          highlightthickness=1)
        header.grid(row=1, column=0, sticky="ew", padx=24, pady=(18, 14))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        tk.Label(header, text="FILE ORGANISER", bg=C["bg2"], fg=C["cyan"],
                 font=FONT_TITLE).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 0))
        tk.Label(header, text=f"{APP_NAME} v{APP_VERSION}  |  Offline desktop cleanup agent",
                 bg=C["bg2"], fg=C["muted2"], font=FONT_SUBTITLE).grid(
                     row=1, column=0, sticky="w", padx=20, pady=(0, 18))
        badge_wrap = tk.Frame(header, bg=C["bg2"])
        badge_wrap.grid(row=0, column=1, rowspan=2, sticky="e", padx=18)
        tk.Label(badge_wrap, text="MOVE ONLY", bg=C["green"], fg="#061008",
                 font=("Courier", 16, "bold"), padx=16, pady=8).grid(row=0, column=0, sticky="e")
        tk.Label(badge_wrap, text="Never deletes. Never overwrites.",
                 bg=C["bg2"], fg=C["muted2"], font=FONT_SMALL).grid(row=1, column=0, sticky="e", pady=(8, 0))

        stats = tk.Frame(self, bg=C["bg"])
        stats.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 14))
        stats.grid_columnconfigure(0, weight=1)
        stats.grid_columnconfigure(1, weight=1)
        stats.grid_columnconfigure(2, weight=1)
        self._stat_card(stats, "PLANNED MOVES", self.count_var, C["cyan"], 0)
        self._stat_card(stats, "TARGET FOLDERS", self.folder_var, C["violet"], 1)
        self._stat_card(stats, "SAFETY STATE", self.safety_var, C["green"], 2)

        controls = self._panel(self, row=3, column=0, sticky="ew", padx=24, pady=(0, 14))
        controls.grid_columnconfigure(1, weight=1)
        controls.grid_columnconfigure(3, weight=1)

        tk.Label(controls, text="SOURCE", bg=C["surface"], fg=C["muted"],
                 font=FONT_SMALL).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 3))
        self._entry(controls, self.source_var).grid(
                     row=1, column=0, columnspan=2, sticky="ew", padx=(14, 8), pady=(0, 12), ipady=8)
        self._button(controls, "Browse", self.pick_source).grid(
            row=1, column=2, sticky="ew", padx=(0, 14), pady=(0, 12))

        tk.Label(controls, text="SORT INTO", bg=C["surface"], fg=C["muted"],
                 font=FONT_SMALL).grid(row=0, column=3, sticky="w", padx=14, pady=(14, 3))
        self._entry(controls, self.dest_var).grid(
                     row=1, column=3, sticky="ew", padx=(14, 8), pady=(0, 12), ipady=8)
        self._button(controls, "Browse", self.pick_dest).grid(
            row=1, column=4, sticky="ew", padx=(0, 14), pady=(0, 12))

        main = tk.Frame(self, bg=C["bg"])
        main.grid(row=4, column=0, sticky="nsew", padx=24)
        main.grid_columnconfigure(0, weight=0)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        left = self._panel(main, row=0, column=0, sticky="ns", padx=(0, 14), pady=0)
        left.grid_rowconfigure(1, weight=1)
        tk.Label(left, text="SORTING RULES", bg=C["surface"], fg=C["cyan"],
                 font=FONT_HEAD).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))
        self.instructions = tk.Text(left, width=38, height=16, bg=C["bg"], fg=C["text"],
                                    insertbackground=C["cyan"], relief="flat",
                                    wrap="word", font=FONT_BODY, padx=12, pady=12,
                                    highlightbackground=C["border"], highlightcolor=C["cyan"],
                                    highlightthickness=1)
        self.instructions.grid(row=1, column=0, sticky="nsew", padx=14)
        self.instructions.insert("1.0", DEFAULT_INSTRUCTIONS)

        help_text = (
            "Examples:\n"
            "folders: Finance, Photos, Work\n"
            "invoices receipts tax -> Finance\n"
            "ignore: shortcuts temp\n"
            "Sort by date/month/project/type"
        )
        tk.Label(left, text=help_text, bg=C["surface"], fg=C["muted"],
                 justify="left", font=FONT_SMALL).grid(row=2, column=0, sticky="w",
                                                       padx=14, pady=14)

        action_row = tk.Frame(left, bg=C["surface"])
        action_row.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
        action_row.grid_columnconfigure(0, weight=1)
        action_row.grid_columnconfigure(1, weight=1)
        self._button(action_row, "Preview", self.preview, C["cyan"]).grid(
            row=0, column=0, sticky="ew", padx=(0, 8))
        self.sort_button = self._button(action_row, "Sort Files", self.sort_files, C["green"])
        self.sort_button.grid(row=0, column=1, sticky="ew")

        right = self._panel(main, row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        plan_header = tk.Frame(right, bg=C["surface"])
        plan_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        plan_header.grid_columnconfigure(0, weight=1)
        tk.Label(plan_header, text="PREVIEW PLAN", bg=C["surface"], fg=C["cyan"],
                 font=FONT_HEAD).grid(row=0, column=0, sticky="w")
        tk.Label(plan_header, text="preview first, then move", bg=C["surface"],
                 fg=C["muted"], font=FONT_SMALL).grid(row=0, column=1, sticky="e")

        cols = ("file", "category", "target", "reason", "status")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("file", text="File")
        self.tree.heading("category", text="Folder")
        self.tree.heading("target", text="Target")
        self.tree.heading("reason", text="Reason")
        self.tree.heading("status", text="Status")
        self.tree.column("file", width=210, anchor="w")
        self.tree.column("category", width=120, anchor="w")
        self.tree.column("target", width=280, anchor="w")
        self.tree.column("reason", width=230, anchor="w")
        self.tree.column("status", width=90, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=14)
        self.tree.tag_configure("odd", background=C["surface"])
        self.tree.tag_configure("even", background=C["surface2"])
        self.tree.tag_configure("moved", foreground=C["green"])
        self.tree.tag_configure("error", foreground=C["red"])
        self.tree.tag_configure("ready", foreground=C["text"])

        scroll = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns", pady=(0, 14))

        footer = tk.Frame(self, bg=C["bg"])
        footer.grid(row=5, column=0, sticky="ew", padx=24, pady=18)
        footer.grid_columnconfigure(0, weight=1)

        tk.Label(footer, textvariable=self.status_var, bg=C["bg"], fg=C["muted"],
                 font=FONT_BODY).grid(row=0, column=0, sticky="w")
        self.progress = ttk.Progressbar(footer, mode="determinate", style="Horizontal.TProgressbar")
        self.progress.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self._button(footer, "Undo Last Sort", self.undo_last_sort, C["amber"]).grid(
            row=0, column=1, rowspan=2, sticky="e", padx=(14, 0))

    def update_stats(self):
        folders = {plan.category for plan in self.plans}
        self.count_var.set(f"{len(self.plans)} files")
        self.folder_var.set(f"{len(folders)} folders")
        if any(plan.status.startswith("Error") for plan in self.plans):
            self.safety_var.set("Check errors")
        elif any(plan.status == "Moved" for plan in self.plans):
            self.safety_var.set("Undo log ready")
        else:
            self.safety_var.set("Preview mode")

    def pick_source(self):
        path = filedialog.askdirectory(title="Choose folder to organise",
                                       initialdir=self.source_var.get())
        if path:
            self.source_var.set(path)
            if not self.dest_var.get():
                self.dest_var.set(str(Path(path) / "Sorted Files"))

    def pick_dest(self):
        path = filedialog.askdirectory(title="Choose destination folder",
                                       initialdir=self.dest_var.get())
        if path:
            self.dest_var.set(path)

    def preview(self):
        try:
            self.plans = build_plan(
                self.source_var.get(),
                self.dest_var.get(),
                self.instructions.get("1.0", "end").strip(),
            )
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not build plan:\n{exc}")
            return
        self.render_plan()
        self.update_stats()
        self.status_var.set(f"Preview ready: {len(self.plans)} file(s) will be moved. Nothing has changed yet.")

    def render_plan(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for index, plan in enumerate(self.plans):
            status_tag = "ready"
            if plan.status == "Moved":
                status_tag = "moved"
            elif plan.status.startswith("Error"):
                status_tag = "error"
            self.tree.insert("", "end", values=(
                Path(plan.source).name,
                plan.category,
                str(Path(plan.target).parent),
                plan.reason,
                plan.status,
            ), tags=("even" if index % 2 == 0 else "odd", status_tag))

    def sort_files(self):
        if not self.plans:
            self.preview()
        if not self.plans:
            messagebox.showinfo(APP_NAME, "No files found to sort.")
            return
        answer = messagebox.askyesno(
            APP_NAME,
            "Move the planned files now?\n\n"
            "This app only moves files into folders. It does not delete files or overwrite existing files.",
        )
        if not answer:
            return
        self.sort_button.configure(state="disabled")
        threading.Thread(target=self._sort_worker, daemon=True).start()

    def _sort_worker(self):
        moved = []
        total = len(self.plans)
        manifest_dir = Path(self.dest_var.get()) / "_organiser_logs"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / f"sort-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        self.last_manifest = manifest_path

        for idx, plan in enumerate(self.plans, start=1):
            source = Path(plan.source)
            target = unique_target(Path(plan.target))
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                if source.exists() and source.is_file():
                    shutil.move(str(source), str(target))
                    plan.target = str(target)
                    plan.status = "Moved"
                    moved.append(asdict(plan))
                else:
                    plan.status = "Missing"
            except Exception as exc:
                plan.status = f"Error: {exc}"

            self.after(0, self._worker_progress, idx, total)

        manifest = {
            "app": APP_NAME,
            "version": APP_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "source": self.source_var.get(),
            "destination": self.dest_var.get(),
            "moves": moved,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self.after(0, self._sort_done, len(moved), manifest_path)

    def _worker_progress(self, idx, total):
        self.progress["maximum"] = total
        self.progress["value"] = idx
        self.render_plan()
        self.update_stats()
        self.status_var.set(f"Sorting files: {idx}/{total}")

    def _sort_done(self, moved_count, manifest_path):
        self.sort_button.configure(state="normal")
        self.render_plan()
        self.update_stats()
        self.status_var.set(f"Done. Moved {moved_count} file(s). Undo log: {manifest_path}")
        messagebox.showinfo(APP_NAME, f"Sorting complete.\n\nMoved {moved_count} file(s).\n\nUndo log saved at:\n{manifest_path}")

    def undo_last_sort(self):
        manifest = self.last_manifest
        if not manifest or not Path(manifest).exists():
            path = filedialog.askopenfilename(
                title="Choose organiser undo log",
                filetypes=[("Organiser logs", "*.json"), ("All files", "*.*")]
            )
            if not path:
                return
            manifest = Path(path)

        try:
            data = json.loads(Path(manifest).read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not read undo log:\n{exc}")
            return

        moves = list(reversed(data.get("moves", [])))
        if not moves:
            messagebox.showinfo(APP_NAME, "This undo log does not contain moved files.")
            return

        answer = messagebox.askyesno(APP_NAME, f"Move {len(moves)} file(s) back to their original locations?")
        if not answer:
            return

        restored = 0
        for move in moves:
            current = Path(move["target"])
            original = unique_target(Path(move["source"]))
            if current.exists() and current.is_file():
                original.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(current), str(original))
                restored += 1
        self.status_var.set(f"Undo complete. Restored {restored} file(s).")
        messagebox.showinfo(APP_NAME, f"Undo complete.\n\nRestored {restored} file(s).")


def main():
    app = FileOrganiserApp()
    app.mainloop()


if __name__ == "__main__":
    main()
