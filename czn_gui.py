from __future__ import annotations

import queue
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from czn_detector import DEFAULT_GAME_WINDOW_TITLE, list_visible_windows


APP_DIR = Path(__file__).resolve().parent
STOP_FILE = APP_DIR / "STOP"

BG = "#f4f7fb"
PANEL = "#ffffff"
INK = "#182230"
MUTED = "#667085"
LINE = "#d9e2ef"
BLUE = "#2563eb"
BLUE_DARK = "#1d4ed8"
RED = "#dc2626"
GREEN = "#16a34a"
LOG_BG = "#101828"
LOG_FG = "#d0d5dd"


def detector_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, str(APP_DIR / "czn_detector.py")]


class CznAutoGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CZN Auto")
        self.geometry("1040x680")
        self.minsize(900, 600)
        self.configure(bg=BG)

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.windows: list[dict[str, object]] = []

        self.window_var = tk.StringVar()
        self.capture_var = tk.StringVar(value="printwindow")
        self.click_method_var = tk.StringVar(value="postmessage")
        self.restore_after_click_var = tk.BooleanVar(value=True)
        self.postmessage_fallback_var = tk.BooleanVar(value=False)
        self.act_var = tk.BooleanVar(value=True)
        self.advance_unknown_var = tk.BooleanVar(value=False)
        self.fast_start_var = tk.BooleanVar(value=False)
        self.max_clicks_var = tk.StringVar(value="0")
        self.max_seconds_var = tk.StringVar(value="0")
        self.status_var = tk.StringVar(value="就绪")
        self.window_count_var = tk.StringVar(value="0 个窗口")

        self._configure_style()
        self._build_ui()
        self.refresh_windows()
        self.after(100, self._drain_output)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Microsoft YaHei UI", 10), background=BG, foreground=INK)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("Title.TLabel", background=BG, foreground=INK, font=("Microsoft YaHei UI", 22, "bold"))
        style.configure("Subtle.TLabel", background=BG, foreground=MUTED)
        style.configure("PanelTitle.TLabel", background=PANEL, foreground=INK, font=("Microsoft YaHei UI", 12, "bold"))
        style.configure("PanelText.TLabel", background=PANEL, foreground=MUTED)
        style.configure("Status.TLabel", background=PANEL, foreground=GREEN, font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("TCheckbutton", background=PANEL, foreground=INK)
        style.map("TCheckbutton", background=[("active", PANEL)])
        style.configure("TCombobox", fieldbackground="#f8fafc", background="#f8fafc", foreground=INK, bordercolor=LINE)
        style.configure("TEntry", fieldbackground="#f8fafc", bordercolor=LINE, foreground=INK)

    def _build_ui(self) -> None:
        shell = ttk.Frame(self, padding=18)
        shell.pack(fill=tk.BOTH, expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(2, weight=1)

        header = ttk.Frame(shell)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="CZN Auto", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="自动识别与点击控制台", style="Subtle.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.status_chip = tk.Label(
            header,
            textvariable=self.status_var,
            bg="#dcfce7",
            fg="#166534",
            padx=14,
            pady=7,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        self.status_chip.grid(row=0, column=1, rowspan=2, sticky="e")

        controls = ttk.Frame(shell)
        controls.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        controls.columnconfigure(0, weight=3)
        controls.columnconfigure(1, weight=2)
        controls.columnconfigure(2, weight=2)

        target = self._panel(controls, "目标窗口")
        target.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        target.columnconfigure(0, weight=1)
        self.window_combo = ttk.Combobox(target, textvariable=self.window_var, state="readonly")
        self.window_combo.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        target_actions = ttk.Frame(target, style="Panel.TFrame")
        target_actions.grid(row=2, column=0, sticky="ew")
        target_actions.columnconfigure(1, weight=1)
        self._text_button(target_actions, "刷新窗口", self.refresh_windows, bg="#eef4ff", fg=BLUE).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(target_actions, textvariable=self.window_count_var, style="PanelText.TLabel").grid(
            row=0, column=1, sticky="e"
        )

        runtime = self._panel(controls, "运行模式")
        runtime.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        runtime.columnconfigure(1, weight=1)
        ttk.Label(runtime, text="截图", style="PanelText.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 8))
        ttk.Combobox(
            runtime,
            textvariable=self.capture_var,
            values=("printwindow", "mss", "dxgi"),
            state="readonly",
            width=12,
        ).grid(
            row=1, column=1, sticky="ew", pady=(10, 8)
        )
        ttk.Label(runtime, text="点击", style="PanelText.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 8))
        ttk.Combobox(
            runtime,
            textvariable=self.click_method_var,
            values=("postmessage", "sendinput"),
            state="readonly",
            width=12,
        ).grid(row=2, column=1, sticky="ew", pady=(0, 8))
        ttk.Checkbutton(runtime, text="实际点击", variable=self.act_var).grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(runtime, text="点击后还原", variable=self.restore_after_click_var).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )
        ttk.Checkbutton(runtime, text="失败真实点击", variable=self.postmessage_fallback_var).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        limits = self._panel(controls, "保护设置")
        limits.grid(row=0, column=2, sticky="nsew")
        limits.columnconfigure(1, weight=1)
        ttk.Label(limits, text="最多点击", style="PanelText.TLabel").grid(row=1, column=0, sticky="w", pady=(10, 8))
        ttk.Entry(limits, textvariable=self.max_clicks_var, width=8).grid(row=1, column=1, sticky="ew", pady=(10, 8))
        ttk.Label(limits, text="最多秒数", style="PanelText.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(limits, textvariable=self.max_seconds_var, width=8).grid(row=2, column=1, sticky="ew", pady=(0, 8))
        ttk.Checkbutton(limits, text="未知画面推进", variable=self.advance_unknown_var).grid(
            row=3, column=0, columnspan=2, sticky="w"
        )
        ttk.Checkbutton(limits, text="快速进队伍", variable=self.fast_start_var).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        main_area = ttk.Frame(shell)
        main_area.grid(row=2, column=0, sticky="nsew")
        main_area.columnconfigure(0, weight=1)
        main_area.rowconfigure(1, weight=1)

        actions = ttk.Frame(main_area)
        actions.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        actions.columnconfigure(5, weight=1)
        self.start_button = self._text_button(actions, "开始运行", self.start_live, bg=BLUE, fg="#ffffff", active=BLUE_DARK)
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        self.stop_button = self._text_button(actions, "停止", self.stop_live, bg="#fee2e2", fg=RED)
        self.stop_button.configure(state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        self._text_button(actions, "状态检查", self.state_check, bg="#e0f2fe", fg="#0369a1").grid(
            row=0, column=2, padx=(0, 10)
        )
        self._text_button(actions, "打开配置", self.open_config, bg="#f1f5f9", fg=INK).grid(row=0, column=3)

        log_panel = ttk.Frame(main_area, style="Panel.TFrame", padding=12)
        log_panel.grid(row=1, column=0, sticky="nsew")
        log_panel.rowconfigure(1, weight=1)
        log_panel.columnconfigure(0, weight=1)
        ttk.Label(log_panel, text="运行日志", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.log = tk.Text(
            log_panel,
            wrap="word",
            height=20,
            bg=LOG_BG,
            fg=LOG_FG,
            insertbackground=LOG_FG,
            relief=tk.FLAT,
            borderwidth=0,
            padx=12,
            pady=12,
            font=("Consolas", 10),
        )
        self.log.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_panel, command=self.log.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

    def _panel(self, parent: tk.Widget, title: str) -> ttk.Frame:
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        ttk.Label(panel, text=title, style="PanelTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        return panel

    def _text_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        *,
        bg: str,
        fg: str,
        active: str | None = None,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active or bg,
            activeforeground=fg,
            relief=tk.FLAT,
            bd=0,
            padx=18,
            pady=9,
            font=("Microsoft YaHei UI", 10, "bold"),
            cursor="hand2",
        )

    def refresh_windows(self) -> None:
        self.windows = list_visible_windows()
        values = [f"{item['title']}  [{item['width']}x{item['height']} pid={item['pid']}]" for item in self.windows]
        self.window_combo["values"] = values
        if values:
            selected = self.window_combo.current()
            preferred = next(
                (
                    index
                    for index, item in enumerate(self.windows)
                    if str(item["title"]).strip() == DEFAULT_GAME_WINDOW_TITLE
                ),
                -1,
            )
            if preferred >= 0:
                self.window_combo.current(preferred)
            elif selected < 0 or selected >= len(values):
                self.window_combo.current(0)
        self.window_count_var.set(f"{len(values)} 个窗口")
        self.status_var.set("就绪")

    def selected_title(self) -> str:
        index = self.window_combo.current()
        if index < 0 or index >= len(self.windows):
            raise ValueError("请先选择一个窗口")
        return str(self.windows[index]["title"])

    def build_common_args(self) -> list[str]:
        selected_title = self.selected_title()
        window_args = ["--game-window"] if selected_title == DEFAULT_GAME_WINDOW_TITLE else ["--window-title", selected_title]
        return detector_command() + window_args + [
            "--capture-method",
            self.capture_var.get(),
            "--click-method",
            self.click_method_var.get(),
            "--restore-after-click" if self.restore_after_click_var.get() else "--no-restore-after-click",
            "--postmessage-fallback-sendinput"
            if self.postmessage_fallback_var.get()
            else "--no-postmessage-fallback-sendinput",
        ]

    def start_live(self) -> None:
        if self.process and self.process.poll() is None:
            return
        try:
            args = self.build_common_args()
            int(self.max_clicks_var.get() or "0")
            float(self.max_seconds_var.get() or "0")
        except Exception as exc:
            messagebox.showerror("无法启动", str(exc))
            return

        if STOP_FILE.exists():
            STOP_FILE.unlink()
        args += [
            "--live",
            "--max-clicks",
            self.max_clicks_var.get() or "0",
            "--max-seconds",
            self.max_seconds_var.get() or "0",
        ]
        if self.act_var.get():
            args.append("--act")
        if self.advance_unknown_var.get():
            args.append("--advance-on-unknown")
        if self.fast_start_var.get():
            args.append("--fast-start-to-team")
        self._start_process(args, "运行中")

    def state_check(self) -> None:
        if self.process and self.process.poll() is None:
            messagebox.showinfo("正在运行", "请先停止当前任务")
            return
        try:
            args = self.build_common_args() + ["--state-check"]
        except Exception as exc:
            messagebox.showerror("无法检查", str(exc))
            return
        self._start_process(args, "检查中")

    def _start_process(self, args: list[str], status: str) -> None:
        self.log.delete("1.0", tk.END)
        self._append_log("> " + " ".join(f'"{arg}"' if " " in arg else arg for arg in args) + "\n\n")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.process = subprocess.Popen(
            args,
            cwd=str(APP_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=flags,
        )
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.status_var.set(status)
        self.status_chip.configure(bg="#dbeafe", fg=BLUE_DARK)
        threading.Thread(target=self._read_process_output, daemon=True).start()

    def _read_process_output(self) -> None:
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            self.output_queue.put(line)
        code = self.process.wait()
        self.output_queue.put(f"\n进程已退出，代码 {code}\n")
        self.output_queue.put("__PROCESS_DONE__")

    def _drain_output(self) -> None:
        while True:
            try:
                line = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if line == "__PROCESS_DONE__":
                self.start_button.configure(state=tk.NORMAL)
                self.stop_button.configure(state=tk.DISABLED)
                self.status_var.set("就绪")
                self.status_chip.configure(bg="#dcfce7", fg="#166534")
            else:
                self._append_log(line)
        self.after(100, self._drain_output)

    def _append_log(self, text: str) -> None:
        self.log.insert(tk.END, text)
        self.log.see(tk.END)

    def stop_live(self) -> None:
        STOP_FILE.write_text("stop\n", encoding="utf-8")
        if self.process and self.process.poll() is None:
            self.status_var.set("正在停止")
            self.status_chip.configure(bg="#fef3c7", fg="#92400e")

    def open_config(self) -> None:
        config = APP_DIR / "config.json"
        if not config.exists():
            subprocess.run(detector_command() + ["--init-config"], cwd=str(APP_DIR))
        if sys.platform == "win32":
            subprocess.Popen(["notepad.exe", str(config)])
        else:
            messagebox.showinfo("配置文件", str(config))

    def on_close(self) -> None:
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno("退出", "任务还在运行，是否停止并退出？"):
                return
            self.stop_live()
        self.destroy()


def main() -> None:
    CznAutoGui().mainloop()


if __name__ == "__main__":
    main()
