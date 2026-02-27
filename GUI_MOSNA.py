import os
import re
import sys
import yaml
import ast
import subprocess
import shlex
from pathlib import Path
from yaml.representer import SafeRepresenter
import markdown

from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QMessageBox,
    QPushButton, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QLineEdit,
    QTextEdit, QFormLayout, QComboBox, QProgressBar, QTextBrowser
)
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtCore import QUrl

BASE_DIR = Path(__file__).resolve().parent

CONFIG_PATH = str(BASE_DIR / 'CONFIG' / 'configuration.yaml')
DOC_HTML_PATH = BASE_DIR / "DOC" / "documentation.html"
SCRIPTS = [
    str(BASE_DIR / 'package' / 'tysserand_network.py'),
    str(BASE_DIR / 'package' / 'assortativity.py'),
    str(BASE_DIR / 'package' / 'niche_analysis.py'),
    str(BASE_DIR / 'package' / 'clear_temporary_files.sh'),
]

class ScriptRunnerThread(QThread):
    finished_signal = Signal(bool, int, str)
    output_line = Signal(str)  # Nouvelle sortie temps réel

    def __init__(self, command, cwd=None, env=None):
        super().__init__()
        self.command = command
        self.cwd = cwd
        self.env = env

    def run(self):
        try:
            proc = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.cwd,
                env=self.env,
                bufsize=1,
                universal_newlines=True
            )

            collected = []

            # Lecture temps réel
            if proc.stdout is not None:
                for line in proc.stdout:
                    line = line.rstrip("\n")
                    collected.append(line)
                    self.output_line.emit(line)

            returncode = proc.wait()
            output = "\n".join(collected)
            success = (returncode == 0)
            self.finished_signal.emit(success, returncode, output)

        except Exception as e:
            self.finished_signal.emit(False, -1, f"Error while running the command: {e}")
class FlowStyleList(list):
    pass

def represent_flow_style_list(dumper, data):
    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

yaml.add_representer(FlowStyleList, represent_flow_style_list, Dumper=yaml.SafeDumper)

