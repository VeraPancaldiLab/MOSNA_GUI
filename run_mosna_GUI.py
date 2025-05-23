import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkfont
import yaml
import subprocess
import os
import ast

CONFIG_PATH = 'CONFIG/configuration.yaml'
SCRIPTS = [
    'pre_processing.sh',
    'draw_tysserand_IMC_IF.sh',
    'mosna_assortativity.sh',
    'mosna_NAS.sh'
]

class MosnaGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Mosna Analysis GUI')
        default_font = tkfont.nametofont('TkDefaultFont')
        default_font.configure(size=12)
        style = ttk.Style(self)
        style.configure('Large.TButton', font=default_font)

        self.config_data = {}
        self.entries = {}
        self._load_config()
        self._build_ui()

    def _load_config(self):
        try:
            with open(CONFIG_PATH, 'r') as f:
                raw = yaml.safe_load(f) or {}
                self.config_data = self._normalize_config(raw)
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load config: {e}')
            self.config_data = {}
    
    def _normalize_config(self, d):
        def _safe_eval(v):
            if isinstance(v, (dict, list)):
                return v
            try:
                val = ast.literal_eval(v)
                return val if isinstance(val, (list, dict)) else v
            except Exception:
                return v
        if isinstance(d, dict):
            return {k: self._normalize_config(_safe_eval(v)) for k, v in d.items()}
        return d
    
    def _save_config(self):
        try:
            # Preserve documentation at end
            doc = self.config_data.pop('documentation', None)
            ordered = dict(self.config_data)
            if doc is not None:
                ordered['documentation'] = doc
            with open(CONFIG_PATH, 'w') as f:
                # Use block-style YAML with literal strings preserved and wide flow
                yaml.safe_dump(
                    ordered,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    width=4096,
                    encoding=('utf-8'),
                    default_style=None
                )
            messagebox.showinfo('Saved', 'Configuration saved successfully.')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to save config: {e}')
            messagebox.showerror('Error', f'Failed to save config: {e}')

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        order = ['General', 'IF_import', 'IMC_import', 'tysserand', 'Assortativity', 'NAS', 'documentation']

        # General tab
        gen = ttk.Frame(notebook)
        notebook.add(gen, text='General')
        gen_data = {k: v for k, v in self.config_data.items() if not isinstance(v, dict) and k != 'documentation'}
        self._build_section(gen, '__general__', gen_data)

        # Other ordered sections
        for key in order[1:]:
            if key == 'documentation' and 'documentation' in self.config_data:
                df = ttk.Frame(notebook)
                notebook.add(df, text='Documentation')
                doc = self.config_data['documentation']
                if isinstance(doc, dict):
                    dnb = ttk.Notebook(df)
                    dnb.pack(fill='both', expand=True)
                    for sec, cont in doc.items():
                        sf = ttk.Frame(dnb)
                        dnb.add(sf, text=sec)
                        tw = tk.Text(sf)
                        tw.insert('1.0', cont)
                        tw.config(state='disabled')
                        tw.pack(fill='both', expand=True)
                else:
                    tw = tk.Text(df)
                    tw.insert('1.0', doc)
                    tw.config(state='disabled')
                    tw.pack(fill='both', expand=True)
            elif key in self.config_data and isinstance(self.config_data[key], dict):
                sf = ttk.Frame(notebook)
                notebook.add(sf, text=key)
                self._add_section(sf, key, self.config_data[key])

        # Extras
        for sec, data in self.config_data.items():
            if sec in order or sec == 'documentation' or not isinstance(data, dict):
                continue
            ef = ttk.Frame(notebook)
            notebook.add(ef, text=sec)
            self._add_section(ef, sec, data)

        # Buttons
        bf = ttk.Frame(self)
        bf.pack(fill='x', pady=10, padx=10)
        ttk.Button(bf, text='Save Config', style='Large.TButton', command=self._on_save).pack(side='left')
        ttk.Button(bf, text='Run All Scripts', style='Large.TButton', command=self._on_run_all).pack(side='right')
        for s in reversed(SCRIPTS):
            ttk.Button(bf, text=f'Run {os.path.basename(s)}', style='Large.TButton', command=lambda sc=s: self._on_run_script(sc)).pack(side='right', padx=2)

    def _add_section(self, frame, section, data):
        # NAS section with nested sub-sections, including nodes_aggregation
        if section == 'NAS':
            nb = ttk.Notebook(frame)
            nb.pack(fill='both', expand=True)
            # General sub-section for NAS
            general = {k: v for k, v in data.items() if not isinstance(v, dict)}
            if general:
                sub = ttk.Frame(nb)
                nb.add(sub, text='General')
                self._build_section(sub, 'NAS__general', general)
            # Each NAS sub-section
            for subsec, subdata in data.items():
                if not isinstance(subdata, dict):
                    continue
                sub = ttk.Frame(nb)
                nb.add(sub, text=subsec)
                # If this sub-section is nodes_aggregation, create nested tabs
                if subsec == 'nodes_aggregation':
                    nested_nb = ttk.Notebook(sub)
                    nested_nb.pack(fill='both', expand=True)
                    for subsub, subsubdata in subdata.items():
                        if isinstance(subsubdata, dict):
                            nest_frame = ttk.Frame(nested_nb)
                            nested_nb.add(nest_frame, text=subsub)
                            self._build_section(nest_frame, f'nodes_aggregation__{subsub}', subsubdata)
                else:
                    # Regular NAS sub-section
                    self._build_section(sub, f'NAS__{subsec}', subdata)
        else:
            # Default handler for non-NAS sections
            self._build_section(frame, section, data)

    def _build_section(self, parent, section_key, data):
        parent.columnconfigure(1, weight=1)
        for i, (k, v) in enumerate(data.items()):
            ttk.Label(parent, text=k).grid(row=i, column=0, sticky='nw', pady=2)
            if isinstance(v, str) and ('\n' in v or '\t' in v):
                t = tk.Text(parent, height=4)
                t.insert('1.0', v)
                t.grid(row=i, column=1, sticky='nsew', pady=2)
                widget = t
            else:
                e = ttk.Entry(parent)
                e.insert(0, str(v))
                e.grid(row=i, column=1, sticky='ew', pady=2)
                widget = e
            self.entries.setdefault(section_key, {})[k] = widget

    def _parse_value(self, widget):
        if isinstance(widget, tk.Text):
            return widget.get('1.0', 'end-1c')
        val = widget.get().strip()
        if val.lower() in ('none','null',''):
            return None
        if val.lower() in ('true','false'):
            return val.lower() == 'true'
        try:
            return int(val)
        except:
            pass
        try:
            return float(val)
        except:
            pass
        if val.startswith('[') and val.endswith(']'):
            return val
        return val

    def _on_save(self):
        new = {}
        if 'documentation' in self.config_data:
            new['documentation'] = self.config_data['documentation']

        for sec, its in self.entries.items():
            if sec == '__general__':
                for k, w in its.items():
                    new[k] = self._parse_value(w)
                continue

            # Séparer tous les niveaux imbriqués (ex: NAS__nodes_aggregation__sub1)
            keys = sec.split('__')
            target = new
            for key in keys[:-1]:
                target = target.setdefault(key, {})
            target[keys[-1]] = {k: self._parse_value(w) for k, w in its.items()}

        self.config_data = new
        self._save_config()

    def _on_run_script(self, script):
        self._on_save()
        if not os.path.isfile(script):
            messagebox.showwarning('Missing', f"Script not found: {script}")
            return
        try:
            subprocess.check_call(['bash', script])
            messagebox.showinfo('Success', f'Script completed: {os.path.basename(script)}')
        except subprocess.CalledProcessError as e:
            messagebox.showerror('Error', f"Script failed: {script}\n{e}")

    def _on_run_all(self):
        self._on_save()
        for s in SCRIPTS:
            if not os.path.isfile(s):
                messagebox.showwarning('Missing', f"Script not found: {s}")
                continue
            try:
                subprocess.check_call(['bash', s])
            except subprocess.CalledProcessError as e:
                messagebox.showerror('Error', f"Script failed: {s}\n{e}")
                return
        messagebox.showinfo('Done', 'All scripts completed successfully.')

if __name__ == '__main__':
    try:
        import yaml
    except ImportError:
        messagebox.showerror('Error', 'PyYAML is required. Install with `pip install pyyaml`.')
    else:
        MosnaGUI().mainloop()
