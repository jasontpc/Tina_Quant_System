#!/usr/bin/env python3
"""
Tina Gateway Monitor GUI v2
Standalone GUI to monitor and restart OpenClaw Gateway

Improvements:
- All subprocess calls run in background threads
- Uses Popen instead of run() for non-blocking execution
- Thread-safe UI updates via root.after()
- Proper error handling and encoding
- Timeout protection for all operations
"""

import tkinter as tk
from tkinter import ttk
import requests
import subprocess
import threading
import time
import sys
from pathlib import Path
from datetime import datetime
import queue

# ============ CONFIG ============
GATEWAY_URL = "http://127.0.0.1:18789"
CHECK_INTERVAL = 5  # seconds
CHECK_TIMEOUT = 3   # seconds for health check
RESTART_TIMEOUT = 30  # seconds for restart operations
LOG_FILE = Path(__file__).parent / "gateway_monitor.log"
# ==============================

class GatewayMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tina Gateway Monitor v2")
        self.root.geometry("480x340")
        self.root.configure(bg="#2b2b2b")
        
        # State variables (thread-safe access via queue)
        self.is_monitoring = False
        self.is_running = False
        self.is_restarting = False
        self.restart_count = 0
        self.log_queue = queue.Queue()
        self.command_queue = queue.Queue()
        
        self.setup_ui()
        self.schedule_status_check()
        
    def setup_ui(self):
        # Title
        title_frame = tk.Frame(self.root, bg="#1a1a2e", height=40)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, text="Tina Gateway Monitor", 
                 font=("Arial", 12, "bold"),
                 fg="white", bg="#1a1a2e").pack(pady=8)
        
        # Status section
        status_frame = tk.Frame(self.root, bg="#2b2b2b")
        status_frame.pack(fill="x", pady=5, padx=10)
        
        # Status indicator (colored circle)
        self.canvas = tk.Canvas(status_frame, width=30, height=30, 
                                bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(side="left", padx=(0, 10))
        self.circle = self.canvas.create_oval(5, 5, 25, 25, fill="#e74c3c", outline="")
        
        self.status_text = tk.Label(status_frame, text="STOPPED",
                                      font=("Arial", 14, "bold"),
                                      fg="#e74c3c", bg="#2b2b2b")
        self.status_text.pack(side="left")
        
        self.info_text = tk.Label(status_frame, text="",
                                   font=("Arial", 9),
                                   fg="#888888", bg="#2b2b2b")
        self.info_text.pack(side="left", padx=10)
        
        # Buttons section
        btn_frame = tk.Frame(self.root, bg="#2b2b2b")
        btn_frame.pack(pady=10)
        
        # Row 1: Main controls
        self.start_btn = tk.Button(btn_frame, text="START",
                                   font=("Arial", 10, "bold"),
                                   bg="#27ae60", fg="white",
                                   padx=12, pady=4,
                                   command=self.on_start_click,
                                   state="disabled")
        self.start_btn.grid(row=0, column=0, padx=3)
        
        self.stop_btn = tk.Button(btn_frame, text="STOP",
                                  font=("Arial", 10, "bold"),
                                  bg="#e74c3c", fg="white",
                                  padx=12, pady=4,
                                  command=self.on_stop_click,
                                  state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=3)
        
        self.monitor_btn = tk.Button(btn_frame, text="MONITOR",
                                      font=("Arial", 10, "bold"),
                                      bg="#3498db", fg="white",
                                      padx=12, pady=4,
                                      command=self.on_monitor_click)
        self.monitor_btn.grid(row=0, column=2, padx=3)
        
        self.refresh_btn = tk.Button(btn_frame, text="REFRESH",
                                      font=("Arial", 9),
                                      bg="#7f8c8d", fg="white",
                                      padx=10, pady=4,
                                      command=self.check_status)
        self.refresh_btn.grid(row=0, column=3, padx=3)
        
        # Row 2: Info
        info_frame = tk.Frame(self.root, bg="#2b2b2b")
        info_frame.pack(pady=2)
        
        self.restart_label = tk.Label(info_frame, text="Auto-restarts: 0",
                                       font=("Arial", 9),
                                       fg="#f39c12", bg="#2b2b2b")
        self.restart_label.grid(row=0, column=0, columnspan=4)
        
        # Monitor status
        self.monitor_status = tk.Label(info_frame, text="Monitor: OFF",
                                        font=("Arial", 9),
                                        fg="#aaaaaa", bg="#2b2b2b")
        self.monitor_status.grid(row=1, column=0, columnspan=4)
        
        # Log section
        log_frame = tk.Frame(self.root, bg="#1a1a1a")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = tk.Text(log_frame, height=9, font=("Consolas", 8),
                                 bg="#1a1a1a", fg="#00ff88",
                                 relief="flat")
        log_scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True)
        
        self.log("[Tina Gateway Monitor v2 started]")
        self.log("Gateway URL: {}".format(GATEWAY_URL))
        
        # Start log processor
        self.root.after(100, self.process_log_queue)
        
    def log(self, msg):
        """Add message to log queue (thread-safe)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put("[{}] {}".format(timestamp, msg))
        
    def process_log_queue(self):
        """Process log messages from queue"""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.process_log_queue)
        
    def update_ui(self, **kwargs):
        """Thread-safe UI update via queue"""
        def _update():
            for key, value in kwargs.items():
                if key == "status_text":
                    self.status_text.config(text=value)
                elif key == "status_color":
                    self.status_text.config(fg=value)
                elif key == "circle_color":
                    self.canvas.itemconfig(self.circle, fill=value)
                elif key == "info_text":
                    self.info_text.config(text=value)
                elif key == "start_state":
                    self.start_btn.config(state=value)
                elif key == "stop_state":
                    self.stop_btn.config(state=value)
                elif key == "restart_count":
                    self.restart_label.config(text="Auto-restarts: {}".format(value))
                elif key == "monitor_text":
                    self.monitor_status.config(text=value)
                    self.monitor_status.config(fg="#27ae60" if "ON" in value else "#aaaaaa")
                elif key == "monitor_color":
                    self.monitor_btn.config(bg=value)
                    text = "STOP MONITOR" if value == "#e67e22" else "MONITOR"
                    self.monitor_btn.config(text=text)
                    
        self.root.after(0, _update)
        
    def check_gateway(self):
        """Check if Gateway is responding"""
        try:
            resp = requests.get(GATEWAY_URL, timeout=CHECK_TIMEOUT)
            return resp.status_code == 200
        except:
            return False
            
    def check_status(self):
        """Check and update UI with current gateway status"""
        is_running = self.check_gateway()
        self.is_running = is_running
        
        if is_running:
            self.update_ui(
                status_text="RUNNING",
                status_color="#27ae60",
                circle_color="#27ae60",
                info_text="Gateway responding normally",
                start_state="disabled",
                stop_state="normal"
            )
        else:
            self.update_ui(
                status_text="STOPPED",
                status_color="#e74c3c",
                circle_color="#e74c3c",
                info_text="Gateway not responding",
                start_state="normal",
                stop_state="disabled"
            )
            
    def schedule_status_check(self):
        """Schedule periodic status check"""
        self.check_status()
        self.root.after(CHECK_INTERVAL * 1000, self.schedule_status_check)
        
    def run_command(self, cmd, callback=None):
        """Run command in background thread (non-blocking)"""
        def _thread():
            self.log("Executing: {}".format(cmd))
            try:
                # Use Popen for non-blocking execution
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # Wait with timeout
                try:
                    stdout, stderr = proc.communicate(timeout=RESTART_TIMEOUT)
                    returncode = proc.returncode
                    
                    if returncode == 0:
                        self.log("Command succeeded")
                        if callback:
                            callback(True, stdout, stderr)
                    else:
                        err_msg = stderr[:200] if stderr else "Unknown error"
                        self.log("Command failed: {}".format(err_msg))
                        if callback:
                            callback(False, stdout, stderr)
                            
                except subprocess.TimeoutExpired:
                    proc.kill()
                    self.log("Command timed out after {}s".format(RESTART_TIMEOUT))
                    if callback:
                        callback(False, None, "Timeout")
                        
            except Exception as e:
                self.log("Exception: {}".format(str(e)))
                if callback:
                    callback(False, None, str(e))
                    
        thread = threading.Thread(target=_thread, daemon=True)
        thread.start()
        
    def on_start_click(self):
        """Start button clicked"""
        if self.is_restarting:
            self.log("Already restarting, please wait...")
            return
            
        self.log("=== START GATEWAY ===")
        self.is_restarting = True
        
        # Show restarting status
        self.update_ui(
            status_text="STARTING",
            status_color="#f39c12",
            circle_color="#f39c12",
            info_text="Starting Gateway...",
            start_state="disabled",
            stop_state="disabled"
        )
        
        def on_started(success, stdout, stderr):
            if success:
                self.log("Gateway start command sent")
                # Wait and check
                threading.Thread(target=self._wait_and_check, daemon=True).start()
            else:
                self.log("Gateway start failed")
                self.is_restarting = False
                self.check_status()
                
        self.run_command('powershell -Command "openclaw gateway start"', on_started)
        
    def on_stop_click(self):
        """Stop button clicked"""
        if self.is_restarting:
            self.log("Already restarting, please wait...")
            return
            
        if not self.is_running:
            self.log("Gateway is already stopped")
            return
            
        self.log("=== STOP GATEWAY ===")
        
        def on_stopped(success, stdout, stderr):
            if success:
                self.log("Gateway stop command sent")
            else:
                self.log("Gateway stop: {}".format(stderr[:100] if stderr else "Failed"))
            # Always update status after stop attempt
            time.sleep(1)
            self.check_status()
            self.is_restarting = False
            
        self.run_command('powershell -Command "openclaw gateway stop"', on_stopped)
        
    def _wait_and_check(self):
        """Wait for Gateway to start and check status"""
        for i in range(10):
            time.sleep(2)
            if self.check_gateway():
                self.log("Gateway is now running")
                self.is_restarting = False
                self.check_status()
                return
            self.log("Waiting for Gateway... {}/10".format(i+1))
            
        self.log("Gateway did not start within 20s")
        self.is_restarting = False
        self.check_status()
        
    def on_monitor_click(self):
        """Toggle monitor on/off"""
        if self.is_monitoring:
            self.log("Auto-monitor DISABLED")
            self.is_monitoring = False
            self.update_ui(
                monitor_text="Monitor: OFF",
                monitor_color="#3498db"
            )
        else:
            self.log("Auto-monitor ENABLED")
            self.is_monitoring = True
            self.update_ui(
                monitor_text="Monitor: ON",
                monitor_color="#e67e22"
            )
            self._run_auto_monitor()
            
    def _run_auto_monitor(self):
        """Background auto-monitor loop"""
        if not self.is_monitoring:
            return
            
        is_running = self.check_gateway()
        
        if not is_running and not self.is_restarting:
            self.log("=== AUTO-RESTART TRIGGERED ===")
            self.is_restarting = True
            self.restart_count += 1
            self.update_ui(restart_count=self.restart_count)
            
            def on_restarted(success, stdout, stderr):
                if success:
                    self.log("Restart command sent, waiting...")
                    threading.Thread(target=self._wait_and_check, daemon=True).start()
                else:
                    self.log("Auto-restart failed: {}".format(str(stderr)[:100] if stderr else "unknown"))
                    self.is_restarting = False
                    
            self.run_command('powershell -Command "openclaw gateway stop"', None)
            time.sleep(2)
            self.run_command('powershell -Command "openclaw gateway start"', on_restarted)
        elif not is_running:
            pass  # Already restarting
        else:
            pass  # Gateway is running
            
        # Schedule next check
        self.root.after(CHECK_INTERVAL * 1000, self._run_auto_monitor if self.is_monitoring else lambda: None)
        
    def on_close(self):
        """Handle window close"""
        self.is_monitoring = False
        self.root.destroy()
        sys.exit(0)


def main():
    root = tk.Tk()
    app = GatewayMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()