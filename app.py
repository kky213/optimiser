"""
Optimiser Desktop App
Local token compression dashboard for Claude / AI coding tools.
Run: python app.py
"""

import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from tkinter import ttk

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── Paths ─────────────────────────────────────────────────────────
BASE         = Path(__file__).parent
CHART_PATH   = BASE / "comparison.png"
RESULT_PATH  = BASE / "test_report_result.json"
TEST_SCRIPT  = BASE / "test_report.py"
PYTHON       = sys.executable

# Proxy saves lifetime data here automatically
SAVINGS_PATH = Path.home() / ".headroom" / "proxy_savings.json"
# App saves its own session history here
APP_DATA     = BASE / "app_data.json"

PROXY_URL  = "http://127.0.0.1:8787"
PROXY_CMD  = ["optimiser", "proxy", "--port", "8787"]
PROXY_ENV  = {**os.environ, "HEADROOM_TELEMETRY": "off",
              "HEADROOM_UPDATE_CHECK": "off", "HF_HUB_OFFLINE": "1"}
NO_WINDOW  = 0x08000000  # Windows: suppress console popup

# ── Colours ───────────────────────────────────────────────────────
C = {
    "bg":        "#0f1117",
    "panel":     "#1a1d27",
    "card":      "#1e2130",
    "border":    "#2a2d3e",
    "green":     "#22c55e",
    "red":       "#ef4444",
    "amber":     "#f59e0b",
    "blue":      "#6366f1",
    "white":     "#f1f5f9",
    "grey":      "#94a3b8",
    "dark_grey": "#334155",
    "log_bg":    "#0d1117",
    "log_fg":    "#c9d1d9",
    "num_green": "#4ade80",
    "num_white": "#f8fafc",
    "tab_bg":    "#161b22",
}


# ── App data helpers ──────────────────────────────────────────────

def load_app_data() -> dict:
    try:
        if APP_DATA.exists():
            return json.loads(APP_DATA.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"sessions": [], "total_runs": 0}


def save_app_data(data: dict):
    try:
        APP_DATA.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_lifetime_savings() -> dict:
    """Read proxy's own persistence file for lifetime totals."""
    try:
        if SAVINGS_PATH.exists():
            d = json.loads(SAVINGS_PATH.read_text(encoding="utf-8"))
            return d.get("lifetime", {})
    except Exception:
        pass
    return {}


