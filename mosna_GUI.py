import os
import sys
import yaml
import ast
import subprocess
import io
import shlex
from yaml.representer import SafeRepresenter

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox,
    QPushButton, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QLineEdit,
    QTextEdit, QFormLayout, QScrollArea, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QTextCursor

CONFIG_PATH = 'CONFIG/configuration.yaml'
SCRIPTS = [
    'SCRIPT/pre_processing.sh',
    'SCRIPT/draw_tysserand.py',
    'SCRIPT/mosna_assortativity.py',
    'SCRIPT/mosna_NAS.py',
    'SCRIPT/clear_temporary_files.sh'
]

class ScriptRunnerThread(QThread):
    output_signal = Signal(str)
    finished_signal = Signal(bool, int)

    def __init__(self, command):
        super().__init__()
        self.command = command

    def run(self):
        try:
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in process.stdout:
                self.output_signal.emit(line)
            code = process.wait()
            self.finished_signal.emit(code == 0, code)
        except Exception as e:
            self.output_signal.emit(f"Error: {e}")
            self.finished_signal.emit(False, -1)

class FlowStyleList(list):
    pass

def represent_flow_style_list(dumper, data):
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)
yaml.add_representer(FlowStyleList, represent_flow_style_list, Dumper=yaml.SafeDumper)
def force_inline_lists(obj):
    if isinstance(obj, dict):
        return {k: force_inline_lists(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return FlowStyleList(force_inline_lists(i) for i in obj)
    return obj

class MosnaGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mosna Analysis GUI")

        self.config_data = {}
        self.entries = {}

        self._load_config()
        self._build_ui()
        self.expected_types = {
            "silent":        (bool, type(None)),
            "phenograph":    (bool, type(None)),
            "pheno_dir":     (str,  type(None)),
            "add_pheno":     (bool, type(None)),
            "present_in":          (bool,    type(None)),
            "directory_path":      (str,     type(None)),
            "path_encoding_patient": (str,   type(None)), 
            "path_file_to_patient":  (str,   type(None)),
            "phenotypes":            (str,  type(None)), 
            "columns_to_drop":      (str,   type(None)),
            "layer_columns":        (str,   type(None)),
            "patient_columns":      (str,   type(None)),
            "marker_columns":       (str,   type(None)),
            "cell_id_columns":      (int,   type(None)),
            "spatial_columns":      (str,   type(None)),
            "normalization_method":            (bool,  type(None)),
            "re_index":             (bool,  type(None)),
            "there_is_duplicata":   (bool,  type(None)),
            "cpu":                    (int,  type(None)),
            "k_neighbors_phenograph": (int,  type(None)),
            "panel": (str, type(None)),
            "primary_metric_phenograph": (str, type(None)),
            "method_tysserand":        (str, type(None)),
            "min_neighbors":           (int, type(None)),
            "IF_perform":            (bool, type(None)),
            "IMC_perform":           (bool, type(None)),
            "perform_batch":         (bool, type(None)),
            "perform_clr_transfo":   (bool, type(None)),
            "method":                (str,  type(None)),
            "output_name_file":      (str,  type(None)),
            "node_aggregation":      (bool, type(None)),
            "perform_NAS_all_sample": (bool, type(None)),
            "order":           (str,   type(None)),
            "stat_funcs":      (str,   type(None)),
            "stat_names":      (list,  type(None)),
            "clusterer_type":  (str,   type(None)),
            "n_clusters":      (int,   type(None)),
            "reducer_type":    (str,   type(None)),
            "metric":          (str,   type(None)),
            "resolution":      (float, type(None)),
            "n_neighbors":     (int,   type(None)),
            "min_dist":        (float, type(None)),
            "dim_clust":       (int,   type(None)),
            "min_cluster_size":(int,   type(None)),
            "k_cluster":       (int,   type(None)),
            "normalize":       (str,   type(None)),
        }

    def _on_script_finished(self, script, success, returncode):
        if success:
            self._append_console(f"[✓] Script completed: {script}\n")
            QMessageBox.information(self, "Success", f"Script completed: {os.path.basename(script)}")
        else:
            self._append_console(f"[✗] Script failed (code {returncode}): {script}\n")
            QMessageBox.critical(self, "Error", f"Script failed: {script}\nExit code: {returncode}")

    def _load_config(self):
        try:
            with open(CONFIG_PATH, 'r') as f:
                raw = yaml.safe_load(f) or {}
                if not raw:
                    QMessageBox.warning(self, "Empty Config", "The configuration file is empty. Please check the file.")
                self.config_data = self._normalize_config(raw)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config:\n{e}")
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

    def _get_widget_for_value(self, key, value):
        if isinstance(value, bool):
            combo = QComboBox()
            combo.addItems(['True', 'False'])
            combo.setCurrentText(str(value))
            return combo

        lower_key = key.lower()
        if lower_key in ['method'] and isinstance(value, str):
            options = ['NAS']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        elif lower_key in ['reducer_type'] and isinstance(value, str):
            options = ['umap']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        elif lower_key in ['clusterer_type'] and isinstance(value, str):
            options = ['leiden','ecg','spectral','gmm','hdbscan']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        elif lower_key in ['order'] and isinstance(value, str):
            options = ['1','2']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        elif lower_key in ['metric'] and isinstance(value, str):
            options = ['manhattan', 'euclidean', 'cosine']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        elif lower_key in ['primary_metric_phenograph'] and isinstance(value, str):
            options = ['minkowski']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        elif lower_key in ['method_tysserand'] and isinstance(value, str):
            options = ['delaunay','knn']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        elif lower_key in ['stat_funcs'] and isinstance(value, str):
            options = ['np.mean,np.std','np.mean']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        elif lower_key in ['normalize'] and isinstance(value, str):
            options = ['total', 'niche', 'obs', 'clr', 'niche&obs']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        if isinstance(value, str) and ('\n' in value or '\t' in value):
            text_edit = QTextEdit()
            text_edit.setPlainText(value)
            return text_edit

        return QLineEdit(str(value))

    def _build_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        order = ['General', 'IF_import', 'IMC_import', 'tysserand', 'Assortativity', 'NAS', 'documentation']
        general_data = {k: v for k, v in self.config_data.items() if not isinstance(v, dict) and k != 'documentation'}
        self._add_tab("General", "__general__", general_data)

        for key in order[1:]:
            if key == "documentation" and "documentation" in self.config_data:
                self._add_doc_tab(self.config_data['documentation'])
            elif key in self.config_data and isinstance(self.config_data[key], dict):
                self._add_nested_tab(key, self.config_data[key])

        for sec, data in self.config_data.items():
            if sec not in order and isinstance(data, dict):
                self._add_nested_tab(sec, data)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        for s in SCRIPTS:
            b = QPushButton(f"Run {os.path.splitext(os.path.basename(s))[0].replace('_', ' ').upper()}")
            b.clicked.connect(lambda _, sc=s: self._run_script(sc))
            btn_layout.addWidget(b)

        save_btn = QPushButton("Save Config")
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("background-color: black; color: white; font-family: monospace;")
        self.console_output.setMinimumHeight(250)
        layout.addWidget(QLabel("Console Output:"))
        layout.addWidget(self.console_output)

    def _add_tab(self, tab_name, section_key, data):
        tab = QWidget()
        form_layout = QFormLayout(tab)
        tab.setLayout(form_layout)

        for k, v in data.items():
            label = QLabel(k)
            widget = self._get_widget_for_value(k, v)
            form_layout.addRow(label, widget)
            self.entries.setdefault(section_key, {})[k] = widget

        self.tabs.addTab(tab, tab_name)

    def _add_nested_tab(self, section, data):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)

        inner_tabs = QTabWidget()
        tab_layout.addWidget(inner_tabs)
        
        general = {k: v for k, v in data.items() if not isinstance(v, dict)}
        if general:
            self._add_inner_form(inner_tabs, "General", f"{section}", general)

        for subsec, subdata in data.items():
            if isinstance(subdata, dict):
                if section == "NAS" and subsec == "nodes_aggregation":
                    nested = QWidget()
                    nested_layout = QVBoxLayout(nested)
                    deep_tabs = QTabWidget()
                    nested_layout.addWidget(deep_tabs)
                    for subsub, subsubdata in subdata.items():
                        self._add_inner_form(deep_tabs, subsub, f"{section}__nodes_aggregation__{subsub}", subsubdata)
                    inner_tabs.addTab(nested, "nodes_aggregation")
                else:
                    self._add_inner_form(inner_tabs, subsec, f"{section}__{subsec}", subdata)

        self.tabs.addTab(tab, section)

    def _append_console(self, text):
        cursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.End)

        if text.startswith('\r'):
            cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            cursor.deleteChar()
            self.console_output.insertPlainText(text.lstrip('\r'))
        else:
            self.console_output.insertPlainText(text)

        self.console_output.moveCursor(QTextCursor.End)
        QApplication.processEvents()

    def _add_inner_form(self, tab_widget, name, section_key, data):
        widget = QWidget()
        layout = QFormLayout(widget)
        for k, v in data.items():
            label = QLabel(k)
            widget_field = self._get_widget_for_value(k, v)
            layout.addRow(label, widget_field)
            self.entries.setdefault(section_key, {})[k] = widget_field
        tab_widget.addTab(widget, name)

    def _add_doc_tab(self, doc):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        if isinstance(doc, dict):
            doc_tabs = QTabWidget()
            for sec, content in doc.items():
                page = QWidget()
                page_layout = QVBoxLayout(page)
                text = QTextEdit()
                text.setReadOnly(True)
                text.setPlainText(str(content))
                page_layout.addWidget(text)
                doc_tabs.addTab(page, sec)
            layout.addWidget(doc_tabs)
        else:
            text = QTextEdit()
            text.setReadOnly(True)
            text.setPlainText(str(doc))
            layout.addWidget(text)

        self.tabs.addTab(tab, "Documentation")

    def _parse_value(self, key, widget):
        if isinstance(widget, QTextEdit):
            val = widget.toPlainText().strip()
        elif isinstance(widget, QComboBox):
            val = widget.currentText().strip()
        else:
            val = widget.text().strip()

        if key.lower() == "order":
            return val
        if val.lower() in ('none', 'null', ''):
            return None
        if val.lower() in ('true', 'false'):
            return val.lower() == 'true'

        # Try numeric types
        for caster in (int, float):
            try:
                return caster(val)
            except ValueError:
                continue

        # Clean redundant triple/surrounding quotes (e.g. '''mean','std''' -> 'mean','std')
        if (val.startswith("[") and val.endswith("]")) or \
        (val.startswith("{") and val.endswith("}")) or \
        (val.startswith("(") and val.endswith(")")):
            try:
                return ast.literal_eval(val)
            except Exception:
                pass  # If eval fails, fall back to raw string

        return val

    def _simple_validate(self):
        for section_key, widgets_dict in self.entries.items():
            for key, widget in widgets_dict.items():
                value = self._parse_value(key, widget)

                expected_type = self.expected_types[key]

                if not isinstance(value, expected_type):
                    if isinstance(expected_type, tuple):
                        noms_types = ", ".join(t.__name__ for t in expected_type)
                    else:
                        noms_types = expected_type.__name__
                    QMessageBox.warning(
                        self, "Incorrect type",
                        f"For the key '{key}' :\n"
                        f"We wanted those types {noms_types} but you pick"
                        f"{type(value).__name__}.\nFor this value : {value!r}"
                    )
                    return False
        return True

    def _on_save(self):
        if not self._simple_validate():
            return
        
        new = {}
        if 'documentation' in self.config_data:
            new['documentation'] = self.config_data['documentation']

        for sec, its in self.entries.items():
            if sec == '__general__':
                # Pour les clés générales (non-nested)
                for k, w in its.items():
                    new[k] = self._parse_value(k, w)
            else:
                # Pour les sections imbriquées, par ex "NAS__some_subsection"
                keys = sec.split('__')
                target = new
                for key in keys[:-1]:
                    target = target.setdefault(key, {})
                # On construit le dict final pour cette sous-section
                target[keys[-1]] = {
                    k: self._parse_value(k, w)
                    for k, w in its.items()
                }

        # Réassembler "documentation" en fin de fichier si nécessaire
        try:
            doc = new.pop('documentation', None)
            ordered = dict(new)
            if doc is not None:
                ordered['documentation'] = doc

            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    force_inline_lists(ordered),
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    width=4096
                )
            QMessageBox.information(self, "Saved", "Configuration saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config:\n{e}")

    def _run_script(self, script):
        self._on_save()
        if not os.path.isfile(script):
            QMessageBox.warning(self, "Missing", f"Script not found: {script}")
            return
        ext = os.path.splitext(script)[1].lower()
        if ext == ".sh":
            cmd = ["bash", script]
        elif ext == ".py":
            cmd = ["python", script, "--file", CONFIG_PATH]
        else:
            QMessageBox.warning(self, "Unsupported", f"Unsupported script type: {ext}")
            return

        self._append_console(f"\n$ {' '.join(shlex.quote(arg) for arg in cmd)}\n{'=' * 60}\n")
        self.script_thread = ScriptRunnerThread(cmd)
        self.script_thread.output_signal.connect(self._append_console)
        self.script_thread.finished_signal.connect(lambda success, code: self._on_script_finished(script, success, code))
        self.script_thread.start()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    try:
        with open("./SCRIPT/style.qss") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Impossible to download the style file : {e}")
    
    window = MosnaGUI()
    window.resize(2000, 1600)
    window.show()
    sys.exit(app.exec())