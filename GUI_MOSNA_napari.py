from pathlib import Path
import os
import re
import sys
import ast
import time
import subprocess

import yaml
import pandas as pd

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "CONFIG" / "configuration.yaml"
DOC_HTML_PATH = BASE_DIR / "assets" / "documentation.html"

SCRIPTS = [
    BASE_DIR / "package" / "tysserand_network.py",
    BASE_DIR / "package" / "assortativity.py",
    BASE_DIR / "package" / "niche_analysis.py",
    BASE_DIR / "package" / "clear_temporary.py",
]


class FlowStyleList(list):
    pass


def represent_flow_style_list(dumper, data):
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq", data, flow_style=True
    )


yaml.add_representer(FlowStyleList, represent_flow_style_list, Dumper=yaml.SafeDumper)


def force_inline_lists(obj):
    if isinstance(obj, dict):
        return {k: force_inline_lists(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return FlowStyleList(force_inline_lists(i) for i in obj)
    return obj


def find_sample(net_dir, extension, patient_column_name, sample_column_name=None):
    """
    Cette fonction reprend la logique du fichier find_sample.py.
    Ici, les noms des paramètres correspondent réellement au rôle qu'ils jouent.
    Le dossier net_dir doit être un objet Path.
    """
    if sample_column_name is None:
        nodes_files = sorted(net_dir.glob(f"nodes_{patient_column_name}-*.{extension}"))
    else:
        nodes_files = sorted(
            net_dir.glob(f"nodes_{patient_column_name}-*_{sample_column_name}-*.{extension}")
        )
    return nodes_files


class ScriptRunnerThread(QThread):
    finished_signal = Signal(bool, int, str, float)
    output_line = Signal(str)

    def __init__(self, command, cwd=None, env=None):
        super().__init__()
        self.command = command
        self.cwd = cwd
        self.env = env

    def run(self):
        start_time = time.perf_counter()
        try:
            proc = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.cwd,
                env=self.env,
                bufsize=1,
                universal_newlines=True,
            )

            stdout_lines = []
            if proc.stdout:
                for line in proc.stdout:
                    line = line.rstrip("\n")
                    stdout_lines.append(line)
                    self.output_line.emit(line)

            stderr_output = proc.stderr.read() if proc.stderr else ""
            returncode = proc.wait()
            success = returncode == 0

            if success:
                output = "\n".join(stdout_lines)
            else:
                error_lines = [l.strip() for l in stderr_output.splitlines() if l.strip()]
                if not error_lines:
                    error_lines = [l.strip() for l in stdout_lines if l.strip()]

                output = "Erreur inconnue."
                for line in reversed(error_lines):
                    if (
                        line != "Traceback (most recent call last):"
                        and "[QT_PROGRESS]" not in line
                        and not line.startswith("[INFO]")
                    ):
                        output = line
                        break

            elapsed = time.perf_counter() - start_time
            self.finished_signal.emit(success, returncode, output, elapsed)

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            self.finished_signal.emit(False, -1, f"Error while running: {e}", elapsed)


class BrowserPanel(QWidget):
    """
    Le panneau de gauche contient uniquement les paramètres utiles pour découvrir
    les fichiers à partir de la structure décrite dans le YAML.

    Il ne sert pas à lancer les analyses. Il prépare les chemins et la sélection.
    """

    sampleSelected = Signal(dict)
    browserConfigChanged = Signal(dict)

    def __init__(self, config_data, parent=None):
        super().__init__(parent)
        self.config_data = config_data
        self._current_results = []
        self._build()
        self.load_from_config()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QLabel("🔎 Browser")
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        source_group = QGroupBox("Data sources")
        source_form = QFormLayout(source_group)

        self.nodes_dir_edit = QLineEdit()
        self.nodes_dir_btn = QPushButton("…")
        self.nodes_dir_btn.setMaximumWidth(32)
        nodes_row = QWidget()
        nodes_row_layout = QHBoxLayout(nodes_row)
        nodes_row_layout.setContentsMargins(0, 0, 0, 0)
        nodes_row_layout.addWidget(self.nodes_dir_edit)
        nodes_row_layout.addWidget(self.nodes_dir_btn)
        source_form.addRow("Nodes directory", nodes_row)

        self.network_dir_edit = QLineEdit()
        self.network_dir_btn = QPushButton("…")
        self.network_dir_btn.setMaximumWidth(32)
        network_row = QWidget()
        network_row_layout = QHBoxLayout(network_row)
        network_row_layout.setContentsMargins(0, 0, 0, 0)
        network_row_layout.addWidget(self.network_dir_edit)
        network_row_layout.addWidget(self.network_dir_btn)
        source_form.addRow("Network directory", network_row)

        self.extension_combo = QComboBox()
        self.extension_combo.addItems(["csv", "parquet", "tsv"])
        source_form.addRow("Extension", self.extension_combo)

        layout.addWidget(source_group)

        naming_group = QGroupBox("Pattern used to find files")
        naming_form = QFormLayout(naming_group)

        self.patient_column_edit = QLineEdit()
        self.sample_column_edit = QLineEdit()
        naming_form.addRow("Patient column name", self.patient_column_edit)
        naming_form.addRow("Sample column name", self.sample_column_edit)
        layout.addWidget(naming_group)

        filter_group = QGroupBox("Optional filters")
        filter_form = QFormLayout(filter_group)
        self.patient_value_edit = QLineEdit()
        self.sample_value_edit = QLineEdit()
        self.patient_value_edit.setPlaceholderText("Exemple : patient01")
        self.sample_value_edit.setPlaceholderText("Exemple : sample01")
        filter_form.addRow("Patient value", self.patient_value_edit)
        filter_form.addRow("Sample value", self.sample_value_edit)
        layout.addWidget(filter_group)

        actions = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh list")
        self.apply_btn = QPushButton("Apply to config")
        actions.addWidget(self.refresh_btn)
        actions.addWidget(self.apply_btn)
        layout.addLayout(actions)

        list_group = QGroupBox("Files found")
        list_layout = QVBoxLayout(list_group)
        self.results_label = QLabel("No file discovered yet.")
        self.sample_combo = QComboBox()
        self.sample_combo.setEnabled(False)
        list_layout.addWidget(self.results_label)
        list_layout.addWidget(self.sample_combo)
        layout.addWidget(list_group)

        layout.addStretch()

        self.nodes_dir_btn.clicked.connect(lambda: self._browse_dir(self.nodes_dir_edit, "Choose nodes directory"))
        self.network_dir_btn.clicked.connect(lambda: self._browse_dir(self.network_dir_edit, "Choose network directory"))
        self.refresh_btn.clicked.connect(self.refresh_files)
        self.apply_btn.clicked.connect(self.emit_browser_config)
        self.sample_combo.currentIndexChanged.connect(self._emit_selected_sample)

    def _browse_dir(self, line_edit, title):
        path = QFileDialog.getExistingDirectory(self, title)
        if path:
            line_edit.setText(path)

    def load_from_config(self):
        tys = self.config_data.get("Tysserand", {})
        assort = self.config_data.get("Assortativity", {})

        self.nodes_dir_edit.setText(str(tys.get("Nodes directory") or ""))

        network_dir = assort.get("Network directory")
        if network_dir in (None, "Default"):
            network_dir = ""
        self.network_dir_edit.setText(str(network_dir or ""))

        extension = tys.get("Extension") or assort.get("Extension") or "parquet"
        idx = self.extension_combo.findText(str(extension))
        if idx >= 0:
            self.extension_combo.setCurrentIndex(idx)

        self.patient_column_edit.setText(str(tys.get("Patient column name") or ""))
        self.sample_column_edit.setText(str(tys.get("Sample column name") or ""))

    def get_browser_values(self):
        return {
            "nodes_directory": self.nodes_dir_edit.text().strip() or None,
            "network_directory": self.network_dir_edit.text().strip() or None,
            "extension": self.extension_combo.currentText().strip(),
            "patient_column_name": self.patient_column_edit.text().strip() or None,
            "sample_column_name": self.sample_column_edit.text().strip() or None,
            "patient_value": self.patient_value_edit.text().strip() or None,
            "sample_value": self.sample_value_edit.text().strip() or None,
        }

    def emit_browser_config(self):
        self.browserConfigChanged.emit(self.get_browser_values())

    def refresh_files(self):
        values = self.get_browser_values()
        nodes_directory = values["nodes_directory"]
        extension = values["extension"]
        patient_column_name = values["patient_column_name"]
        sample_column_name = values["sample_column_name"]
        patient_value = values["patient_value"]
        sample_value = values["sample_value"]

        if not nodes_directory or not os.path.isdir(nodes_directory):
            QMessageBox.warning(self, "Invalid path", "Nodes directory must be a valid folder.")
            return

        if not patient_column_name:
            QMessageBox.warning(self, "Missing value", "Patient column name is required to build the filename pattern.")
            return

        nodes_dir = Path(nodes_directory)
        selected_sample_name = sample_column_name if sample_column_name else None
        nodes_files = find_sample(nodes_dir, extension, patient_column_name, selected_sample_name)

        filtered_results = []
        for nodes_path in nodes_files:
            meta = self._build_metadata_from_nodes(nodes_path, values)
            if meta is None:
                continue

            if patient_value and patient_value.lower() not in (meta.get("patient_value") or "").lower():
                continue
            if sample_value and sample_value.lower() not in (meta.get("sample_value") or "").lower():
                continue

            filtered_results.append(meta)

        self._current_results = filtered_results
        self.sample_combo.clear()

        if not filtered_results:
            self.results_label.setText("No file matches the current pattern.")
            self.sample_combo.setEnabled(False)
            return

        for meta in filtered_results:
            label = meta["label"]
            self.sample_combo.addItem(label, userData=meta)

        self.results_label.setText(f"{len(filtered_results)} file(s) found.")
        self.sample_combo.setEnabled(True)
        self._emit_selected_sample()

    def _build_metadata_from_nodes(self, nodes_path, browser_values):
        nodes_path = Path(nodes_path)
        extension = browser_values["extension"]
        network_directory = browser_values["network_directory"]
        sample_column_name = browser_values["sample_column_name"]

        patient_value, sample_value = self._extract_patient_sample_from_name(
            nodes_path.stem,
            browser_values["patient_column_name"],
            sample_column_name,
        )

        edges_path = None
        if network_directory and Path(network_directory).is_dir():
            candidate_name = self._build_edges_name(nodes_path.name)
            candidate_path = Path(network_directory) / candidate_name
            if candidate_path.exists():
                edges_path = candidate_path

        label = patient_value or nodes_path.stem
        if sample_value:
            label = f"{label} / {sample_value}"

        return {
            "label": label,
            "nodes_path": str(nodes_path),
            "edges_path": str(edges_path) if edges_path else "",
            "patient_value": patient_value,
            "sample_value": sample_value,
            "extension": extension,
        }

    def _extract_patient_sample_from_name(self, stem, patient_column_name, sample_column_name):
        """
        La logique de nommage supposée est du type :
        nodes_patient-XXX_sample-YYY
        ou, si sample est absent :
        nodes_patient-XXX
        """
        stem = stem.removeprefix("nodes_")
        patient_value = None
        sample_value = None

        patient_pattern = rf"{re.escape(patient_column_name)}-([^_]+)"
        patient_match = re.search(patient_pattern, stem)
        if patient_match:
            patient_value = patient_match.group(1)

        if sample_column_name:
            sample_pattern = rf"{re.escape(sample_column_name)}-([^_]+)"
            sample_match = re.search(sample_pattern, stem)
            if sample_match:
                sample_value = sample_match.group(1)

        return patient_value, sample_value

    def _build_edges_name(self, nodes_filename):
        if nodes_filename.startswith("nodes_"):
            return "edges_" + nodes_filename[len("nodes_"):]
        return nodes_filename.replace("nodes", "edges", 1)

    def _emit_selected_sample(self):
        idx = self.sample_combo.currentIndex()
        if idx < 0:
            return
        meta = self.sample_combo.itemData(idx)
        if meta:
            self.sampleSelected.emit(meta)

    def get_selected_meta(self):
        idx = self.sample_combo.currentIndex()
        if idx < 0:
            return None
        return self.sample_combo.itemData(idx)


class ImageViewerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("🖼 Viewer")
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        self._stack = QStackedWidget()
        self._placeholder = QLabel("No output to display.\nRun a script to generate images.")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._stack.addWidget(self._placeholder)

        self._img_tabs = QTabWidget()
        self._stack.addWidget(self._img_tabs)
        layout.addWidget(self._stack, stretch=1)

        self._status_label = QLabel("No script running.")
        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        layout.addWidget(self._status_label)
        layout.addWidget(self._progress)

    def show_image(self, path, title=None):
        pix = QPixmap(path)
        if pix.isNull():
            return

        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setPixmap(pix.scaled(900, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        scroll = QScrollArea()
        scroll.setWidget(label)
        scroll.setWidgetResizable(True)

        self._img_tabs.addTab(scroll, title or Path(path).stem)
        self._stack.setCurrentIndex(1)

    def clear_images(self):
        while self._img_tabs.count():
            self._img_tabs.removeTab(0)
        self._stack.setCurrentIndex(0)

    def set_status(self, text):
        self._status_label.setText(text)

    def set_progress(self, current, total):
        if total > 0:
            if self._progress.maximum() != total:
                self._progress.setRange(0, total)
            self._progress.setValue(min(current, total))

    def progress_start(self, title):
        self._status_label.setText(title)
        self._progress.setRange(0, 0)

    def progress_stop(self, success):
        self._progress.setRange(0, 100)
        self._progress.setValue(100 if success else 0)


class ParametersPanel(QWidget):
    """
    Ici, on garde tous les autres paramètres du YAML.
    Les paramètres du browser ont été sortis volontairement pour éviter les doublons.
    """

    COLUMN_FIELDS = {
        "X coordinates column",
        "Y coordinates column",
        "Phenotype column",
        "X coordinates column for niches",
        "Y coordinates column for niches",
    }

    BROWSER_KEYS = {
        "Nodes directory",
        "Network directory",
        "Patient column name",
        "Sample column name",
        "Extension",
    }

    FIXED_OPTIONS = {
        "Niches method": ["NAS", "SCAN-IT"],
        "Processing method": ["Aggregated nodes", "Per sample"],
        "reducer_type": ["umap"],
        "clusterer_type": ["leiden", "ecg", "spectral", "gmm", "hdbscan"],
        "order": ["1", "2"],
        "metric": ["manhattan", "euclidean", "cosine"],
        "Edges method": ["delaunay", "knn"],
        "stat_funcs": ["np.mean,np.std", "np.mean"],
        "normalize": ["total", "niche", "obs", "clr", "niche&obs", "all"],
    }

    def __init__(self, config_data, parent=None):
        super().__init__(parent)
        self.config_data = config_data
        self.entries = {}
        self._nodes_columns = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel("⚙ Parameters")
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, stretch=1)

        preferred_order = ["Tysserand", "Assortativity", "Niche Analysis"]
        for key in preferred_order:
            if key in self.config_data and isinstance(self.config_data[key], dict):
                self._add_section_tab(key, self.config_data[key])

        for sec, data in self.config_data.items():
            if sec not in preferred_order and isinstance(data, dict):
                self._add_section_tab(sec, data)

        self.save_btn = QPushButton("💾 Save Config")
        layout.addWidget(self.save_btn)

        self.run_buttons = []
        for script in SCRIPTS:
            name = script.stem.replace("_", " ").upper()
            btn = QPushButton(f"▶ {name}")
            self.run_buttons.append(btn)
            layout.addWidget(btn)

    def _add_section_tab(self, section, data):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        inner_tabs = QTabWidget()
        tab_layout.addWidget(inner_tabs)

        general = {
            k: v for k, v in data.items()
            if not isinstance(v, dict) and k not in self.BROWSER_KEYS
        }
        if general:
            self._add_form(inner_tabs, "General", section, general)

        for subsec, subdata in data.items():
            if isinstance(subdata, dict):
                self._add_form(inner_tabs, subsec, f"{section}__{subsec}", subdata)

        self.tabs.addTab(tab, section)

    def _add_form(self, tab_widget, title, section_key, data):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)

        for k, v in data.items():
            label = QLabel(k)
            field = self._get_widget(k, v)
            form.addRow(label, field)
            self.entries.setdefault(section_key, {})[k] = field

        scroll.setWidget(inner)
        tab_widget.addTab(scroll, title)

    def _get_widget(self, key, value):
        if key in self.COLUMN_FIELDS:
            combo = QComboBox()
            combo.addItems(["— select column —"] + self._nodes_columns)
            if isinstance(value, str) and value in self._nodes_columns:
                combo.setCurrentText(value)
            return combo

        if isinstance(value, bool):
            combo = QComboBox()
            combo.addItems(["True", "False"])
            combo.setCurrentText(str(value))
            return combo

        if key in self.FIXED_OPTIONS:
            combo = QComboBox()
            combo.addItems(self.FIXED_OPTIONS[key])
            if isinstance(value, str) and value in self.FIXED_OPTIONS[key]:
                combo.setCurrentText(value)
            return combo

        if key == "Index":
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            mode = QComboBox()
            mode.addItems(["index", "Custom"])
            edit = QLineEdit()

            if value in (None, "index"):
                mode.setCurrentText("index")
                edit.setText("index")
                edit.setEnabled(False)
            else:
                mode.setCurrentText("Custom")
                edit.setText(str(value))
                edit.setEnabled(True)

            def toggle_index_mode():
                is_custom = mode.currentText() == "Custom"
                edit.setEnabled(is_custom)
                if not is_custom:
                    edit.setText("index")

            mode.currentIndexChanged.connect(toggle_index_mode)
            row.addWidget(mode)
            row.addWidget(edit)
            container._mode_combo = mode
            container._value_edit = edit
            return container

        if key == "Saving directory":
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit(str(value) if value else "")
            button = QPushButton("…")
            button.setMaximumWidth(32)

            def browse_dir():
                selected = QFileDialog.getExistingDirectory(self, "Choose saving directory")
                if selected:
                    edit.setText(selected)

            button.clicked.connect(browse_dir)
            row.addWidget(edit)
            row.addWidget(button)
            container._path_edit = edit
            return container

        if isinstance(value, str) and ("\n" in value or "\t" in value):
            text_edit = QTextEdit()
            text_edit.setPlainText(value)
            text_edit.setMaximumHeight(80)
            return text_edit

        return QLineEdit("" if value is None else str(value))

    def set_nodes_columns(self, columns):
        self._nodes_columns = list(columns)
        for section_dict in self.entries.values():
            for key, widget in section_dict.items():
                if key in self.COLUMN_FIELDS and isinstance(widget, QComboBox):
                    current = widget.currentText()
                    widget.clear()
                    widget.addItems(["— select column —"] + self._nodes_columns)
                    if current in self._nodes_columns:
                        widget.setCurrentText(current)

    def parse_value(self, key, widget):
        if hasattr(widget, "_path_edit") and not hasattr(widget, "_mode_combo"):
            return widget._path_edit.text().strip() or None

        if hasattr(widget, "_mode_combo") and hasattr(widget, "_value_edit"):
            mode = widget._mode_combo.currentText().strip()
            if mode != "Custom":
                return "index"
            value = widget._value_edit.text().strip()
            return value or None

        if isinstance(widget, QTextEdit):
            val = widget.toPlainText().strip()
        elif isinstance(widget, QComboBox):
            val = widget.currentText().strip()
            if val.startswith("—"):
                return None
        else:
            val = widget.text().strip()

        if key == "order":
            return val
        if val.lower() in ("none", "null", ""):
            return None
        if val.lower() in ("true", "false"):
            return val.lower() == "true"

        for caster in (int, float):
            try:
                return caster(val)
            except ValueError:
                continue

        if val.startswith(("[", "{", "(")):
            try:
                return ast.literal_eval(val)
            except Exception:
                pass

        return val

    def collect_config(self):
        new_config = {}
        for sec, items in self.entries.items():
            keys = sec.split("__")
            target = new_config
            for key in keys[:-1]:
                target = target.setdefault(key, {})
            target[keys[-1]] = {
                k: self.parse_value(k, w) for k, w in items.items()
            }
        return new_config


class MosnaGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MOSNA Analysis — Napari layout rewritten")
        self.working_dir = None
        self.script_thread = None
        self.config_data = {}

        self._load_config()
        self._build_ui()
        self._wire_signals()
        self._set_ui_enabled(False)
        QTimer.singleShot(0, self._ask_working_dir)

    def _load_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            self.config_data = self._normalize(raw)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config:\n{e}")
            self.config_data = {}

    def _normalize(self, obj):
        def _safe(v):
            if isinstance(v, (dict, list)):
                return v
            try:
                val = ast.literal_eval(v)
                return val if isinstance(val, (list, dict)) else v
            except Exception:
                return v

        if isinstance(obj, dict):
            return {k: self._normalize(_safe(v)) for k, v in obj.items()}
        return obj

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(12, 4, 12, 4)
        self.wd_label = QLabel("Working directory: not set")
        self.wd_btn = QPushButton("📁 Set working dir")
        self.wd_btn.setFixedWidth(180)
        top_layout.addWidget(self.wd_label, stretch=1)
        top_layout.addWidget(self.wd_btn)
        root_layout.addWidget(top_bar)

        splitter = QSplitter(Qt.Horizontal)

        self.browser = BrowserPanel(self.config_data)
        self.browser.setMinimumWidth(280)
        self.browser.setMaximumWidth(420)
        splitter.addWidget(self.browser)

        self.viewer = ImageViewerPanel()
        splitter.addWidget(self.viewer)

        self.params = ParametersPanel(self.config_data)
        self.params.setMinimumWidth(320)
        self.params.setMaximumWidth(520)
        splitter.addWidget(self.params)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([340, 700, 420])
        root_layout.addWidget(splitter, stretch=1)

    def _wire_signals(self):
        self.wd_btn.clicked.connect(lambda: self._choose_working_dir())
        self.browser.sampleSelected.connect(self._on_sample_selected)
        self.browser.browserConfigChanged.connect(self._apply_browser_values_to_config)
        self.params.save_btn.clicked.connect(self._save_config)

        for btn, script in zip(self.params.run_buttons, SCRIPTS):
            btn.clicked.connect(lambda _, s=script: self._run_script(s))

    def _set_ui_enabled(self, enabled):
        self.browser.setEnabled(enabled)
        self.params.setEnabled(enabled)

    def _ask_working_dir(self):
        ok = self._choose_working_dir(mandatory=True)
        if not ok:
            self.close()
            return
        self._set_ui_enabled(True)
        self.browser.refresh_files()

    def _choose_working_dir(self, mandatory=False):
        path = QFileDialog.getExistingDirectory(self, "Choose working directory")
        if not path:
            if mandatory:
                QMessageBox.warning(self, "Required", "You must choose a working directory.")
            return False

        self.working_dir = str(Path(path).expanduser().resolve())
        self.wd_label.setText(f"Working directory: {self.working_dir}")
        return True

    def _on_sample_selected(self, meta):
        nodes_path = meta.get("nodes_path")
        patient = meta.get("patient_value") or "?"
        sample = meta.get("sample_value") or "None"

        try:
            path = Path(nodes_path)
            if path.suffix.lower() == ".parquet":
                df = pd.read_parquet(path, engine="pyarrow")
            elif path.suffix.lower() == ".csv":
                df = pd.read_csv(path, nrows=0)
            elif path.suffix.lower() == ".tsv":
                df = pd.read_csv(path, sep="\t", nrows=0)
            else:
                raise ValueError(f"Unsupported extension: {path.suffix}")

            columns = list(df.columns)
            self.params.set_nodes_columns(columns)
            self.viewer.set_status(
                f"Selected sample — patient: {patient} | sample: {sample} | {len(columns)} columns detected"
            )
        except Exception as e:
            self.viewer.set_status(f"Could not read nodes file: {e}")

    def _apply_browser_values_to_config(self, browser_values):
        tys = self.config_data.setdefault("Tysserand", {})
        assort = self.config_data.setdefault("Assortativity", {})
        niche = self.config_data.setdefault("Niche Analysis", {})

        tys["Nodes directory"] = browser_values["nodes_directory"]
        tys["Patient column name"] = browser_values["patient_column_name"]
        tys["Sample column name"] = browser_values["sample_column_name"]
        tys["Extension"] = browser_values["extension"]

        assort["Network directory"] = browser_values["network_directory"] or "Default"
        assort["Patient column name"] = browser_values["patient_column_name"]
        assort["Sample column name"] = browser_values["sample_column_name"]
        assort["Extension"] = browser_values["extension"]

        niche["Network directory"] = browser_values["network_directory"] or "Default"
        niche["Patient column name"] = browser_values["patient_column_name"]
        niche["Sample column name"] = browser_values["sample_column_name"]
        niche["Extension"] = browser_values["extension"]

        self.viewer.set_status("Browser values copied into in-memory configuration.")

    def _merge_browser_and_parameters(self):
        self._apply_browser_values_to_config(self.browser.get_browser_values())
        collected = self.params.collect_config()

        for section, values in collected.items():
            if section not in self.config_data:
                self.config_data[section] = values
                continue

            if isinstance(values, dict):
                self.config_data[section].update(values)
            else:
                self.config_data[section] = values

    def _save_config(self):
        self._merge_browser_and_parameters()

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    force_inline_lists(self.config_data),
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    width=4096,
                )
            QMessageBox.information(self, "Saved", "Configuration saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config:\n{e}")

    def _run_script(self, script_path):
        self._save_config()

        if self.working_dir is None:
            QMessageBox.warning(self, "Missing", "Please choose a working directory first.")
            return

        if not script_path.is_file():
            QMessageBox.warning(self, "Missing", f"Script not found:\n{script_path}")
            return

        rel = script_path.relative_to(BASE_DIR)
        module = ".".join(rel.with_suffix("").parts)
        cmd = [
            "python",
            "-m",
            module,
            "--file",
            str(CONFIG_PATH),
            "--working_dir",
            self.working_dir,
        ]

        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(BASE_DIR) if not existing else str(BASE_DIR) + os.pathsep + existing
        env["ENABLE_QT_PROGRESS"] = "1"

        self.viewer.progress_start(f"Running: {script_path.name}")
        self.script_thread = ScriptRunnerThread(cmd, cwd=self.working_dir, env=env)
        self.script_thread.output_line.connect(self._on_output_line)
        self.script_thread.finished_signal.connect(
            lambda ok, code, out, elapsed: self._on_finished(script_path, ok, code, out, elapsed)
        )
        self.script_thread.start()

    def _on_output_line(self, line):
        if not line:
            return

        if line.startswith("[QT_INFO]"):
            self.viewer.set_status(line.replace("[QT_INFO]", "").strip())
            return

        if line.startswith("[QT_PROGRESS]"):
            payload = line.replace("[QT_PROGRESS]", "").strip()
            m_cur = re.search(r"current=(\d+)", payload)
            m_tot = re.search(r"total=(\d+)", payload)
            if m_cur and m_tot:
                cur = int(m_cur.group(1))
                tot = int(m_tot.group(1))
                m_desc = re.search(r"desc=(.*)$", payload)
                if m_desc:
                    self.viewer.set_status(m_desc.group(1).strip())
                self.viewer.set_progress(cur, tot)

    def _on_finished(self, script_path, success, returncode, output, elapsed):
        self.viewer.progress_stop(success)
        duration = self._format_duration(elapsed)

        if success:
            self.viewer.set_status(f"✅ {script_path.name} completed in {duration}")
            self.viewer.clear_images()
            if self.working_dir:
                for pattern in ("*.png", "*.jpg", "*.jpeg", "*.svg"):
                    for img in sorted(Path(self.working_dir).rglob(pattern))[-10:]:
                        self.viewer.show_image(str(img))
            return

        output = (output or "").strip()[:4000]
        self.viewer.set_status(f"❌ {script_path.name} failed in {duration}")
        QMessageBox.critical(
            self,
            "Script error",
            f"Script: {script_path.name}\nExit code: {returncode}\nTime: {duration}\n\n{output}",
        )

    def _format_duration(self, seconds):
        total = int(round(seconds))
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h} h {m} min {s} s"
        if m:
            return f"{m} min {s} s"
        return f"{seconds:.2f} s"


def main():
    app = QApplication(sys.argv)

    try:
        with open(BASE_DIR / "package" / "style_napari.qss", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception:
        pass

    window = MosnaGUI()
    window.resize(1400, 900)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