def force_inline_lists(obj):
    if isinstance(obj, dict):
        return {k: force_inline_lists(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return FlowStyleList(force_inline_lists(i) for i in obj)
    return obj

class MosnaGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mosna Analysis GUI")
        self.working_dir = None
        self.working_dir_label = None

        self.config_data = {}
        self.entries = {}
        self.script_thread = None

        self._load_config()
        self._build_ui()
        self._set_ui_enabled(False)
        QTimer.singleShot(0, self._ask_working_dir_at_start)

        self.expected_types = {

            ### Tysserand features ###
            "Nodes directory":(str, type(None)),
            "CPU": (int, type(None)),
            "Edges method": (str, type(None)),
            "Min neighbors": (int, type(None)),
            "Extension":(str, type(None)),
            "X coordinates column":(str, type(None)),
            "Y coordinates column":(str, type(None)),
            "Phenotype column":(str, type(None)),
            "Patient column name":(str, type(None)),
            "Sample column name":(str, type(None)),

            ### Assortativity features ###
            "Network_directory": (str, type(None)),
            "Phenotype column":(str, type(None)),
            "Index":(str, type(None)),

            ### NAS ###
            "Niches method": (str, type(None)),
            "Processing method":(str, type(None)),
            "order": (str, type(None)),
            "stat_funcs": (str, type(None)),
            "stat_names": (list, type(None)),
            "clusterer_type": (str, type(None)),
            "n_clusters": (int, type(None)),
            "reducer_type": (str, type(None)),
            "metric": (str, type(None)),
            "resolution": (float, type(None)),
            "n_neighbors": (int, type(None)),
            "min_dist": (float, type(None)),
            "dim_clust": (int, type(None)),
            "min_cluster_size": (int, type(None)),
            "k_cluster": (int, type(None)),
            "normalize": (str, type(None)),
        }

    def _on_script_finished(self, script, success, returncode, output):
        self._progress_stop(success)
        base = os.path.basename(script)

        if success:
            QMessageBox.information(self, "Success", f"Script completed: {base}")
            return

        # En cas d'échec, on affiche un extrait lisible.
        # Ça évite un “terminal” permanent dans l'UI, mais garde l'info utile.
        max_chars = 6000
        output = (output or "").strip()
        if len(output) > max_chars:
            output = output[:max_chars] + "\n\n[Output truncated...]"

        QMessageBox.critical(
            self,
            "Error",
            f"Script failed: {base}\nExit code: {returncode}\n\nOutput:\n{output}"
        )
    
    def _set_ui_enabled(self, enabled: bool):

            if hasattr(self, "tabs"):
                self.tabs.setEnabled(enabled)

            # Si tu as gardé des boutons de scripts, on les désactive aussi
            if hasattr(self, "run_buttons"):
                for b in self.run_buttons:
                    b.setEnabled(enabled)

            if hasattr(self, "save_btn"):
                self.save_btn.setEnabled(enabled)

    def _ask_working_dir_at_start(self):
        """
        Forçage au démarrage : sans dossier de travail, on ne laisse pas l'utilisateur avancer.
        """
        ok = self.choose_working_dir(mandatory=True)
        if not ok:
            self.close()
            return

        self._set_ui_enabled(True)

    def _add_html_doc_tab_textedit(self, html_path: Path, tab_title: str = "Documentation"):
        """
        J'affiche un fichier HTML externe dans un QTextBrowser.
        Ce widget est adapté à l'affichage HTML avec gestion des liens.
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)

        view = QTextBrowser()
        view.setReadOnly(True)
        view.setOpenExternalLinks(True)  # Les liens s'ouvrent dans le navigateur système

        if html_path.exists():
            # setSource permet à Qt de gérer correctement les chemins relatifs (CSS, images)
            view.setSource(QUrl.fromLocalFile(str(html_path.resolve())))
        else:
            view.setHtml(f"<h1>Documentation</h1><p>Fichier introuvable : {html_path}</p>")

        layout.addWidget(view)
        self.tabs.addTab(tab, tab_title)

    def choose_working_dir(self, mandatory=False) -> bool:
        """
        Ouvre un QFileDialog pour définir le dossier de travail.
        Le chemin de config reste celui de l'application, on ne le déplace pas.
        """
        selected = QFileDialog.getExistingDirectory(self, "Choisir un dossier de travail")
        if not selected:
            if mandatory:
                QMessageBox.warning(
                    self,
                    "Dossier requis",
                    "Vous devez choisir un dossier de travail pour continuer."
                )
            return False

        self.working_dir = str(Path(selected).expanduser().resolve())

        if self.working_dir_label is not None:
            self.working_dir_label.setText(f"Working directory : {self.working_dir}")

        return True

    def _load_config(self):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                raw = yaml.safe_load(f) or {}
                if not raw:
                    QMessageBox.warning(
                        self,
                        "Empty Config",
                        "The configuration file is empty. Please check the file."
                    )
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

        if lower_key in ['niches method'] and isinstance(value, str):
            options = ['NAS', "SCAN-IT"]
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        if lower_key in ['processing method'] and isinstance(value, str):
            options = ['Aggregated nodes','Per sample' ,'both']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        if lower_key in ['reducer_type'] and isinstance(value, str):
            options = ['umap']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo

        if lower_key in ['clusterer_type'] and isinstance(value, str):
            options = ['leiden', 'ecg', 'spectral', 'gmm', 'hdbscan']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo

        if lower_key in ['order'] and isinstance(value, str):
            options = ['1', '2']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo

        if lower_key in ['metric'] and isinstance(value, str):
            options = ['manhattan', 'euclidean', 'cosine']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo

        if lower_key in ['edges method'] and isinstance(value, str):
            options = ['delaunay', 'knn']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo
        
        if lower_key in ['extension'] and isinstance(value, str):
            options = ['csv', 'parquet']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo

        if lower_key == "sample column name":
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)

            mode = QComboBox()
            mode.addItems(["None", "Custom"])

            edit = QLineEdit()

            if value is None:
                mode.setCurrentText("None")
                edit.setText("")
                edit.setEnabled(False)
            else:
                mode.setCurrentText("Custom")
                edit.setText(str(value))
                edit.setEnabled(True)

            def toggle_mode():
                is_custom = (mode.currentText() == "Custom")
                edit.setEnabled(is_custom)
                if not is_custom:
                    edit.setText("")

            mode.currentIndexChanged.connect(toggle_mode)

            layout.addWidget(mode)
            layout.addWidget(edit)

            container._mode_combo = mode
            container._value_edit = edit

            return container   

        if lower_key in ['network directory']:
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)

            combo = QComboBox()
            combo.addItems(['Default', 'Custom'])

            path_edit = QLineEdit()
            browse_btn = QPushButton("Browse")

            if value is None:
                combo.setCurrentText('Default')
                path_edit.setEnabled(False)
                browse_btn.setEnabled(False)
            else:
                combo.setCurrentText('Custom')
                path_edit.setText(str(value))

            def toggle_mode():
                is_custom = combo.currentText() == 'Custom'
                path_edit.setEnabled(is_custom)
                browse_btn.setEnabled(is_custom)

            combo.currentIndexChanged.connect(toggle_mode)

            def browse():
                selected = QFileDialog.getExistingDirectory(self, "Select folder")
                if selected:
                    path_edit.setText(selected)

            browse_btn.clicked.connect(browse)

            layout.addWidget(combo)
            layout.addWidget(path_edit)
            layout.addWidget(browse_btn)

            container._combo = combo
            container._path_edit = path_edit

            return container
        
        if lower_key in ['nodes directory']:
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)

            path_edit = QLineEdit(str(value) if value else "")
            browse_btn = QPushButton("Browse")

            def browse():
                selected = QFileDialog.getExistingDirectory(self, "Select folder")
                if selected:
                    path_edit.setText(selected)

            browse_btn.clicked.connect(browse)

            layout.addWidget(path_edit)
            layout.addWidget(browse_btn)

            container._path_edit = path_edit

            return container

        if lower_key in ['stat_funcs'] and isinstance(value, str):
            options = ['np.mean,np.std', 'np.mean']
            combo = QComboBox()
            combo.addItems(options)
            if value in options:
                combo.setCurrentText(value)
            return combo

        if lower_key in ['normalize'] and isinstance(value, str):
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

    def _on_script_output_line(self, line: str):
        if not line:
            return
        
        if line.startswith("[QT_INFO]"):
            msg = line.replace("[QT_INFO]", "").strip()
            if msg:
                self.run_status_label.setText(msg)
            return

        if line.startswith("[QT_PROGRESS]"):
            payload = line.replace("[QT_PROGRESS]", "").strip()

            m_cur = re.search(r"current=(\d+)", payload)
            m_tot = re.search(r"total=(\d+)", payload)

            if not (m_cur and m_tot):
                return

            current = int(m_cur.group(1))
            total = int(m_tot.group(1))

            m_desc = re.search(r"desc=(.*)$", payload)
            desc = m_desc.group(1).strip() if m_desc else ""
            if desc:
                self.run_status_label.setText(desc)

            if total > 0:
                if self.run_progress.maximum() != total:
                    self.run_progress.setRange(0, total)
                self.run_progress.setValue(min(current, total))

            return

    def _build_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        self.working_dir_label = QLabel("Working directory : non défini")
        self.working_dir_label.setStyleSheet(
            "padding: 6px; background-color: #f2f2f2; border: 1px solid #d0d0d0;"
        )

        layout.addWidget(self.working_dir_label)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, stretch=1)

        self._add_html_doc_tab_textedit(DOC_HTML_PATH, tab_title="Documentation")
        order = ['Tysserand', 'Assortativity', 'NAS']

        """
        general_data = {
            k: v for k, v in self.config_data.items()
            if not isinstance(v, dict) and k != 'documentation' and k != 'silent'
        }
        self._add_tab("General", "__general__", general_data)
        """

        for key in order:
            if key == "documentation" and "documentation" in self.config_data:
                self._add_doc_tab(self.config_data['documentation'])
            elif key in self.config_data and isinstance(self.config_data[key], dict):
                self._add_nested_tab(key, self.config_data[key])

        for sec, data in self.config_data.items():
            if sec not in order and isinstance(data, dict):
                self._add_nested_tab(sec, data)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.run_buttons = []
        for s in SCRIPTS:
            b = QPushButton(f"Run {os.path.splitext(os.path.basename(s))[0].replace('_', ' ').upper()}")
            b.clicked.connect(lambda _, sc=s: self._run_script(sc))
            btn_layout.addWidget(b)
            self.run_buttons.append(b)

        self.save_btn = QPushButton("Save Config")
        self.save_btn.clicked.connect(self._on_save)
        layout.addWidget(self.save_btn)

        self.run_status_label = QLabel("Aucun script en cours")
        self.run_status_label.setStyleSheet("padding: 6px;")

        self.run_progress = QProgressBar()
        self.run_progress.setVisible(True)

        self.run_progress.setRange(0, 1)
        self.run_progress.setValue(0)

        self.run_status_label.setObjectName("RunStatusLabel")
        self.run_progress.setObjectName("RunProgressBar")

        layout.addWidget(self.run_status_label)
        layout.addWidget(self.run_progress)

    def _add_tab(self, tab_name, section_key, data):
        tab = QWidget()
        form_layout = QFormLayout(tab)

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
                        self._add_inner_form(
                            deep_tabs,
                            subsub,
                            f"{section}__nodes_aggregation__{subsub}",
                            subsubdata
                        )
                    inner_tabs.addTab(nested, "nodes_aggregation")
                else:
                    self._add_inner_form(inner_tabs, subsec, f"{section}__{subsec}", subdata)

        self.tabs.addTab(tab, section)

    def _add_inner_form(self, tab_widget, name, section_key, data):
        widget = QWidget()
        layout = QFormLayout(widget)
        for k, v in data.items():
            label = QLabel(k)
            widget_field = self._get_widget_for_value(k, v)
            layout.addRow(label, widget_field)
            self.entries.setdefault(section_key, {})[k] = widget_field
        tab_widget.addTab(widget, name)

    def _progress_start(self, title: str):
        self.run_status_label.setText(title)
        self.run_progress.setRange(0, 0)

    def _progress_stop(self, success: bool):
        self.run_progress.setRange(0, 100)
        self.run_progress.setValue(100 if success else 0)

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

        if hasattr(widget, "_path_edit"):
            return widget._path_edit.text().strip() or None

        if hasattr(widget, "_combo") and hasattr(widget, "_path_edit"):
            if widget._combo.currentText() == "Default":
                return None
            return widget._path_edit.text().strip() or None
        
        if hasattr(widget, "_mode_combo") and hasattr(widget, "_value_edit"):
            mode = widget._mode_combo.currentText().strip()
            if mode == "None":
                return None
            txt = widget._value_edit.text().strip()
            return txt if txt != "" else None

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

        for caster in (int, float):
            try:
                return caster(val)
            except ValueError:
                continue

        if (val.startswith("[") and val.endswith("]")) or \
           (val.startswith("{") and val.endswith("}")) or \
           (val.startswith("(") and val.endswith(")")):
            try:
                return ast.literal_eval(val)
            except Exception:
                pass

        return val

    def _simple_validate(self):
        for section_key, widgets_dict in self.entries.items():
            for key, widget in widgets_dict.items():
                value = self._parse_value(key, widget)
                expected_type = self.expected_types.get(key)

                if expected_type is None:
                    continue

                if not isinstance(value, expected_type):
                    if isinstance(expected_type, tuple):
                        noms_types = ", ".join(t.__name__ for t in expected_type)
                    else:
                        noms_types = expected_type.__name__

                    QMessageBox.warning(
                        self,
                        "Incorrect type",
                        f"For the key '{key}' :\n"
                        f"We wanted those types {noms_types} but you picked {type(value).__name__}.\n"
                        f"For this value : {value!r}"
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
                for k, w in its.items():
                    new[k] = self._parse_value(k, w)
            else:
                keys = sec.split('__')
                target = new
                for key in keys[:-1]:
                    target = target.setdefault(key, {})
                target[keys[-1]] = {k: self._parse_value(k, w) for k, w in its.items()}

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

        if self.working_dir is None:
            QMessageBox.warning(self, "Missing working directory", "Please choose a working directory first.")
            return

        if not os.path.isfile(script):
            QMessageBox.warning(self, "Missing", f"Script not found: {script}")
            return

        ext = os.path.splitext(script)[1].lower()
        if ext == ".sh":
            cmd = ["bash", script]
        elif ext == ".py":
            script_path = Path(script)
            rel = script_path.relative_to(BASE_DIR)
            module = ".".join(rel.with_suffix("").parts)
            cmd = ["python", "-m", module, "--file", CONFIG_PATH, "--working_dir", self.working_dir]
        else:
            QMessageBox.warning(self, "Unsupported", f"Unsupported script type: {ext}")
            return
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        prefix = str(BASE_DIR)
        env["PYTHONPATH"] = prefix if not existing else prefix + os.pathsep + existing

        env["ENABLE_QT_PROGRESS"] = "1"
        base = os.path.basename(script)
        self._progress_start(f"Script en cours : {base}")

        self.script_thread = ScriptRunnerThread(cmd, cwd=self.working_dir, env=env)

        # Connexion temps réel : indispensable pour mettre à jour le statut et la barre
        self.script_thread.output_line.connect(self._on_script_output_line)

        self.script_thread.finished_signal.connect(
            lambda success, code, out: self._on_script_finished(script, success, code, out)
        )

        self.script_thread.start()
  
if __name__ == '__main__':
    app = QApplication(sys.argv)

    try:
        with open("./package/style.qss", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Impossible to download the style file : {e}")

    window = MosnaGUI()
    window.resize(1000, 800)
    window.show()
    sys.exit(app.exec())