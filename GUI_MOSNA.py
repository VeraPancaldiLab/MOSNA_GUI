from pathlib import Path
import os
import re
import sys
import ast
import time
import subprocess
import signal
import yaml
import pandas as pd

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QUrl, QSize
from PySide6.QtGui import QPixmap, QAction, QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QStackedWidget,
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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QMenu,
    QToolButton,
    QWidgetAction,
)

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "CONFIG" / "configuration.yaml"
DOC_HTML_PATH = BASE_DIR / "assets" / "documentation.html"
LOGO_PATH = BASE_DIR / "assets" / "logo.ico"

# Add project root to sys.path so package imports work when run directly
import sys as _sys
if str(BASE_DIR) not in _sys.path:
    _sys.path.insert(0, str(BASE_DIR))

from package.utils.find_sample import find_sample  # noqa: E402 — after path setup

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


class ScriptRunnerThread(QThread):
    finished_signal = Signal(bool, int, str, float)
    output_line = Signal(str)

    def __init__(self, command, cwd=None, env=None):
        super().__init__()
        self.command = command
        self.cwd = cwd
        self.env = env
        self.proc = None
        self._stop_requested = False

    def run(self):
        start_time = time.perf_counter()
        try:
            self.proc = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.cwd,
                env=self.env,
                bufsize=1,
                universal_newlines=True,
                start_new_session=True,
            )

            stdout_lines = []
            if self.proc.stdout:
                for line in self.proc.stdout:
                    line = line.rstrip("\n")
                    stdout_lines.append(line)
                    self.output_line.emit(line)

            stderr_output = self.proc.stderr.read() if self.proc.stderr else ""
            returncode = self.proc.wait()

            if self._stop_requested:
                success = False
                output = "Process interrupted by user."
            else:
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

        finally:
            self.proc = None

    def stop(self):
        """
        Essaie d'interrompre proprement le processus comme un Ctrl+C.
        Si le processus ne s'arrête pas, on pourra ensuite forcer davantage.
        """
        self._stop_requested = True

        if self.proc is None:
            return

        try:
            if self.proc.poll() is None:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGINT)
        except Exception:
            try:
                if self.proc.poll() is None:
                    self.proc.terminate()
            except Exception:
                pass

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
        self.working_dir = None

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QLabel("Browser")
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

        self.network_dir_mode = QComboBox()
        self.network_dir_mode.addItems(["Default", "Custom"])

        self.network_dir_edit = QLineEdit()
        self.network_dir_btn = QPushButton("…")
        self.network_dir_btn.setMaximumWidth(32)

        network_row = QWidget()
        network_row_layout = QHBoxLayout(network_row)
        network_row_layout.setContentsMargins(0, 0, 0, 0)
        network_row_layout.addWidget(self.network_dir_mode)
        network_row_layout.addWidget(self.network_dir_edit)
        network_row_layout.addWidget(self.network_dir_btn)
        source_form.addRow("Network directory", network_row)

        layout.addWidget(source_group)

        naming_group = QGroupBox("Pattern used to find files")
        naming_form = QFormLayout(naming_group)

        self.patient_column_edit = QLineEdit()
        self.sample_column_edit = QLineEdit()
        naming_form.addRow("Patient column name", self.patient_column_edit)
        naming_form.addRow("Sample column name", self.sample_column_edit)
        self.extension_combo = QComboBox()
        self.extension_combo.addItems(["csv", "parquet", "tsv"])
        naming_form.addRow("Extension", self.extension_combo)

        layout.addWidget(naming_group)

        actions = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Nodes")
        self.apply_btn = QPushButton("Refresh Networks")
        actions.addWidget(self.refresh_btn)
        actions.addWidget(self.apply_btn)
        layout.addLayout(actions)

        list_group = QGroupBox("Files found")
        list_layout = QVBoxLayout(list_group)

        self.results_label = QLabel("No file discovered yet.")

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Patient", "Sample", "Nodes files", "Edges files"])
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.setAlternatingRowColors(False)
        self.results_table.setEnabled(False)
        self.results_table.setFixedHeight(350)

        list_layout.addWidget(self.results_label)
        list_layout.addWidget(self.results_table)
        layout.addWidget(list_group)

        layout.addStretch()

        self.nodes_dir_btn.clicked.connect(lambda: self._browse_dir(self.nodes_dir_edit, "Choose nodes directory"))
        self.network_dir_btn.clicked.connect(lambda: self._browse_dir(self.network_dir_edit, "Choose network directory"))
        self.network_dir_mode.currentIndexChanged.connect(self._toggle_network_dir_mode)
        self.refresh_btn.clicked.connect(self.refresh_files)
        self.apply_btn.clicked.connect(self.refresh_network_folder)
        self.results_table.itemSelectionChanged.connect(self._emit_selected_sample)

    def refresh_network_folder(self):
        values = self.get_browser_values()
        network_directory = values["network_directory"]
        extension = values["extension"]
        patient_column_name = values["patient_column_name"]
        sample_column_name = values["sample_column_name"]

        if network_directory in (None, "", "Default"):
            if self.working_dir is None:
                QMessageBox.warning(
                    self,
                    "Missing path",
                    "Working directory is required to resolve the default network folder."
                )
                return
            nodes_dir = self.working_dir / "temp" / "net_dir_mosna"
        else:
            nodes_dir = Path(network_directory)

        if not nodes_dir.is_dir():
            QMessageBox.warning(
                self,
                "Invalid path",
                "Network directory must be a valid folder."
            )
            return

        if not patient_column_name:
            QMessageBox.warning(
                self,
                "Missing value",
                "Patient column name is required to build the filename pattern."
            )
            return

        selected_sample_name = sample_column_name if sample_column_name else None
        nodes_files = find_sample(nodes_dir, extension, patient_column_name, selected_sample_name)

        self._populate_results_table(nodes_files, values, use_network_for_edges=True)
        self.browserConfigChanged.emit(self.get_browser_values())

    def set_working_dir(self, working_dir):
        self.working_dir = Path(working_dir) if working_dir else None

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
            self.network_dir_mode.setCurrentText("Default")
            self.network_dir_edit.setText("")
            self.network_dir_edit.setEnabled(False)
            self.network_dir_btn.setEnabled(False)
        else:
            self.network_dir_mode.setCurrentText("Custom")
            self.network_dir_edit.setText(str(network_dir))
            self.network_dir_edit.setEnabled(True)
            self.network_dir_btn.setEnabled(True)

        extension = tys.get("Extension") or assort.get("Extension") or "parquet"
        idx = self.extension_combo.findText(str(extension))
        if idx >= 0:
            self.extension_combo.setCurrentIndex(idx)

        self.patient_column_edit.setText(str(tys.get("Patient column name") or ""))
        self.sample_column_edit.setText(str(tys.get("Sample column name") or ""))

    def get_browser_values(self):
        return {
            "nodes_directory": self.nodes_dir_edit.text().strip() or None,
            "network_directory": (
                self.network_dir_edit.text().strip()
                if self.network_dir_mode.currentText() == "Custom"
                else "Default"
            ),
            "extension": self.extension_combo.currentText().strip(),
            "patient_column_name": self.patient_column_edit.text().strip() or None,
            "sample_column_name": self.sample_column_edit.text().strip() or None,
        }

    def _toggle_network_dir_mode(self):
        is_custom = self.network_dir_mode.currentText() == "Custom"
        self.network_dir_edit.setEnabled(is_custom)
        self.network_dir_btn.setEnabled(is_custom)
        if not is_custom:
            self.network_dir_edit.setText("")

    def emit_browser_config(self):
        self.browserConfigChanged.emit(self.get_browser_values())

    def refresh_files(self):
        values = self.get_browser_values()
        nodes_directory = values["nodes_directory"]
        extension = values["extension"]
        patient_column_name = values["patient_column_name"]
        sample_column_name = values["sample_column_name"]

        if not nodes_directory:
            QMessageBox.warning(
                self,
                "Missing path",
                "Nodes directory is required for Refresh Table."
            )
            return

        nodes_dir = Path(nodes_directory)
        if not nodes_dir.is_dir():
            QMessageBox.warning(
                self,
                "Invalid path",
                "Nodes directory must be a valid folder."
            )
            return

        if not patient_column_name:
            QMessageBox.warning(
                self,
                "Missing value",
                "Patient column name is required to build the filename pattern."
            )
            return

        selected_sample_name = sample_column_name if sample_column_name else None
        nodes_files = find_sample(nodes_dir, extension, patient_column_name, selected_sample_name)

        self._populate_results_table(nodes_files, values, use_network_for_edges=False)

    def _build_metadata_from_nodes(self, nodes_path, browser_values, use_network_for_edges=False):
        nodes_path = Path(nodes_path)
        extension = browser_values["extension"]
        network_directory = browser_values["network_directory"]
        sample_column_name = browser_values["sample_column_name"]

        patient_value, sample_value = self._extract_patient_sample_from_name(
            nodes_path.stem,
            browser_values["patient_column_name"],
            sample_column_name,
        )

        if network_directory in (None, "", "Default"):
            resolved_network_dir = (
                Path(self.working_dir) / "temp" / "net_dir_mosna"
                if self.working_dir is not None
                else None
            )
        else:
            resolved_network_dir = Path(network_directory)

        edges_path = None
        if use_network_for_edges:
            network_directory = browser_values["network_directory"]

            if network_directory in (None, "", "Default"):
                resolved_network_dir = (
                    Path(self.working_dir) / "temp" / "net_dir_mosna"
                    if self.working_dir is not None
                    else None
                )
            else:
                resolved_network_dir = Path(network_directory)

            if resolved_network_dir is not None and resolved_network_dir.is_dir():
                candidate_name = self._build_edges_name(nodes_path.name)
                candidate_path = resolved_network_dir / candidate_name

                if candidate_path.exists():
                    edges_path = candidate_path
                else:
                    stem_suffix = nodes_path.stem.removeprefix("nodes_")
                    matches = sorted(resolved_network_dir.glob(f"edges_{stem_suffix}.*"))
                    if matches:
                        edges_path = matches[0]

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
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        item = self.results_table.item(row, 0)
        if item is None:
            return

        meta = item.data(Qt.UserRole)
        if meta:
            self.sampleSelected.emit(meta)

    def get_selected_meta(self):
        selected_items = self.results_table.selectedItems()
        if not selected_items:
            return None

        row = selected_items[0].row()
        item = self.results_table.item(row, 0)
        if item is None:
            return None

        return item.data(Qt.UserRole)

    def _populate_results_table(self, nodes_files, values, use_network_for_edges):
        filtered_results = []
        for nodes_path in nodes_files:
            meta = self._build_metadata_from_nodes(
                nodes_path,
                values,
                use_network_for_edges=use_network_for_edges,
            )
            if meta is None:
                continue
            filtered_results.append(meta)

        self._current_results = filtered_results
        self.results_table.clearContents()
        self.results_table.setRowCount(0)

        if not filtered_results:
            self.results_label.setText("No file matches the current pattern.")
            self.results_table.setEnabled(False)
            return

        self.results_table.setRowCount(len(filtered_results))

        for row, meta in enumerate(filtered_results):
            patient_item = QTableWidgetItem(meta.get("patient_value") or "")
            sample_item = QTableWidgetItem(meta.get("sample_value") or "")
            nodes_item = QTableWidgetItem(Path(meta["nodes_path"]).name)

            edges_name = ""
            if meta.get("edges_path"):
                edges_name = Path(meta["edges_path"]).name
            edges_item = QTableWidgetItem(edges_name)

            patient_item.setData(Qt.UserRole, meta)

            self.results_table.setItem(row, 0, patient_item)
            self.results_table.setItem(row, 1, sample_item)
            self.results_table.setItem(row, 2, nodes_item)
            self.results_table.setItem(row, 3, edges_item)

        self.results_table.resizeColumnsToContents()
        self.results_label.setText(f"{len(filtered_results)} file(s) found.")
        self.results_table.setEnabled(True)
        self.results_table.selectRow(0)
        self._emit_selected_sample()

