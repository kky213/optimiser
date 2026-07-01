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
from pathlib import Path
from tkinter import ttk

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── Paths ─────────────────────────────────────────────────────────
BASE        = Path(__file__).parent
CHART_PATH  = BASE / "comparison.png"
RESULT_PATH = BASE / "test_report_result.json"
TEST_SCRIPT = BASE / "test_report.py"
PYTHON      = sys.executable

PROXY_URL  = "http://127.0.0.1:8787"
PROXY_CMD  = ["optimiser", "proxy", "--port", "8787"]
PROXY_ENV  = {**os.environ, "HEADROOM_TELEMETRY": "off",
              "HEADROOM_UPDATE_CHECK": "off", "HF_HUB_OFFLINE": "1"}
NO_WINDOW  = 0x08000000  # Windows: suppress console

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
}


# ── Main app ──────────────────────────────────────────────────────
class OptimiserApp:

    def __init__(self, root: tk.Tk):
        self._root = root
        self._root.title("Optimiser — Token Saver")
        self._root.geometry("1160x780")
        self._root.minsize(900, 600)
        self._root.configure(bg=C["bg"])
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        # State
        self._proxy_proc: subprocess.Popen | None = None
        self._proxy_alive = False
        self._stop_event  = threading.Event()
        self._test_running = False

        # Build UI
        self._build_ui()

        # Load chart
        self._load_chart()

        # Load last test result if it exists
        self._try_load_last_result()

        # Start background poller
        t = threading.Thread(target=self._stats_poll_loop, daemon=True)
        t.start()

        # Periodic log flush (every 150 ms)
        self._root.after(150, self._flush_log_tick)

    # ── UI Construction ───────────────────────────────────────────

    def _build_ui(self):
        self._root.rowconfigure(0, weight=0)
        self._root.rowconfigure(1, weight=1)
        self._root.columnconfigure(0, weight=1)

        self._build_header()
        self._build_body()

    def _build_header(self):
        hf = tk.Frame(self._root, bg=C["panel"], pady=10, padx=16)
        hf.grid(row=0, column=0, sticky="ew")
        hf.columnconfigure(1, weight=1)

        # Title
        tk.Label(hf, text="OPTIMISER", font=("Segoe UI", 18, "bold"),
                 bg=C["panel"], fg=C["white"]).grid(row=0, column=0, sticky="w")

        tk.Label(hf, text="Local token compression for Claude / AI tools",
                 font=("Segoe UI", 10), bg=C["panel"],
                 fg=C["grey"]).grid(row=1, column=0, sticky="w")

        # Status
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
        self._status_label.pack(side="left", padx=(0, 16))

        # Buttons
        style = ttk.Style()
        style.configure("Start.TButton", font=("Segoe UI", 10))
        style.configure("Test.TButton",  font=("Segoe UI", 10))

        self._btn_proxy = ttk.Button(hf, text="▶  Start Proxy",
                                      command=self._on_start_proxy, width=16)
        self._btn_proxy.grid(row=0, column=3, rowspan=2, padx=(0, 8))

        self._btn_test = ttk.Button(hf, text="⚡  Run Test",
                                     command=self._on_run_test, width=14)
        self._btn_test.grid(row=0, column=4, rowspan=2)

        # Thin separator
        sep = tk.Frame(self._root, bg=C["border"], height=1)
        sep.grid(row=0, column=0, sticky="ews", pady=(0, 0))

    def _build_body(self):
        body = tk.Frame(self._root, bg=C["bg"])
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)

        self._build_left(body)
        self._build_right(body)

    def _build_left(self, parent):
        lf = tk.Frame(parent, bg=C["bg"])
        lf.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        lf.rowconfigure(2, weight=1)
        lf.columnconfigure(0, weight=1)

        self._build_stats_cards(lf)
        self._build_results_panel(lf)
        self._build_log_panel(lf)

    def _build_stats_cards(self, parent):
        sf = tk.LabelFrame(parent, text=" Live Stats — session ",
                            bg=C["panel"], fg=C["grey"],
                            font=("Segoe UI", 9), bd=1,
                            relief="flat", padx=10, pady=8)
        sf.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        sf.columnconfigure((0, 1, 2, 3), weight=1)

        cards = [
            ("requests",    "Requests",      C["blue"],      "0"),
            ("tokens",      "Tokens Saved",  C["num_green"], "0"),
            ("savings_pct", "Saved %",       C["num_green"], "0%"),
            ("cost",        "Cost Saved",    C["num_green"], "$0.000"),
        ]
        self._stat_vars = {}
        for i, (key, label, color, default) in enumerate(cards):
            card = tk.Frame(sf, bg=C["card"], padx=12, pady=8)
            card.grid(row=0, column=i, sticky="ew", padx=4)
            card.columnconfigure(0, weight=1)
            sf.columnconfigure(i, weight=1)

            var = tk.StringVar(value=default)
            self._stat_vars[key] = var

            tk.Label(card, textvariable=var,
                     font=("Segoe UI", 20, "bold"),
                     bg=C["card"], fg=color).pack(anchor="w")
            tk.Label(card, text=label,
                     font=("Segoe UI", 9),
                     bg=C["card"], fg=C["grey"]).pack(anchor="w")

        # By-model table
        tf = tk.Frame(sf, bg=C["panel"])
        tf.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        tf.columnconfigure(0, weight=1)

        tk.Label(tf, text="By model",
                 font=("Segoe UI", 9), bg=C["panel"],
                 fg=C["grey"]).grid(row=0, column=0, sticky="w", pady=(0, 2))

        cols = ("model", "requests", "compression")
        self._model_tree = ttk.Treeview(tf, columns=cols, show="headings",
                                         height=3, selectmode="none")
        self._model_tree.heading("model",       text="Model")
        self._model_tree.heading("requests",    text="Requests")
        self._model_tree.heading("compression", text="Avg Compression")
        self._model_tree.column("model",       width=260, anchor="w")
        self._model_tree.column("requests",    width=80,  anchor="center")
        self._model_tree.column("compression", width=120, anchor="center")
        self._model_tree.grid(row=1, column=0, sticky="ew")

    def _build_results_panel(self, parent):
        self._results_frame = tk.LabelFrame(
            parent, text=" Last Test Result ",
            bg=C["panel"], fg=C["grey"],
            font=("Segoe UI", 9), bd=1, relief="flat", padx=10, pady=8)
        # Hidden by default
        self._results_frame.columnconfigure(0, weight=1)

        cols = ("task", "direct", "compressed", "saved")
        self._results_tree = ttk.Treeview(
            self._results_frame, columns=cols,
            show="headings", height=5, selectmode="none")
        self._results_tree.heading("task",       text="Task")
        self._results_tree.heading("direct",     text="Direct")
        self._results_tree.heading("compressed", text="Compressed")
        self._results_tree.heading("saved",      text="Saved %")
        self._results_tree.column("task",       width=220, anchor="w")
        self._results_tree.column("direct",     width=90,  anchor="e")
        self._results_tree.column("compressed", width=100, anchor="e")
        self._results_tree.column("saved",      width=80,  anchor="center")
        self._results_tree.grid(row=0, column=0, sticky="ew")

        self._results_summary = tk.Label(
            self._results_frame, text="",
            font=("Segoe UI", 9), bg=C["panel"], fg=C["grey"])
        self._results_summary.grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _build_log_panel(self, parent):
        lf = tk.LabelFrame(parent, text=" Log ",
                            bg=C["panel"], fg=C["grey"],
                            font=("Segoe UI", 9), bd=1, relief="flat")
        lf.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
        lf.rowconfigure(0, weight=1)
        lf.columnconfigure(0, weight=1)
        self._log_lf = lf

        self._log_text = tk.Text(
            lf, state="disabled", wrap="word",
            bg=C["log_bg"], fg=C["log_fg"],
            font=("Consolas", 9), relief="flat",
            padx=8, pady=6, insertbackground=C["white"],
            selectbackground=C["dark_grey"])
        self._log_text.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(lf, orient="vertical",
                           command=self._log_text.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._log_text.configure(yscrollcommand=sb.set)

    def _build_right(self, parent):
        rf = tk.LabelFrame(parent, text=" Benchmark Chart ",
                            bg=C["panel"], fg=C["grey"],
                            font=("Segoe UI", 9), bd=1, relief="flat",
                            width=450, padx=6, pady=6)
        rf.grid(row=0, column=1, sticky="ns")
        rf.pack_propagate(False)
        rf.grid_propagate(False)

        self._chart_label = tk.Label(rf, bg=C["panel"],
                                      text="Chart loading...")
        self._chart_label.pack(fill="both", expand=True)

    # ── Chart loading ─────────────────────────────────────────────

    def _load_chart(self):
        if not PIL_OK:
            self._chart_label.configure(
                text="Install Pillow to see chart\npip install pillow",
                fg=C["grey"])
            return
        if not CHART_PATH.exists():
            self._chart_label.configure(
                text="comparison.png not found\nRun test first",
                fg=C["grey"])
            return
        try:
            img = Image.open(CHART_PATH)
            img = img.resize((436, 278), Image.LANCZOS)
            self._chart_photo = ImageTk.PhotoImage(img)
            self._chart_label.configure(image=self._chart_photo, text="")
        except Exception as e:
            self._chart_label.configure(text=f"Chart error:\n{e}", fg=C["red"])

    # ── Proxy control ─────────────────────────────────────────────

    def _on_start_proxy(self):
        if self._proxy_alive:
            self._on_stop_proxy()
            return
        self.append_log("Starting proxy...")
        self._btn_proxy.configure(text="⏳  Starting...", state="disabled")
        try:
            self._proxy_proc = subprocess.Popen(
                PROXY_CMD, env=PROXY_ENV,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=NO_WINDOW, text=True, bufsize=1)
            t = threading.Thread(target=self._proxy_reader, daemon=True)
            t.start()
        except FileNotFoundError:
            self.append_log("ERROR: 'optimiser' command not found. Run SETUP.bat first.")
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
        self._root.after(0, self.append_log, "Proxy process exited.")
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
        # Belt-and-suspenders: kill by port
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
                with urllib.request.urlopen(
                        f"{PROXY_URL}/stats", timeout=2) as r:
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
            self._stat_vars["requests"].set("—")
            self._stat_vars["tokens"].set("—")
            self._stat_vars["savings_pct"].set("—")
            self._stat_vars["cost"].set("—")
            for row in self._model_tree.get_children():
                self._model_tree.delete(row)
            return

        ds = data.get("display_session", {})
        req     = ds.get("requests", 0)
        saved   = ds.get("tokens_saved", 0)
        pct     = ds.get("savings_percent", 0.0)
        cost_s  = ds.get("compression_savings_usd", 0.0)

        self._stat_vars["requests"].set(f"{req:,}")
        self._stat_vars["tokens"].set(f"{saved:,}")
        self._stat_vars["savings_pct"].set(f"{pct:.1f}%")
        self._stat_vars["cost"].set(f"${cost_s:.4f}")

        # By-model table
        by_model = data.get("requests", {}).get("by_model", {})
        per_model_cost = data.get("cost", {}).get("per_model", {})

        for row in self._model_tree.get_children():
            self._model_tree.delete(row)

        for model, count in by_model.items():
            mc = per_model_cost.get(model, {})
            comp_pct = mc.get("compression_percent", 0)
            short_model = model.split(".")[-1] if "." in model else model
            self._model_tree.insert("", "end",
                values=(short_model, count, f"{comp_pct:.1f}%"))

    def _update_status(self, alive: bool):
        if alive:
            color = C["green"]
            text  = "RUNNING"
            btn   = "■  Stop Proxy"
        else:
            color = C["dark_grey"]
            text  = "STOPPED"
            btn   = "▶  Start Proxy"

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
        self._log_lf.configure(text=" Test Output ")
        self.append_log("─" * 50)
        self.append_log("Running compression test...")
        self.append_log("─" * 50)
        t = threading.Thread(target=self._run_test_thread, daemon=True)
        t.start()

    def _run_test_thread(self):
        env = {**PROXY_ENV}
        try:
            proc = subprocess.Popen(
                [PYTHON, str(TEST_SCRIPT)],
                cwd=str(BASE), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=NO_WINDOW, text=True, bufsize=1)
            for line in proc.stdout:
                clean = line.rstrip()
                if clean and not any(s in clean for s in [
                        "Exception in thread", "Traceback", "UnicodeDecodeError",
                        "charmap", "  File ", "_bootstrap", "_target", "  ~~~"]):
                    self._root.after(0, self.append_log, clean)
            proc.wait()
            self._root.after(0, self._on_test_done, proc.returncode)
        except Exception as e:
            self._root.after(0, self.append_log, f"Test error: {e}")
            self._root.after(0, self._on_test_done, 1)

    def _on_test_done(self, returncode: int):
        self._test_running = False
        self._btn_test.configure(state="normal", text="⚡  Run Test")
        self._log_lf.configure(text=" Log ")
        if returncode == 0:
            self.append_log("✓ Test complete.")
            self._try_load_last_result()
            self._load_chart()   # refresh chart if regenerated
        else:
            self.append_log(f"✗ Test finished with error (code {returncode}).")

    def _try_load_last_result(self):
        if not RESULT_PATH.exists():
            return
        try:
            with open(RESULT_PATH) as f:
                report = json.load(f)
            self._show_results(report)
        except Exception:
            pass

    def _show_results(self, report: dict):
        for row in self._results_tree.get_children():
            self._results_tree.delete(row)

        tests = report.get("tests", [])
        total_d = 0
        total_c = 0

        for t in tests:
            if t.get("direct_error"):
                continue
            d = t["direct_in"]
            c = t.get("proxy_in") or t.get("comp_local_in", d)
            pct = round((d - c) / max(d, 1) * 100, 1)
            total_d += d
            total_c += c
            self._results_tree.insert("", "end", values=(
                t["name"],
                f"{d:,}",
                f"{c:,}",
                f"{pct:.1f}%"
            ))

        if total_d:
            tot_pct = round((total_d - total_c) / total_d * 100, 1)
            self._results_tree.insert("", "end", values=(
                "TOTAL",
                f"{total_d:,}",
                f"{total_c:,}",
                f"{tot_pct:.1f}%"
            ), tags=("total",))
            self._results_tree.tag_configure("total",
                                              font=("Segoe UI", 9, "bold"))

        s = report.get("summary", {})
        cost_d = s.get("input_cost_direct_usd", 0)
        cost_c = s.get("input_cost_with_optimiser_usd", 0)
        cost_s = s.get("input_cost_saved_usd", 0)
        self._results_summary.configure(
            text=f"Cost  without: ${cost_d:.5f}   with: ${cost_c:.5f}"
                 f"   saved: ${cost_s:.5f}   model: {report.get('model','')}")

        # Show the results panel (was hidden)
        self._results_frame.grid(row=1, column=0, sticky="ew",
                                  pady=(0, 6))

    # ── Log ───────────────────────────────────────────────────────

    def append_log(self, line: str):
        # Always called on main thread via root.after(0, ...) from bg threads
        ts = time.strftime("%H:%M:%S")
        txt = self._log_text
        txt.configure(state="normal")
        at_bottom = txt.yview()[1] >= 0.98
        txt.insert("end", f"[{ts}]  {line}\n")
        if at_bottom:
            txt.see("end")
        txt.configure(state="disabled")

    def _flush_log_tick(self):
        # Kept for compatibility but log is written directly in append_log
        if not self._stop_event.is_set():
            self._root.after(500, self._flush_log_tick)

    def _flush_log(self):
        pass  # no-op — log written directly in append_log

    # ── Lifecycle ─────────────────────────────────────────────────

    def _on_close(self):
        self._stop_event.set()
        if self._proxy_proc:
            self._terminate_proxy()
        self._root.destroy()


# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()

    # Dark titlebar on Windows 11
    try:
        root.update()
        import ctypes
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.windll.user32.GetForegroundWindow(),
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1)),
            ctypes.sizeof(ctypes.c_int))
    except Exception:
        pass

    app = OptimiserApp(root)
    root.mainloop()
