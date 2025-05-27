import os
import sys
import yaml
import ast
import subprocess

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox,
    QPushButton, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QLineEdit,
    QTextEdit, QFormLayout, QScrollArea
)
from PySide6.QtCore import Qt

CONFIG_PATH = 'CONFIG/configuration.yaml'
SCRIPTS = [
    'pre_processing.sh',
    'draw_tysserand_IMC_IF.sh',
    'mosna_assortativity.sh',
    'mosna_NAS.sh'
]

class MosnaGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mosna Analysis GUI")

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

        run_all_btn = QPushButton("Run All Scripts")
        run_all_btn.clicked.connect(self._run_all_scripts)
        btn_layout.addWidget(run_all_btn)

        for s in reversed(SCRIPTS):
            b = QPushButton(f"Run {os.path.basename(s)}")
            b.clicked.connect(lambda _, sc=s: self._run_script(sc))
            btn_layout.addWidget(b)

        save_btn = QPushButton("Save Config")
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

    def _add_tab(self, tab_name, section_key, data):
        tab = QWidget()
        form_layout = QFormLayout(tab)
        tab.setLayout(form_layout)

        for k, v in data.items():
            label = QLabel(k)
            if isinstance(v, str) and ('\n' in v or '\t' in v):
                widget = QTextEdit()
                widget.setPlainText(v)
            else:
                widget = QLineEdit(str(v))
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
            self._add_inner_form(inner_tabs, "General", f"{section}__general", general)

        for subsec, subdata in data.items():
            if isinstance(subdata, dict):
                if section == "NAS" and subsec == "nodes_aggregation":
                    nested = QWidget()
                    nested_layout = QVBoxLayout(nested)
                    deep_tabs = QTabWidget()
                    nested_layout.addWidget(deep_tabs)
                    for subsub, subsubdata in subdata.items():
                        self._add_inner_form(deep_tabs, subsub, f"nodes_aggregation__{subsub}", subsubdata)
                    inner_tabs.addTab(nested, "nodes_aggregation")
                else:
                    self._add_inner_form(inner_tabs, subsec, f"{section}__{subsec}", subdata)

        self.tabs.addTab(tab, section)

    def _add_inner_form(self, tab_widget, name, section_key, data):
        widget = QWidget()
        layout = QFormLayout(widget)
        for k, v in data.items():
            label = QLabel(k)
            if isinstance(v, str) and ('\n' in v or '\t' in v):
                widget_field = QTextEdit()
                widget_field.setPlainText(v)
            else:
                widget_field = QLineEdit(str(v))
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

    def _parse_value(self, widget):
        if isinstance(widget, QTextEdit):
            return widget.toPlainText()
        val = widget.text().strip()
        if val.lower() in ('none', 'null', ''):
            return None
        if val.lower() in ('true', 'false'):
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
            else:
                keys = sec.split('__')
                target = new
                for key in keys[:-1]:
                    target = target.setdefault(key, {})
                target[keys[-1]] = {k: self._parse_value(w) for k, w in its.items()}
        self.config_data = new
        try:
            doc = self.config_data.pop('documentation', None)
            ordered = dict(self.config_data)
            if doc is not None:
                ordered['documentation'] = doc
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    ordered,
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
        try:
            subprocess.check_call(['bash', script])
            QMessageBox.information(self, "Success", f"Script completed: {os.path.basename(script)}")
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"Script failed: {script}\n{e}")

    def _run_all_scripts(self):
        self._on_save()
        for s in SCRIPTS:
            if not os.path.isfile(s):
                QMessageBox.warning(self, "Missing", f"Script not found: {s}")
                continue
            try:
                subprocess.check_call(['bash', s])
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self, "Error", f"Script failed: {s}\n{e}")
                return
        QMessageBox.information(self, "Done", "All scripts completed successfully.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MosnaGUI()
    window.resize(1000, 800)
    window.show()
    sys.exit(app.exec())