class AnalysisImageTab(QWidget):
    """
    Ce widget représente un onglet d'analyse unique dans le viewer.
    Il gère deux sous-vues :
    - les images globales
    - les images associées au patient sélectionné

    Les images patient sont regroupées par identifiant patient.
    Le sample éventuel reste visible dans le nom du fichier.
    """

    def __init__(self, analysis_name, logo_path, parent=None):
        super().__init__(parent)
        self.analysis_name = analysis_name
        self.logo_path = Path(logo_path)
        self.global_images = []
        self.patient_images = {}
        self.is_tysserand = self.analysis_name.lower() == "tysserand"

        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Patient"))
        self.patient_combo = QComboBox()
        self.patient_combo.addItem("— No patient selected —")
        top_row.addWidget(self.patient_combo)

        top_row.addStretch()
        layout.addLayout(top_row)

        if self.is_tysserand:
            self.image_tabs = QTabWidget()
            layout.addWidget(self.image_tabs)
        else:
            self.content_tabs = QTabWidget()

            self.global_tabs = QTabWidget()
            self.patient_tabs = QTabWidget()

            self.content_tabs.addTab(self.global_tabs, "Global")
            self.content_tabs.addTab(self.patient_tabs, "Patient")

            layout.addWidget(self.content_tabs)

        self.patient_combo.currentIndexChanged.connect(self._refresh_patient_view)

    def set_images(self, global_images, patient_images):
        """
        Cette méthode reçoit les données déjà triées pour une analyse donnée.
        - global_images est une liste de chemins d'images globales
        - patient_images est un dictionnaire : patient -> liste de chemins
        """
        self.global_images = list(global_images)
        self.patient_images = {
            str(patient): list(images)
            for patient, images in patient_images.items()
        }

        self._refresh_global_view()
        self._refresh_patient_combo()
        self._refresh_patient_view()

    def _build_logo_scroll(self):
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)

        pix = QPixmap(str(self.logo_path))
        if not pix.isNull():
            label.setPixmap(
                pix.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            label.setText("Logo not found.")

        scroll = QScrollArea()
        scroll.setWidget(label)
        scroll.setWidgetResizable(True)
        return scroll

    def _build_image_scroll(self, image_path):
        pix = QPixmap(str(image_path))
        if pix.isNull():
            return None

        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setScaledContents(False)
        # Store original pixmap for dynamic rescaling
        label._original_pix = pix
        label.setPixmap(pix)

        scroll = QScrollArea()
        scroll.setWidget(label)
        scroll.setWidgetResizable(True)

        # Rescale image to fit the scroll area when it is resized
        original_resizeEvent = scroll.resizeEvent
        def _on_resize(event, lbl=label, sc=scroll):
            if hasattr(lbl, "_original_pix") and not lbl._original_pix.isNull():
                available = sc.viewport().size()
                lbl.setPixmap(
                    lbl._original_pix.scaled(
                        available.width() - 4,
                        available.height() - 4,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            original_resizeEvent(event)

        scroll.resizeEvent = _on_resize
        return scroll

    def _populate_tabs_with_images(self, tab_widget, image_paths):
        while tab_widget.count():
            tab_widget.removeTab(0)

        if not image_paths:
            tab_widget.addTab(self._build_logo_scroll(), "")
            return

        valid_count = 0
        for img_path in image_paths:
            scroll = self._build_image_scroll(img_path)
            if scroll is None:
                continue

            title = Path(img_path).stem
            tab_widget.addTab(scroll, title)
            valid_count += 1

        if valid_count == 0:
            tab_widget.addTab(self._build_logo_scroll(), "")

    def _refresh_global_view(self):
        if self.is_tysserand:
            return
        self._populate_tabs_with_images(self.global_tabs, self.global_images)

    def _refresh_patient_combo(self):
        current = self.patient_combo.currentText()

        self.patient_combo.blockSignals(True)
        self.patient_combo.clear()

        patients = sorted(self.patient_images.keys())
        if not patients:
            self.patient_combo.addItem("— No patient —")
        else:
            self.patient_combo.addItems(patients)

        index = self.patient_combo.findText(current)
        if index >= 0:
            self.patient_combo.setCurrentIndex(index)
        else:
            self.patient_combo.setCurrentIndex(0)

        self.patient_combo.blockSignals(False)

    def _refresh_patient_view(self):
        patient = self.patient_combo.currentText().strip()

        if patient.startswith("—"):
            if self.is_tysserand:
                self._populate_tabs_with_images(self.image_tabs, [])
            else:
                self._populate_tabs_with_images(self.patient_tabs, [])
            return

        images = self.patient_images.get(patient, [])

        if self.is_tysserand:
            self._populate_tabs_with_images(self.image_tabs, images)
        else:
            self._populate_tabs_with_images(self.patient_tabs, images)

class ImageViewerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("Viewer")
        header.setObjectName("PanelHeader")
        layout.addWidget(header)

        self._tabs = QTabWidget()

        # ── Images page ──────────────────────────────────────
        self._images_page = QWidget()
        images_layout = QVBoxLayout(self._images_page)
        images_layout.setContentsMargins(0, 0, 0, 0)

        self.analysis_tabs = QTabWidget()
        self.tysserand_tab = AnalysisImageTab("Tysserand", LOGO_PATH)
        self.assortativity_tab = AnalysisImageTab("Assortativity", LOGO_PATH)
        self.niches_tab = AnalysisImageTab("Niches", LOGO_PATH)

        self.analysis_tabs.addTab(self.tysserand_tab, "Tysserand")
        self.analysis_tabs.addTab(self.assortativity_tab, "Assortativity")
        self.analysis_tabs.addTab(self.niches_tab, "Niches")

        images_layout.addWidget(self.analysis_tabs)
        self._tabs.addTab(self._images_page, "Images")

        # ── Log page ─────────────────────────────────────────
        self._log_page = QWidget()
        log_layout = QVBoxLayout(self._log_page)
        log_layout.setContentsMargins(6, 6, 6, 6)
        log_layout.setSpacing(4)

        log_header_row = QHBoxLayout()
        log_header_row.addWidget(QLabel("Script output"))
        log_clear_btn = QPushButton("Clear")
        log_clear_btn.setMaximumWidth(80)
        log_header_row.addStretch()
        log_header_row.addWidget(log_clear_btn)
        log_layout.addLayout(log_header_row)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setObjectName("LogView")
        self._log_view.setPlaceholderText("Script output will appear here…")
        log_layout.addWidget(self._log_view)
        log_clear_btn.clicked.connect(self._log_view.clear)

        self._tabs.addTab(self._log_page, "Log")

        # ── Documentation page ───────────────────────────────
        self._doc_view = QTextBrowser()
        self._doc_view.setOpenExternalLinks(True)
        self._tabs.addTab(self._doc_view, "Documentation")

        layout.addWidget(self._tabs, stretch=1)

        # ── Status bar area ──────────────────────────────────
        status_bar = QWidget()
        status_bar.setObjectName("StatusBar")
        status_layout = QVBoxLayout(status_bar)
        status_layout.setContentsMargins(8, 4, 8, 4)
        status_layout.setSpacing(3)

        self._status_label = QLabel("Ready.")
        self._status_label.setObjectName("RunStatusLabel")
        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)

        status_layout.addWidget(self._status_label)
        status_layout.addWidget(self._progress)
        layout.addWidget(status_bar)

    def append_log(self, line: str):
        """Append a coloured line to the log panel."""
        if "[ERROR]" in line or "❌" in line:
            colour = "#ff6b6b"
        elif "[WARN]" in line or "⚠" in line:
            colour = "#f9ca24"
        elif "[OK]" in line or "✅" in line:
            colour = "#6bdd9a"
        elif "[INFO]" in line or "[QT_INFO]" in line:
            colour = "#74b9ff"
        elif "[QT_PROGRESS]" in line:
            colour = "#a29bfe"
        else:
            colour = "#dfe6e9"

        escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._log_view.append(f'<span style="color:{colour};">{escaped}</span>')
        # Auto-scroll to bottom
        sb = self._log_view.verticalScrollBar()
        sb.setValue(sb.maximum())
        # Switch to log tab while running
        self._tabs.setCurrentIndex(1)

    def set_analysis_images(self, data):
        self.tysserand_tab.set_images(
            [],
            data.get("tysserand", {}).get("patients", {}),
        )
        self.assortativity_tab.set_images(
            data.get("assortativity", {}).get("global", []),
            data.get("assortativity", {}).get("patients", {}),
        )
        self.niches_tab.set_images(
            data.get("niches", {}).get("global", []),
            data.get("niches", {}).get("patients", {}),
        )
        self._tabs.setCurrentIndex(0)

    def load_documentation(self, html_path):
        html_path = Path(html_path)
        if html_path.is_file():
            self._doc_view.setSource(QUrl.fromLocalFile(str(html_path.resolve())))

    def set_progress_color(self, obj_name: str):
        """Apply the gradient matching the run button that was clicked."""
        STEP_GRADIENTS = {
            "RunTysserand": "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a6882,stop:1 #28a0c8)",
            "RunAssort":    "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #5030a0,stop:1 #7850c8)",
            "RunNiches":    "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #206840,stop:1 #30a060)",
            "RunClear":     "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #503040,stop:1 #704050)",
        }
        gradient = STEP_GRADIENTS.get(obj_name,
            "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3060c0,stop:1 #5090d8)")
        self._progress.setStyleSheet(
            f"QProgressBar::chunk {{ background: {gradient}; border-radius: 6px; }}"
        )

    def set_status(self, text):
        self._status_label.setText(text)

    def set_progress(self, current, total):
        if total > 0:
            if self._progress.maximum() != total:
                self._progress.setRange(0, total)
            self._progress.setValue(min(current, total))

    def progress_start(self, title, step_obj_name=""):
        self._status_label.setText(title)
        self._progress.setRange(0, 0)
        if step_obj_name:
            self.set_progress_color(step_obj_name)

    def progress_stop(self, success):
        self._progress.setRange(0, 100)
        self._progress.setValue(100 if success else 0)
        if not success:
            self._progress.setStyleSheet(
                "QProgressBar::chunk { background: #8b2020; border-radius: 6px; }"
            )

class SquareIndicator(QWidget):
    """
    Petit carré affiché à gauche du nom de colonne.
    Il est rempli quand l'élément est sélectionné.
    """

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(14, 14)

    def set_checked(self, checked):
        self._checked = bool(checked)
        self.update()

    def is_checked(self):
        return self._checked

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(1, 1, -1, -1)

        painter.setPen(QPen(Qt.black, 1))

        if self._checked:
            painter.setBrush(QBrush(Qt.black))
        else:
            painter.setBrush(Qt.NoBrush)

        painter.drawRect(rect)

class MultiSelectOptionWidget(QWidget):
    """
    Une ligne du menu avec un carré et un texte.
    Un clic sur la ligne inverse l'état sans fermer le menu.
    """

    toggled = Signal(str, bool)

    def __init__(self, text, checked=False, parent=None):
        super().__init__(parent)
        self.text_value = text
        self.checked = bool(checked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.indicator = SquareIndicator(self.checked)
        self.label = QLabel(text)

        layout.addWidget(self.indicator)
        layout.addWidget(self.label)
        layout.addStretch()

        self.setCursor(Qt.PointingHandCursor)

    def set_checked(self, checked):
        self.checked = bool(checked)
        self.indicator.set_checked(self.checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.set_checked(not self.checked)
            self.toggled.emit(self.text_value, self.checked)
        super().mousePressEvent(event)

class MenuTextRow(QWidget):
    clicked = Signal()

    def __init__(self, text, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        self.label = QLabel(text)
        layout.addWidget(self.label)
        layout.addStretch()

        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class MultiSelectColumnsWidget(QWidget):
    """
    Ce widget permet de sélectionner une ou plusieurs colonnes.
    Le bouton ouvre un menu qui reste ouvert pendant les sélections.

    La valeur retournée suit cette logique :
    - aucune sélection : None
    - une seule colonne : str
    - plusieurs colonnes : list[str]
    """

    def __init__(self, columns=None, selected=None, parent=None):
        super().__init__(parent)
        self._columns = list(columns or [])
        self._selected = []
        self._option_widgets = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.button = QToolButton()
        self.button.setPopupMode(QToolButton.InstantPopup)
        self.button.setToolButtonStyle(Qt.ToolButtonTextOnly)

        self.menu = QMenu(self.button)
        self.button.setMenu(self.menu)

        layout.addWidget(self.button)

        self.set_columns(self._columns, selected=selected)

    def set_columns(self, columns, selected=None):
        self._columns = list(columns or [])

        if selected is None:
            selected_values = set(self._selected)
        elif isinstance(selected, str):
            selected_values = {selected}
        else:
            selected_values = set(selected)

        self.menu.clear()
        self._option_widgets.clear()

        self._add_control_row("Select all", self.select_all)
        self._add_control_row("Clear all", self.clear_all)
        self.menu.addSeparator()

        for col in self._columns:
            row_widget = MultiSelectOptionWidget(col, checked=(col in selected_values))
            row_widget.toggled.connect(self._on_option_toggled)

            action = QWidgetAction(self.menu)
            action.setDefaultWidget(row_widget)
            self.menu.addAction(action)

            self._option_widgets[col] = row_widget

        self._update_internal_selected()
        self._update_button_text()

    def _add_control_row(self, text, callback):
        row_widget = MenuTextRow(text)
        row_widget.clicked.connect(callback)

        action = QWidgetAction(self.menu)
        action.setDefaultWidget(row_widget)
        self.menu.addAction(action)

    def _on_option_toggled(self, text, checked):
        self._update_internal_selected()
        self._update_button_text()

    def _update_internal_selected(self):
        self._selected = [
            name for name, widget in self._option_widgets.items()
            if widget.checked
        ]

    def get_selected_values(self):
        return list(self._selected)

    def set_selected_values(self, values):
        if values is None:
            selected_values = set()
        elif isinstance(values, str):
            selected_values = {values}
        else:
            selected_values = set(values)

        for name, widget in self._option_widgets.items():
            widget.set_checked(name in selected_values)

        self._update_internal_selected()
        self._update_button_text()

    def select_all(self):
        for widget in self._option_widgets.values():
            widget.set_checked(True)
        self._update_internal_selected()
        self._update_button_text()

    def clear_all(self):
        for widget in self._option_widgets.values():
            widget.set_checked(False)
        self._update_internal_selected()
        self._update_button_text()

    def get_value(self):
        values = self.get_selected_values()
        if not values:
            return None
        if len(values) == 1:
            return values[0]
        return values

    def _update_button_text(self):
        values = self.get_selected_values()

        if not values:
            self.button.setText("— select column(s) —")
        elif len(values) == 1:
            self.button.setText(values[0])
        elif len(values) <= 3:
            self.button.setText(", ".join(values))
        else:
            self.button.setText(f"{len(values)} columns selected")

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

    MULTI_COLUMN_FIELDS = {
        "Column to aggregate",
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
        layout.setSpacing(6)

        header = QLabel("Parameters")
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

        # ── Action bar ────────────────────────────────────────
        action_bar = QWidget()
        action_bar.setObjectName("ActionBar")
        action_layout = QVBoxLayout(action_bar)
        action_layout.setContentsMargins(4, 6, 4, 4)
        action_layout.setSpacing(5)

        save_stop_row = QHBoxLayout()
        self.save_btn = QPushButton("Save Config")
        self.save_btn.setObjectName("SaveButton")
        save_stop_row.addWidget(self.save_btn, stretch=3)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("StopButton")
        self.stop_btn.setEnabled(False)
        save_stop_row.addWidget(self.stop_btn, stretch=1)
        action_layout.addLayout(save_stop_row)

        # Per-step run buttons with distinct colours
        RUN_CONFIGS = [
            ("tysserand_network", "Step 1 — Tysserand",    "RunTysserand"),
            ("assortativity",     "Step 2 — Assortativity", "RunAssort"),
            ("niche_analysis",    "Step 3 — Niche Analysis", "RunNiches"),
            ("clear_temporary",   "Clear Temp Files",        "RunClear"),
        ]

        self.run_buttons = []
        for script in SCRIPTS:
            stem = script.stem
            label, obj_name = f"▶ {stem}", "RunButton"
            for key, lbl, obj in RUN_CONFIGS:
                if stem == key:
                    label, obj_name = lbl, obj
                    break
            btn = QPushButton(label)
            btn.setObjectName(obj_name)
            self.run_buttons.append(btn)
            action_layout.addWidget(btn)

        layout.addWidget(action_bar)

    # Keys that belong to each group in the niche subsection tabs
    NICHE_REDUCTION_KEYS  = {"reducer_type", "dim_clust", "n_neighbors", "metric", "min_dist"}
    NICHE_CLUSTERING_KEYS = {"clusterer_type", "k_cluster", "resolution", "n_clusters", "min_cluster_size"}
    NICHE_NORM_KEYS       = {"normalize"}

    NICHE_GENERAL_KEYS = {
        "Network directory", "Saving directory", "Extension",
        "Patient column name", "Sample column name", "Processing method",
        "Niches method", "Phenotype column", "Column to aggregate",
    }
    NICHE_REPLOT_KEYS = {
        "Plot Network", "X coordinates column for niches",
        "Y coordinates column for niches", "CPU",
    }

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
            if section == "Niche Analysis":
                self._add_niche_general_tab(inner_tabs, section, general)
            else:
                self._add_form(inner_tabs, "General", section, general)

        for subsec, subdata in data.items():
            if isinstance(subdata, dict):
                # Use the specialized grouped layout for Niche Analysis subsections
                if section == "Niche Analysis" and subsec in ("Aggregated nodes", "Per sample"):
                    self._add_niche_subsection_tab(inner_tabs, subsec, f"{section}__{subsec}", subdata)
                else:
                    self._add_form(inner_tabs, subsec, f"{section}__{subsec}", subdata)

        self.tabs.addTab(tab, section)

    def _add_niche_general_tab(self, tab_widget, section_key, data):
        """Render the Niche Analysis General tab with 2 QGroupBox blocks."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        outer_layout = QVBoxLayout(inner)
        outer_layout.setContentsMargins(6, 6, 6, 6)
        outer_layout.setSpacing(10)

        def add_group(group_title, keys):
            group = QGroupBox(group_title)
            form  = QFormLayout(group)
            form.setSpacing(8)
            form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
            for k in keys:
                if k not in data:
                    continue
                v     = data[k]
                label = QLabel(k)
                tip   = self.PARAM_TOOLTIPS.get(k)
                if tip:
                    label.setToolTip(tip)
                    label.setText(f"{k} ⓘ")
                    label.setObjectName("SmallInfo")
                field = self._get_widget(k, v)
                if tip and hasattr(field, "setToolTip"):
                    field.setToolTip(tip)
                form.addRow(label, field)
                self.entries.setdefault(section_key, {})[k] = field
            return group

        general_keys = [k for k in data if k in self.NICHE_GENERAL_KEYS]
        if general_keys:
            outer_layout.addWidget(add_group("Niche General Parameters", general_keys))

        replot_keys = [k for k in data if k in self.NICHE_REPLOT_KEYS]
        if replot_keys:
            outer_layout.addWidget(add_group("Replot Network with Niche Labels", replot_keys))

        # any remaining keys not in either group
        other_keys = [k for k in data if k not in self.NICHE_GENERAL_KEYS | self.NICHE_REPLOT_KEYS]
        if other_keys:
            outer_layout.addWidget(add_group("Other", other_keys))

        outer_layout.addStretch()
        scroll.setWidget(inner)
        tab_widget.addTab(scroll, "General")

    def _add_niche_subsection_tab(self, tab_widget, title, section_key, data):
        """Render a niche subsection (Aggregated nodes / Per sample) with 3 QGroupBox blocks."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        outer_layout = QVBoxLayout(inner)
        outer_layout.setContentsMargins(6, 6, 6, 6)
        outer_layout.setSpacing(10)

        # ── helpers ──────────────────────────────────────────────────────
        def make_group(title_grp, keys):
            group = QGroupBox(title_grp)
            form  = QFormLayout(group)
            form.setSpacing(8)
            form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
            for k in keys:
                if k not in data:
                    continue
                v     = data[k]
                label = QLabel(k)
                tip   = self.PARAM_TOOLTIPS.get(k)
                if tip:
                    label.setToolTip(tip)
                    label.setText(f"{k} ⓘ")
                    label.setObjectName("SmallInfo")
                field = self._get_widget(k, v)
                if tip and hasattr(field, "setToolTip"):
                    field.setToolTip(tip)
                form.addRow(label, field)
                self.entries.setdefault(section_key, {})[k] = field
            return group

        # ── Reduction ────────────────────────────────────────────────────
        reduction_keys = [k for k in data if k in self.NICHE_REDUCTION_KEYS]
        if reduction_keys:
            outer_layout.addWidget(make_group("Reduction", reduction_keys))

        # ── Clustering ───────────────────────────────────────────────────
        clustering_keys = [k for k in data if k in self.NICHE_CLUSTERING_KEYS]
        if clustering_keys:
            clust_group = QGroupBox("Clustering")
            clust_form  = QFormLayout(clust_group)
            clust_form.setSpacing(8)
            clust_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # We need the clusterer_type widget to drive conditional enabling
            clusterer_widget = None
            field_map = {}   # key -> (label_widget, field_widget)

            for k in clustering_keys:
                v     = data[k]
                label = QLabel(k)
                tip   = self.PARAM_TOOLTIPS.get(k)
                if tip:
                    label.setToolTip(tip)
                    label.setText(f"{k} ⓘ")
                    label.setObjectName("SmallInfo")
                field = self._get_widget(k, v)
                if tip and hasattr(field, "setToolTip"):
                    field.setToolTip(tip)
                clust_form.addRow(label, field)
                self.entries.setdefault(section_key, {})[k] = field
                field_map[k] = (label, field)
                if k == "clusterer_type":
                    clusterer_widget = field

            outer_layout.addWidget(clust_group)

            # Conditional enabling: resolution ↔ leiden
            #                       n_clusters   ↔ gmm | spectral
            #                       min_cluster_size ↔ hdbscan
            def update_clustering_fields():
                if clusterer_widget is None:
                    return
                ct = clusterer_widget.currentText() if isinstance(clusterer_widget, QComboBox) else ""
                for param, activators in [
                    ("resolution",       {"leiden"}),
                    ("n_clusters",       {"gmm", "spectral"}),
                    ("min_cluster_size", {"hdbscan"}),
                ]:
                    if param in field_map:
                        lbl, fld = field_map[param]
                        enabled = ct in activators
                        lbl.setEnabled(enabled)
                        fld.setEnabled(enabled)

            if clusterer_widget is not None and isinstance(clusterer_widget, QComboBox):
                clusterer_widget.currentIndexChanged.connect(update_clustering_fields)
                update_clustering_fields()   # apply initial state

        # ── Niche Normalisation ──────────────────────────────────────────
        norm_keys = [k for k in data if k in self.NICHE_NORM_KEYS]
        if norm_keys:
            outer_layout.addWidget(make_group("Niche Normalisation", norm_keys))

        # remaining keys not in any of the three groups
        other_keys = [k for k in data if k not in
                      self.NICHE_REDUCTION_KEYS | self.NICHE_CLUSTERING_KEYS | self.NICHE_NORM_KEYS]
        if other_keys:
            other_group = QGroupBox("Other")
            other_form  = QFormLayout(other_group)
            other_form.setSpacing(8)
            other_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
            for k in other_keys:
                v     = data[k]
                label = QLabel(k)
                tip   = self.PARAM_TOOLTIPS.get(k)
                if tip:
                    label.setToolTip(tip)
                    label.setText(f"{k} ⓘ")
                    label.setObjectName("SmallInfo")
                field = self._get_widget(k, v)
                if tip and hasattr(field, "setToolTip"):
                    field.setToolTip(tip)
                other_form.addRow(label, field)
                self.entries.setdefault(section_key, {})[k] = field
            outer_layout.addWidget(other_group)

        outer_layout.addStretch()
        scroll.setWidget(inner)
        tab_widget.addTab(scroll, title)

    # Tooltips shown on parameter labels (ⓘ hover)
    PARAM_TOOLTIPS = {
        "order":            "Neighborhood order for NAS aggregation.\n1 = direct neighbors only, 2 = includes 2nd-degree neighbors.",
        "stat_funcs":       "Statistical functions applied to neighbor features (e.g. np.mean, np.std).",
        "stat_names":       "Names associated with stat_funcs, used to label output columns.",
        "clusterer_type":   "Clustering algorithm used to define niches: gmm, leiden, hdbscan, spectral, ecg.",
        "metric":           "Distance metric for comparing observations: euclidean, manhattan or cosine.",
        "normalize":        "Normalization applied to niche features before the model:\ntotal, niche, obs, clr, niche&obs, all.",
        "reducer_type":     "Dimensionality reduction applied before clustering (currently: umap).",
        "n_neighbors":      "Number of neighbors used to build the local graph structure (UMAP / KNN).",
        "min_dist":         "UMAP parameter: how tightly points can cluster in reduced space.\nSmaller = tighter groups.",
        "dim_clust":        "Number of dimensions kept after reduction, used for clustering.",
        "k_cluster":        "Neighbors used during the clustering graph construction step.",
        "n_clusters":       "Number of clusters to produce (gmm, spectral).",
        "resolution":       "Leiden granularity. Lower → fewer clusters, higher → more clusters.",
        "min_cluster_size": "HDBSCAN minimum cluster size. Smaller allows rarer clusters.",
        "Number of shuffle":"Number of randomizations to build the null distribution for assortativity.",
        "Edges method":     "Delaunay: triangulation-based. KNN: k nearest neighbours.",
        "Min neighbors":    "Minimum number of neighbors for KNN edge generation.",
        "CPU":              "Number of CPU cores for parallel processing.",
    }

    def _add_form(self, tab_widget, title, section_key, data):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        for k, v in data.items():
            label = QLabel(k)
            tip = self.PARAM_TOOLTIPS.get(k)
            if tip:
                label.setToolTip(tip)
                label.setText(f"{k} ⓘ")
                label.setObjectName("SmallInfo")
            field = self._get_widget(k, v)
            if tip and hasattr(field, "setToolTip"):
                field.setToolTip(tip)
            form.addRow(label, field)
            self.entries.setdefault(section_key, {})[k] = field

        scroll.setWidget(inner)
        tab_widget.addTab(scroll, title)

    def _get_widget(self, key, value):
        if key in self.MULTI_COLUMN_FIELDS:
            widget = MultiSelectColumnsWidget(
                columns=self._nodes_columns,
                selected=value,
            )
            return widget

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

            combo = QComboBox()
            combo.addItems(["— select column —"] + self._nodes_columns)

            if value in (None, "index"):
                mode.setCurrentText("index")
                combo.setEnabled(False)
            else:
                mode.setCurrentText("Custom")
                if isinstance(value, str) and value in self._nodes_columns:
                    combo.setCurrentText(value)
                combo.setEnabled(True)

            def toggle_index_mode():
                is_custom = mode.currentText() == "Custom"
                combo.setEnabled(is_custom)
                if not is_custom:
                    combo.setCurrentIndex(0)

            mode.currentIndexChanged.connect(toggle_index_mode)

            row.addWidget(mode)
            row.addWidget(combo)

            container._mode_combo = mode
            container._value_combo = combo
            return container
        
        if key == "Network directory":
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)

            mode = QComboBox()
            mode.addItems(["Default", "Custom"])

            edit = QLineEdit()
            button = QPushButton("…")
            button.setMaximumWidth(32)

            if value in (None, "", "Default"):
                mode.setCurrentText("Default")
                edit.setText("")
                edit.setEnabled(False)
                button.setEnabled(False)
            else:
                mode.setCurrentText("Custom")
                edit.setText(str(value))
                edit.setEnabled(True)
                button.setEnabled(True)

            def browse_dir():
                selected = QFileDialog.getExistingDirectory(self, "Choose network directory")
                if selected:
                    edit.setText(selected)

            def toggle_network_mode():
                is_custom = mode.currentText() == "Custom"
                edit.setEnabled(is_custom)
                button.setEnabled(is_custom)
                if not is_custom:
                    edit.setText("")

            button.clicked.connect(browse_dir)
            mode.currentIndexChanged.connect(toggle_network_mode)

            row.addWidget(mode)
            row.addWidget(edit)
            row.addWidget(button)

            container._mode_combo = mode
            container._path_edit = edit
            container._browse_btn = button
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

                if key in self.MULTI_COLUMN_FIELDS and isinstance(widget, MultiSelectColumnsWidget):
                    current = widget.get_selected_values()
                    widget.set_columns(self._nodes_columns, selected=current)

                if key == "Index" and hasattr(widget, "_value_combo"):
                    current = widget._value_combo.currentText()
                    widget._value_combo.clear()
                    widget._value_combo.addItems(["— select column —"] + self._nodes_columns)
                    if current in self._nodes_columns:
                        widget._value_combo.setCurrentText(current)

    def parse_value(self, key, widget):

        if hasattr(widget, "_mode_combo") and hasattr(widget, "_path_edit"):
            mode = widget._mode_combo.currentText().strip()
            if mode != "Custom":
                return "Default"
            value = widget._path_edit.text().strip()
            return value or None

        if hasattr(widget, "_path_edit") and not hasattr(widget, "_mode_combo"):
            return widget._path_edit.text().strip() or None

        if hasattr(widget, "_mode_combo") and hasattr(widget, "_value_combo"):
            mode = widget._mode_combo.currentText().strip()
            if mode != "Custom":
                return "index"

            value = widget._value_combo.currentText().strip()
            if value.startswith("—"):
                return None
            return value or None
        
        if isinstance(widget, MultiSelectColumnsWidget):
            return widget.get_value()

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
        self.setWindowTitle("MOSNA Graphic Interface")
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
        self.viewer.load_documentation(DOC_HTML_PATH)
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
        self.params.stop_btn.clicked.connect(self._stop_script)

        for btn, script in zip(self.params.run_buttons, SCRIPTS):
            btn.clicked.connect(
                lambda _, s=script, b=btn: self._run_script(s, b.objectName())
            )

    def _stop_script(self):
        if self.script_thread is None or not self.script_thread.isRunning():
            return

        self.viewer.set_status("Stopping process...")
        self.script_thread.stop()
        self.params.stop_btn.setEnabled(False)

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
        self.browser.set_working_dir(self.working_dir)
        self._refresh_viewer_from_working_dir()
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
            else:
                raise ValueError(f"Unsupported extension: {path.suffix}")

            columns = list(df.columns)
            self.params.set_nodes_columns(columns)
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

    def _run_script(self, script_path, step_obj_name: str = ""):
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

        self.viewer.progress_start(f"Running: {script_path.name}", step_obj_name)
        self.script_thread = ScriptRunnerThread(cmd, cwd=self.working_dir, env=env)
        self.script_thread.output_line.connect(self._on_output_line)
        self.script_thread.finished_signal.connect(
            lambda ok, code, out, elapsed: self._on_finished(script_path, ok, code, out, elapsed)
        )
        self.params.stop_btn.setEnabled(True)
        self.script_thread.start()

    def _on_output_line(self, line):
        if not line:
            return

        # Always feed raw line into the log panel
        self.viewer.append_log(line)

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
        self.params.stop_btn.setEnabled(False)
        self.viewer.progress_stop(success)
        duration = self._format_duration(elapsed)

        if success:
            randomization_diagnostic = self.config_data.get("Assortativity", {}).get(
                "Randomization diagnostic", False
            )
            if randomization_diagnostic and script_path.name == 'assortativity.py':
                shuffle = self.config_data.get("Assortativity", {}).get(
                    "Number of shuffle", None
                )
                duration_diagnostic = self._format_duration((elapsed - 30) * shuffle/20)
                self.viewer.set_status(f"✅ {script_path.name} completed in {duration} - The shuffling will take {duration_diagnostic} to run with {shuffle} shuffles")
            else:
                self.viewer.set_status(f"✅ {script_path.name} completed in {duration}")

            analysis_images = self._collect_analysis_images()
            self.viewer.set_analysis_images(analysis_images)
            return

        output = (output or "").strip()[:4000]

        if output == "Process interrupted by user.":
            self.viewer.set_status(f"{script_path.name} stopped after {duration}")
            return

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

    def _list_images_in_folder(self, folder):
        images = []
        for pattern in ("*.png", "*.jpg", "*.jpeg", "*.svg"):
            images.extend(sorted(folder.glob(pattern)))
        return images

    def _extract_patient_sample(self, stem, prefix):
        pattern = rf"^{re.escape(prefix)}_(.+)$"
        match = re.match(pattern, stem)
        if not match:
            return None, None

        suffix = match.group(1).strip()
        parts = suffix.split("-")

        if len(parts) == 1:
            return parts[0], None

        if len(parts) >= 2:
            return parts[0], parts[1]

        return None, None

    def _collect_analysis_images(self):
        result = {
            "tysserand": {"patients": {}},
            "assortativity": {"global": [], "patients": {}},
            "niches": {"global": [], "patients": {}},
        }

        if not self.working_dir:
            return result

        working_dir = Path(self.working_dir)

        self._collect_tysserand_images(working_dir / "Tysserand_Network", result["tysserand"])
        self._collect_assortativity_images(working_dir / "Assortativity", result["assortativity"])
        self._collect_niches_images(working_dir / "Niches_Analysis", result["niches"])

        return result

    def _collect_tysserand_images(self, folder, target):
        if not folder.is_dir():
            return

        for img in self._list_images_in_folder(folder):
            patient, sample = self._extract_patient_sample(img.stem, "net")
            target["patients"].setdefault(patient, []).append(img)

    def _collect_assortativity_images(self, folder, target):
        if not folder.is_dir():
            return

        for item in sorted(folder.iterdir()):
            if item.is_file() and item.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg"}:
                target["global"].append(item)

        patient_dir = folder / "assort_files"
        if patient_dir.is_dir():
            for img in self._list_images_in_folder(patient_dir):
                patient, sample = self._extract_patient_sample(img.stem, "heatmap_zscore")
                if patient is None:
                    continue
                target["patients"].setdefault(patient, []).append(img)

    def _collect_niches_images(self, folder, target):
        if not folder.is_dir():
            return

        for img in self._list_images_in_folder(folder):
            stem = img.stem

            if stem.startswith("global_"):
                target["global"].append(img)
                continue

            patient, sample = self._extract_patient_sample(stem, "niches")
            if patient is None:
                target["global"].append(img)
            else:
                target["patients"].setdefault(patient, []).append(img)

    def _refresh_viewer_from_working_dir(self):
        """
        Reload the viewer from images already present in the working directory,
        without waiting for a script to be executed.
        """
        if not self.working_dir:
            return

        analysis_images = self._collect_analysis_images()
        self.viewer.set_analysis_images(analysis_images)

def main():
    app = QApplication(sys.argv)

    try:
        with open(BASE_DIR / "package" / "style.qss", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception:
        pass

    window = MosnaGUI()
    window.resize(1400, 900)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