# ── Main app ──────────────────────────────────────────────────────
class OptimiserApp:

    def __init__(self, root: tk.Tk):
        self._root = root
        self._root.title("Optimiser — Token Saver")
        self._root.geometry("1200x820")
        self._root.minsize(960, 640)
        self._root.configure(bg=C["bg"])
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        # State
        self._proxy_proc: subprocess.Popen | None = None
        self._proxy_alive   = False
        self._stop_event    = threading.Event()
        self._test_running  = False
        self._session_start = time.time()
        self._app_data      = load_app_data()

        # Build UI
        self._build_ui()
        self._load_chart()
        self._try_load_last_result()
        self._load_history_tab()

        # Background stats poller
        threading.Thread(target=self._stats_poll_loop, daemon=True).start()

        # Startup log
        self.append_log("Optimiser started. Click  ▶ Start Proxy  to begin.")
        self.append_log(f"Data saved to: {APP_DATA}")
        self.append_log(f"Proxy savings file: {SAVINGS_PATH}")

    # ── UI Construction ───────────────────────────────────────────

    def _build_ui(self):
        self._root.rowconfigure(0, weight=0)
        self._root.rowconfigure(1, weight=0)
        self._root.rowconfigure(2, weight=1)
        self._root.columnconfigure(0, weight=1)

        self._build_header()
        self._build_tabs()

    def _build_header(self):
        hf = tk.Frame(self._root, bg=C["panel"], pady=10, padx=16)
        hf.grid(row=0, column=0, sticky="ew")
        hf.columnconfigure(1, weight=1)

        tk.Label(hf, text="OPTIMISER",
                 font=("Segoe UI", 18, "bold"),
                 bg=C["panel"], fg=C["white"]).grid(row=0, column=0, sticky="w")

        tk.Label(hf, text="Local token compression — no telemetry, no external servers",
                 font=("Segoe UI", 10),
                 bg=C["panel"], fg=C["grey"]).grid(row=1, column=0, sticky="w")

        # Status dot + label
        sf = tk.Frame(hf, bg=C["panel"])
        sf.grid(row=0, column=2, rowspan=2, sticky="e", padx=(0, 12))

        self._status_canvas = tk.Canvas(sf, width=14, height=14,
                                         bg=C["panel"], highlightthickness=0)
        self._status_canvas.pack(side="left", padx=(0, 6))
        self._status_oval = self._status_canvas.create_oval(
            2, 2, 12, 12, fill=C["dark_grey"], outline="")

        self._status_label = tk.Label(sf, text="STOPPED",
                                       font=("Segoe UI", 10, "bold"),
                                       bg=C["panel"], fg=C["grey"])
        self._status_label.pack(side="left", padx=(0, 20))

        # Buttons
        self._btn_proxy = ttk.Button(hf, text="▶  Start Proxy",
                                      command=self._on_start_proxy, width=16)
        self._btn_proxy.grid(row=0, column=3, rowspan=2, padx=(0, 8))

        self._btn_test = ttk.Button(hf, text="⚡  Run Test",
                                     command=self._on_run_test, width=14)
        self._btn_test.grid(row=0, column=4, rowspan=2, padx=(0, 8))

        # Lifetime summary in header
        lf = tk.Frame(hf, bg=C["panel"])
        lf.grid(row=0, column=5, rowspan=2, sticky="e", padx=(8, 0))

        lt = load_lifetime_savings()
        lt_tok  = lt.get("tokens_saved", 0)
        lt_cost = lt.get("compression_savings_usd", 0.0)

        self._lt_tokens_var = tk.StringVar(value=f"{lt_tok:,}")
        self._lt_cost_var   = tk.StringVar(value=f"${lt_cost:.3f}")

        tk.Label(lf, text="ALL-TIME SAVED",
                 font=("Segoe UI", 8), bg=C["panel"],
                 fg=C["grey"]).grid(row=0, column=0, columnspan=4, sticky="w")

        tk.Label(lf, textvariable=self._lt_tokens_var,
                 font=("Segoe UI", 13, "bold"),
                 bg=C["panel"], fg=C["num_green"]).grid(row=1, column=0, sticky="w")
        tk.Label(lf, text=" tokens  ",
                 font=("Segoe UI", 9), bg=C["panel"],
                 fg=C["grey"]).grid(row=1, column=1, sticky="w")
        tk.Label(lf, textvariable=self._lt_cost_var,
                 font=("Segoe UI", 13, "bold"),
                 bg=C["panel"], fg=C["amber"]).grid(row=1, column=2, sticky="w")
        tk.Label(lf, text=" cost saved",
                 font=("Segoe UI", 9), bg=C["panel"],
                 fg=C["grey"]).grid(row=1, column=3, sticky="w")

        # Separator
        tk.Frame(self._root, bg=C["border"], height=1).grid(
            row=1, column=0, sticky="ew")

    def _build_tabs(self):
        nb = ttk.Notebook(self._root)
        nb.grid(row=2, column=0, sticky="nsew", padx=8, pady=6)
        self._nb = nb

        # Tab 1 — Dashboard
        dash = tk.Frame(nb, bg=C["bg"])
        dash.rowconfigure(0, weight=1)
        dash.columnconfigure(0, weight=1)
        dash.columnconfigure(1, weight=0)
        nb.add(dash, text="  Dashboard  ")
        self._build_dashboard(dash)

        # Tab 2 — History
        hist = tk.Frame(nb, bg=C["bg"])
        hist.rowconfigure(0, weight=1)
        hist.columnconfigure(0, weight=1)
        nb.add(hist, text="  History  ")
        self._build_history_tab(hist)

        # Tab 3 — Log
        log_tab = tk.Frame(nb, bg=C["bg"])
        log_tab.rowconfigure(0, weight=1)
        log_tab.columnconfigure(0, weight=1)
        nb.add(log_tab, text="  Log  ")
        self._build_log_panel(log_tab)

    # ── Dashboard tab ─────────────────────────────────────────────

    def _build_dashboard(self, parent):
        parent.rowconfigure(0, weight=0)
        parent.rowconfigure(1, weight=1)

        self._build_stats_cards(parent)

        bottom = tk.Frame(parent, bg=C["bg"])
        bottom.grid(row=1, column=0, columnspan=2, sticky="nsew")
        bottom.rowconfigure(0, weight=1)
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=0)

        self._build_results_panel(bottom)
        self._build_chart_panel(bottom)

    def _build_stats_cards(self, parent):
        sf = tk.LabelFrame(parent, text=" Live Stats — current session ",
                            bg=C["panel"], fg=C["grey"],
                            font=("Segoe UI", 9), bd=1,
                            relief="flat", padx=10, pady=8)
        sf.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 6))
        sf.columnconfigure((0, 1, 2, 3), weight=1)

        cards = [
            ("requests",    "Requests",      C["blue"],      "—"),
            ("tokens",      "Tokens Saved",  C["num_green"], "—"),
            ("savings_pct", "Saved %",       C["num_green"], "—"),
            ("cost",        "Cost Saved",    C["amber"],     "—"),
        ]
        self._stat_vars = {}
        for i, (key, label, color, default) in enumerate(cards):
            card = tk.Frame(sf, bg=C["card"], padx=14, pady=10)
            card.grid(row=0, column=i, sticky="ew", padx=5)
            sf.columnconfigure(i, weight=1)

            var = tk.StringVar(value=default)
            self._stat_vars[key] = var

            tk.Label(card, textvariable=var,
                     font=("Segoe UI", 22, "bold"),
                     bg=C["card"], fg=color).pack(anchor="w")
            tk.Label(card, text=label,
                     font=("Segoe UI", 9),
                     bg=C["card"], fg=C["grey"]).pack(anchor="w")

        # By-model mini table
        tf = tk.Frame(sf, bg=C["panel"])
        tf.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 2))
        tf.columnconfigure(0, weight=1)

        tk.Label(tf, text="By model",
                 font=("Segoe UI", 9), bg=C["panel"],
                 fg=C["grey"]).grid(row=0, column=0, sticky="w", pady=(0, 2))

        self._model_tree = ttk.Treeview(
            tf, columns=("model", "requests", "compression"),
            show="headings", height=3, selectmode="none")
        self._model_tree.heading("model",       text="Model")
        self._model_tree.heading("requests",    text="Requests")
        self._model_tree.heading("compression", text="Avg Compression")
        self._model_tree.column("model",       width=280, anchor="w")
        self._model_tree.column("requests",    width=90,  anchor="center")
        self._model_tree.column("compression", width=130, anchor="center")
        self._model_tree.grid(row=1, column=0, sticky="ew")

    def _build_results_panel(self, parent):
        rf = tk.LabelFrame(parent, text=" Last Test Result ",
                            bg=C["panel"], fg=C["grey"],
                            font=("Segoe UI", 9), bd=1,
                            relief="flat", padx=10, pady=8)
        rf.grid(row=0, column=0, sticky="nsew", padx=(4, 4), pady=4)
        rf.rowconfigure(0, weight=1)
        rf.columnconfigure(0, weight=1)

        cols = ("task", "direct", "compressed", "saved")
        self._results_tree = ttk.Treeview(
            rf, columns=cols, show="headings",
            height=6, selectmode="none")
        self._results_tree.heading("task",       text="Task")
        self._results_tree.heading("direct",     text="Without")
        self._results_tree.heading("compressed", text="With Optimiser")
        self._results_tree.heading("saved",      text="Saved %")
        self._results_tree.column("task",        width=230, anchor="w")
        self._results_tree.column("direct",      width=100, anchor="e")
        self._results_tree.column("compressed",  width=120, anchor="e")
        self._results_tree.column("saved",       width=90,  anchor="center")
        self._results_tree.grid(row=0, column=0, sticky="nsew")

        self._results_summary = tk.Label(
            rf, text="No test run yet — click ⚡ Run Test",
            font=("Segoe UI", 9), bg=C["panel"], fg=C["grey"])
        self._results_summary.grid(row=1, column=0, sticky="w", pady=(6, 0))

    def _build_chart_panel(self, parent):
        cf = tk.LabelFrame(parent, text=" Benchmark Chart ",
                            bg=C["panel"], fg=C["grey"],
                            font=("Segoe UI", 9), bd=1,
                            relief="flat", width=460, padx=6, pady=6)
        cf.grid(row=0, column=1, sticky="nsew", padx=(0, 4), pady=4)
        cf.pack_propagate(False)
        cf.grid_propagate(False)

        self._chart_label = tk.Label(cf, bg=C["panel"],
                                      text="Chart loading...",
                                      fg=C["grey"])
        self._chart_label.pack(fill="both", expand=True)

    # ── History tab ───────────────────────────────────────────────

    def _build_history_tab(self, parent):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        # Summary row at top
        sf = tk.Frame(parent, bg=C["panel"], padx=16, pady=10)
        sf.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        sf.columnconfigure((0, 1, 2, 3), weight=1)

        self._hist_summary_vars = {}
        for i, (key, label, color) in enumerate([
            ("total_sessions", "Total Sessions",  C["blue"]),
            ("total_requests", "Total Requests",  C["num_green"]),
            ("total_tokens",   "Tokens Saved",    C["num_green"]),
            ("total_cost",     "Cost Saved",       C["amber"]),
        ]):
            f = tk.Frame(sf, bg=C["card"], padx=12, pady=8)
            f.grid(row=0, column=i, sticky="ew", padx=5)
            sf.columnconfigure(i, weight=1)
            var = tk.StringVar(value="—")
            self._hist_summary_vars[key] = var
            tk.Label(f, textvariable=var,
                     font=("Segoe UI", 18, "bold"),
                     bg=C["card"], fg=color).pack(anchor="w")
            tk.Label(f, text=label,
                     font=("Segoe UI", 9),
                     bg=C["card"], fg=C["grey"]).pack(anchor="w")

        # Session history table
        hf = tk.LabelFrame(parent, text=" Session History ",
                            bg=C["panel"], fg=C["grey"],
                            font=("Segoe UI", 9), bd=1, relief="flat")
        hf.grid(row=1, column=0, sticky="nsew", padx=4, pady=6)
        hf.rowconfigure(0, weight=1)
        hf.columnconfigure(0, weight=1)

        cols = ("date", "duration", "requests", "tokens_saved", "savings_pct", "cost_saved")
        self._hist_tree = ttk.Treeview(
            hf, columns=cols, show="headings", selectmode="none")
        self._hist_tree.heading("date",        text="Date / Time")
        self._hist_tree.heading("duration",    text="Duration")
        self._hist_tree.heading("requests",    text="Requests")
        self._hist_tree.heading("tokens_saved",text="Tokens Saved")
        self._hist_tree.heading("savings_pct", text="Saved %")
        self._hist_tree.heading("cost_saved",  text="Cost Saved")
        self._hist_tree.column("date",        width=160, anchor="w")
        self._hist_tree.column("duration",    width=90,  anchor="center")
        self._hist_tree.column("requests",    width=90,  anchor="center")
        self._hist_tree.column("tokens_saved",width=120, anchor="e")
        self._hist_tree.column("savings_pct", width=90,  anchor="center")
        self._hist_tree.column("cost_saved",  width=100, anchor="e")
        self._hist_tree.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(hf, orient="vertical",
                           command=self._hist_tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._hist_tree.configure(yscrollcommand=sb.set)

        # Clear history button
        bf = tk.Frame(parent, bg=C["bg"])
        bf.grid(row=2, column=0, sticky="e", padx=8, pady=(0, 4))
        ttk.Button(bf, text="Clear History",
                   command=self._clear_history).pack(side="right")

        self._hist_tree_ref = self._hist_tree  # save reference

    def _load_history_tab(self):
        """Populate history tab from saved app_data + proxy lifetime file."""
        data     = self._app_data
        sessions = data.get("sessions", [])

        # Also pull lifetime from proxy savings file
        lt = load_lifetime_savings()
        lt_tok  = lt.get("tokens_saved", 0)
        lt_cost = lt.get("compression_savings_usd", 0.0)
        lt_req  = lt.get("requests", 0)

        # Update header lifetime vars
        self._lt_tokens_var.set(f"{lt_tok:,}")
        self._lt_cost_var.set(f"${lt_cost:.3f}")

        # Update history summary cards
        n = len(sessions)
        tot_req  = sum(s.get("requests", 0) for s in sessions)
        tot_tok  = sum(s.get("tokens_saved", 0) for s in sessions)
        tot_cost = sum(s.get("cost_saved", 0.0) for s in sessions)

        self._hist_summary_vars["total_sessions"].set(str(n))
        self._hist_summary_vars["total_requests"].set(f"{tot_req:,}")
        self._hist_summary_vars["total_tokens"].set(f"{tot_tok:,}")
        self._hist_summary_vars["total_cost"].set(f"${tot_cost:.4f}")

        # Populate session rows (newest first)
        for row in self._hist_tree.get_children():
            self._hist_tree.delete(row)

        for s in reversed(sessions):
            dur  = s.get("duration_s", 0)
            mins = dur // 60
            secs = dur % 60
            self._hist_tree.insert("", "end", values=(
                s.get("started_at", ""),
                f"{mins}m {secs:02d}s",
                s.get("requests", 0),
                f"{s.get('tokens_saved', 0):,}",
                f"{s.get('savings_pct', 0):.1f}%",
                f"${s.get('cost_saved', 0.0):.5f}",
            ))

    def _clear_history(self):
        self._app_data["sessions"] = []
        self._app_data["total_runs"] = 0
        save_app_data(self._app_data)
        self._load_history_tab()
        self.append_log("History cleared.")

    # ── Log tab ───────────────────────────────────────────────────

    def _build_log_panel(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        lf = tk.Frame(parent, bg=C["panel"])
        lf.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)

        self._log_text = tk.Text(
            lf, state="disabled", wrap="word",
            bg=C["log_bg"], fg=C["log_fg"],
            font=("Consolas", 9), relief="flat",
            padx=10, pady=8,
            insertbackground=C["white"],
            selectbackground=C["dark_grey"])
        self._log_text.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(lf, orient="vertical",
                           command=self._log_text.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._log_text.configure(yscrollcommand=sb.set)

        # Clear log button
        ttk.Button(parent, text="Clear Log",
                   command=self._clear_log).grid(
            row=1, column=0, sticky="e", padx=8, pady=(0, 4))

    def _clear_log(self):
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

    # ── Chart ─────────────────────────────────────────────────────

    def _load_chart(self):
        if not PIL_OK:
            self._chart_label.configure(
                text="pip install pillow\nto see chart", fg=C["grey"])
            return
        if not CHART_PATH.exists():
            self._chart_label.configure(
                text="Run ⚡ Test first\nto generate chart", fg=C["grey"])
            return
        try:
            img = Image.open(CHART_PATH)
            img = img.resize((444, 283), Image.LANCZOS)
            self._chart_photo = ImageTk.PhotoImage(img)
            self._chart_label.configure(image=self._chart_photo, text="")
        except Exception as e:
            self._chart_label.configure(text=f"Chart error:\n{e}", fg=C["red"])

    # ── Proxy control ─────────────────────────────────────────────

    def _on_start_proxy(self):
        if self._proxy_alive:
            self._on_stop_proxy()
            return
        self.append_log("Starting proxy on port 8787...")
        self._btn_proxy.configure(text="⏳  Starting...", state="disabled")
        try:
            self._proxy_proc = subprocess.Popen(
                PROXY_CMD, env=PROXY_ENV,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=NO_WINDOW, text=True, bufsize=1)
            threading.Thread(target=self._proxy_reader, daemon=True).start()
        except FileNotFoundError:
            self.append_log("ERROR: 'optimiser' not found. Run SETUP.bat first.")
            self._btn_proxy.configure(text="▶  Start Proxy", state="normal")

    def _on_stop_proxy(self):
        self.append_log("Stopping proxy...")
        self._terminate_proxy()

    def _proxy_reader(self):
        proc = self._proxy_proc
        if not proc:
            return
        for line in proc.stdout:
            self._root.after(0, self.append_log, line.rstrip())
        proc.wait()
        self._root.after(0, self.append_log, "Proxy stopped.")
        self._proxy_proc = None

    def _terminate_proxy(self):
        if self._proxy_proc:
            try:
                self._proxy_proc.terminate()
                self._proxy_proc.wait(timeout=3)
            except Exception:
                try:
                    self._proxy_proc.kill()
                except Exception:
                    pass
            self._proxy_proc = None
        try:
            subprocess.run(
                'for /f "tokens=5" %p in (\'netstat -aon ^| findstr ":8787 "\') '
                'do taskkill /PID %p /F',
                shell=True, capture_output=True)
        except Exception:
            pass

    # ── Stats polling ─────────────────────────────────────────────

    def _stats_poll_loop(self):
        while not self._stop_event.is_set():
            try:
                with urllib.request.urlopen(f"{PROXY_URL}/stats", timeout=2) as r:
                    data = json.loads(r.read())
                self._root.after(0, self._update_stats_ui, data)
            except Exception:
                self._root.after(0, self._update_stats_ui, None)
            self._stop_event.wait(2.0)

    def _update_stats_ui(self, data):
        alive = data is not None
        if alive != self._proxy_alive:
            self._proxy_alive = alive
            self._update_status(alive)

        if not alive:
            for k in ("requests", "tokens", "savings_pct", "cost"):
                self._stat_vars[k].set("—")
            for row in self._model_tree.get_children():
                self._model_tree.delete(row)
            return

        ds      = data.get("display_session", {})
        req     = ds.get("requests", 0)
        saved   = ds.get("tokens_saved", 0)
        pct     = ds.get("savings_percent", 0.0)
        cost_s  = ds.get("compression_savings_usd", 0.0)

        self._stat_vars["requests"].set(f"{req:,}")
        self._stat_vars["tokens"].set(f"{saved:,}")
        self._stat_vars["savings_pct"].set(f"{pct:.1f}%")
        self._stat_vars["cost"].set(f"${cost_s:.4f}")

        # Update lifetime header from proxy savings file
        lt = load_lifetime_savings()
        self._lt_tokens_var.set(f"{lt.get('tokens_saved', 0):,}")
        self._lt_cost_var.set(f"${lt.get('compression_savings_usd', 0.0):.3f}")

        # By-model table
        by_model       = data.get("requests", {}).get("by_model", {})
        per_model_cost = data.get("cost", {}).get("per_model", {})

        for row in self._model_tree.get_children():
            self._model_tree.delete(row)
        for model, count in by_model.items():
            mc = per_model_cost.get(model, {})
            cp = mc.get("compression_percent", 0)
            short = model.split(".")[-1] if "." in model else model
            self._model_tree.insert("", "end",
                values=(short, count, f"{cp:.1f}%"))

    def _update_status(self, alive: bool):
        color = C["green"]   if alive else C["dark_grey"]
        text  = "RUNNING"    if alive else "STOPPED"
        btn   = "■  Stop Proxy" if alive else "▶  Start Proxy"
        self._status_canvas.itemconfig(self._status_oval, fill=color)
        self._status_label.configure(text=text,
                                      fg=color if alive else C["grey"])
        self._btn_proxy.configure(text=btn, state="normal")

    # ── Test runner ───────────────────────────────────────────────

    def _on_run_test(self):
        if self._test_running:
            return
        self._test_running = True
        self._btn_test.configure(state="disabled", text="⏳  Running...")
        # Switch to log tab to show output
        self._nb.select(2)
        self.append_log("─" * 52)
        self.append_log("Starting compression test...")
        self.append_log("─" * 52)
        threading.Thread(target=self._run_test_thread, daemon=True).start()

    def _run_test_thread(self):
        try:
            proc = subprocess.Popen(
                [PYTHON, str(TEST_SCRIPT)],
                cwd=str(BASE), env=PROXY_ENV,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=NO_WINDOW, text=True, bufsize=1)
            skip = {"Exception in thread", "Traceback", "UnicodeDecodeError",
                    "charmap", "  File ", "_bootstrap", "_target", "  ~~~",
                    "  ^^^"}
            for line in proc.stdout:
                clean = line.rstrip()
                if clean and not any(s in clean for s in skip):
                    self._root.after(0, self.append_log, clean)
            proc.wait()
            self._root.after(0, self._on_test_done, proc.returncode)
        except Exception as e:
            self._root.after(0, self.append_log, f"Test error: {e}")
            self._root.after(0, self._on_test_done, 1)

    def _on_test_done(self, returncode: int):
        self._test_running = False
        self._btn_test.configure(state="normal", text="⚡  Run Test")
        if returncode == 0:
            self.append_log("✓ Test complete.")
            self._try_load_last_result()
            self._load_chart()
            self._nb.select(0)  # switch back to dashboard
        else:
            self.append_log(f"✗ Test error (code {returncode}).")

    def _try_load_last_result(self):
        if not RESULT_PATH.exists():
            return
        try:
            with open(RESULT_PATH, encoding="utf-8") as f:
                self._show_results(json.load(f))
        except Exception:
            pass

    def _show_results(self, report: dict):
        for row in self._results_tree.get_children():
            self._results_tree.delete(row)

        tests   = report.get("tests", [])
        total_d = total_c = 0

        for t in tests:
            if t.get("direct_error"):
                continue
            d   = t["direct_in"]
            c   = t.get("proxy_in") or t.get("comp_local_in", d)
            pct = round((d - c) / max(d, 1) * 100, 1)
            total_d += d
            total_c += c
            self._results_tree.insert("", "end",
                values=(t["name"], f"{d:,}", f"{c:,}", f"{pct:.1f}%"))

        if total_d:
            tot_pct = round((total_d - total_c) / total_d * 100, 1)
            self._results_tree.insert("", "end",
                values=("TOTAL", f"{total_d:,}", f"{total_c:,}", f"{tot_pct:.1f}%"),
                tags=("total",))
            self._results_tree.tag_configure("total",
                font=("Segoe UI", 9, "bold"))

        s       = report.get("summary", {})
        cost_d  = s.get("input_cost_direct_usd", 0)
        cost_c  = s.get("input_cost_with_optimiser_usd", 0)
        cost_sv = s.get("input_cost_saved_usd", 0)
        self._results_summary.configure(
            text=f"Without: ${cost_d:.5f}  →  With: ${cost_c:.5f}  "
                 f"=  Saved: ${cost_sv:.5f}   [{report.get('model','')}]")

    # ── Log ───────────────────────────────────────────────────────

    def append_log(self, line: str):
        ts  = time.strftime("%H:%M:%S")
        txt = self._log_text
        txt.configure(state="normal")
        at_bottom = txt.yview()[1] >= 0.98
        txt.insert("end", f"[{ts}]  {line}\n")
        if at_bottom:
            txt.see("end")
        txt.configure(state="disabled")

    # ── Save session on close ────────────────────────────────────

    def _save_session(self):
        """Save this session's stats to app_data.json."""
        if not self._proxy_alive:
            return  # nothing to save if proxy never ran

        try:
            with urllib.request.urlopen(f"{PROXY_URL}/stats", timeout=2) as r:
                data = json.loads(r.read())
        except Exception:
            return

        ds       = data.get("display_session", {})
        req      = ds.get("requests", 0)
        tok      = ds.get("tokens_saved", 0)
        pct      = ds.get("savings_percent", 0.0)
        cost     = ds.get("compression_savings_usd", 0.0)
        duration = int(time.time() - self._session_start)

        if req == 0:
            return  # nothing happened this session

        session = {
            "started_at":   datetime.fromtimestamp(self._session_start)
                            .strftime("%Y-%m-%d %H:%M"),
            "duration_s":   duration,
            "requests":     req,
            "tokens_saved": tok,
            "savings_pct":  pct,
            "cost_saved":   cost,
        }

        self._app_data.setdefault("sessions", []).append(session)
        self._app_data["total_runs"] = self._app_data.get("total_runs", 0) + 1
        save_app_data(self._app_data)

    # ── Lifecycle ─────────────────────────────────────────────────

    def _on_close(self):
        self._save_session()
        self._stop_event.set()
        if self._proxy_proc:
            self._terminate_proxy()
        self._root.destroy()


# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()

    try:
        root.update()
        import ctypes
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.windll.user32.GetForegroundWindow(),
            20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int))
    except Exception:
        pass

    app = OptimiserApp(root)
    root.mainloop()
