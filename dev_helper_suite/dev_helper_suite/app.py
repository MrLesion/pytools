"""Minimal desktop frontend. All helper-specific UI comes from helpers.json."""
import json
import os
import signal
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from catalog import ROOT, load_catalog


class Toolbox(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Developer Helpers')
        self.geometry('1100x780')
        self.minsize(850, 620)
        self.proc = None
        self.busy = False
        self.closing = False
        self.cancelled = threading.Event()
        self.messages = queue.Queue()
        self.result = None
        self.values = {}
        self.inputs = {}
        self.protocol('WM_DELETE_WINDOW', self.close)
        style = ttk.Style(self)
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('TButton', padding=(10, 5))
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='Developer Helpers', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
        ttk.Label(outer, text='Small tools for APIs, websites and integration data').pack(anchor='w', pady=(2, 14))
        body = ttk.Panedwindow(outer, orient='horizontal')
        body.pack(fill='both', expand=True)
        sidebar = ttk.Frame(body)
        body.add(sidebar, weight=1)
        self.listbox = tk.Listbox(sidebar, exportselection=False, width=27, activestyle='none', font=('Segoe UI', 11))
        self.listbox.pack(fill='both', expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.select)
        self.reload_button = ttk.Button(sidebar, text='Reload catalog', command=self.reload)
        self.reload_button.pack(fill='x', pady=(8, 0))
        panel = ttk.Frame(body, padding=(16, 0, 0, 0))
        body.add(panel, weight=4)
        self.title_label = ttk.Label(panel, font=('Segoe UI', 15, 'bold'))
        self.title_label.pack(anchor='w')
        self.description = ttk.Label(panel, wraplength=680, justify='left')
        self.description.pack(anchor='w', pady=(4, 12))
        tabs = ttk.Notebook(panel)
        tabs.pack(fill='both', expand=True)
        run_tab, help_tab = ttk.Frame(tabs, padding=10), ttk.Frame(tabs, padding=10)
        tabs.add(run_tab, text='Run helper')
        tabs.add(help_tab, text='Examples & code')
        setup_tab = ttk.Frame(tabs, padding=10)
        tabs.add(setup_tab, text='Pip & setup')
        setup_text = ScrolledText(setup_tab, wrap='word', font=('Consolas', 10))
        setup_text.pack(fill='both', expand=True)
        for filename in ('SETUP.txt', 'requirements.txt', 'requirements-browser.txt', 'requirements-all.txt'):
            setup_text.insert('end', filename + '\n' + '-' * len(filename) + '\n')
            setup_text.insert('end', (ROOT / filename).read_text(encoding='utf-8') + '\n\n')
        setup_text.config(state='disabled')
        # Scrollable schema-driven form.
        form_holder = ttk.Frame(run_tab)
        form_holder.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(form_holder, height=240, highlightthickness=0)
        scrollbar = ttk.Scrollbar(form_holder, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.form = ttk.Frame(self.canvas)
        window = self.canvas.create_window((0, 0), window=self.form, anchor='nw')
        self.form.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(window, width=e.width))
        self.form.columnconfigure(1, weight=1)
        actions = ttk.Frame(run_tab)
        actions.pack(fill='x', pady=8)
        self.run_button = ttk.Button(actions, text='Run helper', command=self.run_helper)
        self.run_button.pack(side='left')
        self.cancel_button = ttk.Button(actions, text='Cancel', command=self.cancel, state='disabled')
        self.cancel_button.pack(side='left', padx=6)
        ttk.Button(actions, text='Export result', command=self.export).pack(side='right')
        ttk.Button(actions, text='Load inputs', command=self.load_inputs).pack(side='right', padx=6)
        self.status = ttk.Label(run_tab, text='Ready')
        self.status.pack(anchor='w')
        self.output = ScrolledText(run_tab, height=15, wrap='none', font=('Consolas', 10))
        self.output.pack(fill='both', expand=True, pady=(6, 0))
        self.help = ScrolledText(help_tab, wrap='word', font=('Consolas', 10))
        self.help.pack(fill='both', expand=True)
        self.reload()
        self.after(100, self.poll)

    def reload(self):
        try:
            self.helpers = load_catalog()
        except Exception as exc:
            messagebox.showerror('Invalid catalog', str(exc))
            return
        self.listbox.delete(0, 'end')
        for item in self.helpers:
            self.listbox.insert('end', item['name'])
        self.listbox.selection_set(0)
        self.select()

    def select(self, event=None):
        if self.busy or not self.listbox.curselection():
            return
        self.item = self.helpers[self.listbox.curselection()[0]]
        self.title_label.config(text=self.item['name'])
        self.description.config(text=self.item['description'])
        for child in self.form.winfo_children():
            child.destroy()
        self.inputs = {}
        for row, field in enumerate(self.item['fields']):
            name, kind = field['name'], field.get('type', 'text')
            ttk.Label(self.form, text=field.get('label', name) + (' *' if field.get('required') else '')).grid(row=row, column=0, sticky='nw', padx=(0, 12), pady=5)
            default = field.get('default', '')
            if kind == 'multiline':
                widget = ScrolledText(self.form, height=3, width=40)
                widget.insert('1.0', str(default))
                value = widget
            elif kind == 'bool':
                value = tk.BooleanVar(value=bool(default))
                widget = ttk.Checkbutton(self.form, variable=value)
            else:
                value = tk.StringVar(value=json.dumps(default) if kind == 'json' and default != '' else str(default))
                widget = ttk.Combobox(self.form, textvariable=value, values=field.get('options', []), state='readonly') if kind == 'select' else ttk.Entry(self.form, textvariable=value)
            widget.grid(row=row, column=1, sticky='ew', pady=5)
            if kind in ('file', 'path'):
                ttk.Button(self.form, text='Browse', command=lambda v=value: self.browse(v)).grid(row=row, column=2, padx=(6, 0))
            self.inputs[name] = (field, value)
        self.help.config(state='normal')
        self.help.delete('1.0', 'end')
        self.help.insert('end', 'WHAT IT DOES\n\n' + self.item['description'] + '\n\nEXAMPLE USE\n\n' + self.item['example_use'] + '\n\nCODE EXAMPLE\n\n' + self.item['code_example'])
        self.help.config(state='disabled')
        self.result = None
        self.output.delete('1.0', 'end')
        self.status.config(text='Ready')

    def browse(self, value):
        path = filedialog.askopenfilename()
        if path:
            value.set(path)

    def collect(self):
        params = {}
        for name, (field, value) in self.inputs.items():
            kind = field.get('type', 'text')
            raw = value.get('1.0', 'end-1c').strip() if kind == 'multiline' else value.get()
            if field.get('required') and raw == '':
                raise ValueError(f'{field.get("label", name)} is required')
            if raw == '' and not field.get('required'):
                continue
            try:
                params[name] = int(raw) if kind == 'int' else float(raw) if kind == 'float' else json.loads(raw) if kind == 'json' else raw
            except (ValueError, TypeError):
                raise ValueError(f'Invalid {kind} value for {name}')
        return params

    def load_inputs(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(filetypes=[('JSON', '*.json')])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                raise ValueError('Inputs must be a JSON object')
            for name, raw in data.items():
                if name not in self.inputs:
                    continue
                field, value = self.inputs[name]
                if field.get('type') == 'multiline':
                    value.delete('1.0', 'end')
                    value.insert('1.0', '\n'.join(raw) if isinstance(raw, list) else str(raw))
                else:
                    value.set(json.dumps(raw) if field.get('type') == 'json' else ','.join(map(str, raw)) if isinstance(raw, list) else raw)
        except Exception as exc:
            messagebox.showerror('Cannot load inputs', str(exc))

    def run_helper(self):
        try:
            params = self.collect()
        except ValueError as exc:
            messagebox.showerror('Check inputs', str(exc))
            return
        self.busy = True
        self.cancelled.clear()
        self.result = None
        self.output.delete('1.0', 'end')
        self.status.config(text='Running…')
        self.run_button.config(state='disabled')
        self.reload_button.config(state='disabled')
        self.listbox.config(state='disabled')
        self.cancel_button.config(state='normal')
        script = self.item['_script']
        def worker():
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                self.proc = subprocess.Popen([sys.executable, script], cwd=ROOT, stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', creationflags=creationflags, start_new_session=sys.platform != 'win32')
                if self.cancelled.is_set():
                    self.stop_process(self.proc)
                try:
                    out, err = self.proc.communicate(json.dumps(params), timeout=600)
                except subprocess.TimeoutExpired:
                    self.stop_process(self.proc)
                    self.proc.communicate()
                    raise ValueError('Run exceeded 10 minutes. Reduce the input size or split the run.')
                if self.cancelled.is_set():
                    self.messages.put((None, 'Cancelled'))
                else:
                    try:
                        result = json.loads(out)
                    except ValueError:
                        raise ValueError(f'Helper did not return JSON. {err[-4000:]} {out[-1000:]}')
                    status = 'Completed' if self.proc.returncode == 0 else 'Completed with findings' if self.proc.returncode == 1 else 'Failed'
                    self.messages.put((result, status))
            except Exception as exc:
                self.messages.put(({'ok': False, 'summary': str(exc)}, 'Failed'))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            result, status = self.messages.get_nowait()
        except queue.Empty:
            pass
        else:
            self.result = result
            self.busy = False
            self.proc = None
            self.status.config(text=status)
            self.output.delete('1.0', 'end')
            if result is not None:
                self.output.insert('end', json.dumps(result, indent=2, ensure_ascii=False))
            self.run_button.config(state='normal')
            self.reload_button.config(state='normal')
            self.listbox.config(state='normal')
            self.cancel_button.config(state='disabled')
            if self.closing:
                self.destroy()
                return
        self.after(100, self.poll)

    @staticmethod
    def stop_process(proc):
        # Terminate browser descendants as well as the helper itself.
        try:
            if sys.platform == 'win32':
                subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                               capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def cancel(self):
        self.cancelled.set()
        proc = self.proc
        if proc and proc.poll() is None:
            self.stop_process(proc)
        self.status.config(text='Cancelling…')

    def export(self):
        if self.result is None:
            messagebox.showinfo('No result', 'Run a helper before exporting.')
            return
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
        if path:
            try:
                Path(path).write_text(json.dumps(self.result, indent=2, ensure_ascii=False), encoding='utf-8')
            except OSError as exc:
                messagebox.showerror('Export failed', str(exc))

    def close(self):
        if self.busy:
            self.closing = True
            self.cancel()
        else:
            self.destroy()


if __name__ == '__main__':
    Toolbox().mainloop()
