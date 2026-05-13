"""Main PySide6 application shell for ImGui Forge Builder."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from .assets import TEMPLATE_LIBRARY, THEME_PRESETS
    from .canvas import PreviewCanvas
    from .code_exporter import export_cpp, export_element_cpp, validate_project
    from .components import COMPONENT_DEFINITIONS, TOOLBOX_ORDER, create_component, make_callback_name, make_variable_name
    from .presets import PresetsPanel, component_to_preset_spec, instantiate_components_from_preset, preset_by_name, save_custom_preset
    from .project_model import Animation, Background, Category, ProjectModel, Theme
    from .properties import PropertiesInspector
    from .save_system import SaveSystemError, load_project, save_project
    from .settings import (
        APP_NAME,
        APP_VERSION,
        DEFAULT_PROJECTS_DIR,
        DEFAULT_WINDOW_HEIGHT,
        DEFAULT_WINDOW_WIDTH,
        GRID_SIZES,
        MAX_UNDO_STATES,
        SUPPORTED_LAYOUT_MODES,
        SUPPORTED_NAV_POSITIONS,
        SUPPORTED_NAV_STYLES,
    )
    from .theme_editor import ThemeEditor
except ImportError:  # pragma: no cover
    from assets import TEMPLATE_LIBRARY, THEME_PRESETS
    from canvas import PreviewCanvas
    from code_exporter import export_cpp, export_element_cpp, validate_project
    from components import COMPONENT_DEFINITIONS, TOOLBOX_ORDER, create_component, make_callback_name, make_variable_name
    from presets import PresetsPanel, component_to_preset_spec, instantiate_components_from_preset, preset_by_name, save_custom_preset
    from project_model import Animation, Background, Category, ProjectModel, Theme
    from properties import PropertiesInspector
    from save_system import SaveSystemError, load_project, save_project
    from settings import (
        APP_NAME,
        APP_VERSION,
        DEFAULT_PROJECTS_DIR,
        DEFAULT_WINDOW_HEIGHT,
        DEFAULT_WINDOW_WIDTH,
        GRID_SIZES,
        MAX_UNDO_STATES,
        SUPPORTED_LAYOUT_MODES,
        SUPPORTED_NAV_POSITIONS,
        SUPPORTED_NAV_STYLES,
    )
    from theme_editor import ThemeEditor


class MainWindow(QMainWindow):
    """Composes the visual builder from independent panels."""

    def __init__(self):
        super().__init__()
        self.project = self._build_project_from_template("Minimal ImGui Menu")
        self.selected_kind = "project"
        self.selected_id = ""
        self.undo_stack: list[dict] = []
        self.redo_stack: list[dict] = []
        self._refreshing = False
        self._preview_mode = False
        self.last_project_path: Path | None = None

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self._apply_dark_style()
        self._build_ui()
        self._connect_signals()
        self._sync_ui(refresh_inspector=True, refresh_theme=True)
        self._append_log("ImGui Forge Builder ready.")

    # ---------------------------------------------------------------------
    # UI construction
    # ---------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.toolbar = self._build_toolbar()
        self.addToolBar(self.toolbar)

        self.left_panel = self._build_left_panel()
        self.canvas = PreviewCanvas()
        self.right_panel = self._build_right_panel()
        self.bottom_panel = self._build_bottom_panel()

        work_splitter = QSplitter(Qt.Orientation.Horizontal)
        work_splitter.addWidget(self.left_panel)
        work_splitter.addWidget(self.canvas)
        work_splitter.addWidget(self.right_panel)
        work_splitter.setStretchFactor(0, 0)
        work_splitter.setStretchFactor(1, 1)
        work_splitter.setStretchFactor(2, 0)
        work_splitter.setSizes([310, 760, 340])

        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.addWidget(work_splitter)
        main_splitter.addWidget(self.bottom_panel)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        main_splitter.setSizes([620, 190])
        self.setCentralWidget(main_splitter)
        self.statusBar().showMessage("Ready")

    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))

        def add_action(text: str, slot, shortcut: str | None = None, checkable: bool = False) -> QAction:
            action = QAction(text, self)
            action.triggered.connect(slot)
            action.setCheckable(checkable)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            toolbar.addAction(action)
            return action

        add_action("New", self.new_project, "Ctrl+N")
        add_action("Save", self.save_project_dialog, "Ctrl+S")
        add_action("Load", self.load_project_dialog, "Ctrl+O")
        add_action("Export Code", self.export_code_dialog, "Ctrl+E")
        add_action("Copy Code", self.copy_code, "Ctrl+Shift+C")
        add_action("Copy Element Code", self.copy_selected_element_code, "Ctrl+Alt+C")
        add_action("Save as Preset", self.save_selected_as_preset)
        toolbar.addSeparator()
        add_action("Undo", self.undo, "Ctrl+Z")
        add_action("Redo", self.redo, "Ctrl+Y")
        toolbar.addSeparator()
        add_action("Preview Mode", self.toggle_preview_mode, checkable=True)
        self.toggle_grid_action = add_action("Toggle Grid", self.toggle_grid, checkable=True)
        self.toggle_grid_action.setChecked(True)
        self.play_animations_action = add_action("Play Animations", self.toggle_animations, checkable=True)
        self.play_animations_action.setChecked(True)
        add_action("Reset Anim", self.reset_animation_preview)
        toolbar.addSeparator()
        add_action("Align Left", lambda: self.align_selected("left"))
        add_action("Align Center", lambda: self.align_selected("center"))
        add_action("Align Right", lambda: self.align_selected("right"))
        add_action("Distribute", self.distribute_active_components)
        toolbar.addSeparator()

        self.toolbar_theme_combo = QComboBox()
        self.toolbar_theme_combo.addItems(list(THEME_PRESETS.keys()))
        self.toolbar_theme_combo.setToolTip("Theme preset")
        toolbar.addWidget(QLabel("Theme"))
        toolbar.addWidget(self.toolbar_theme_combo)
        return toolbar

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("SidePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header = QLabel("Toolbox")
        header.setObjectName("PanelTitle")
        layout.addWidget(header)

        template_row = QHBoxLayout()
        self.template_combo = QComboBox()
        self.template_combo.addItems(list(TEMPLATE_LIBRARY.keys()))
        apply_template = QPushButton("Apply")
        apply_template.clicked.connect(lambda: self.apply_template(self.template_combo.currentText()))
        template_row.addWidget(self.template_combo, 1)
        template_row.addWidget(apply_template)
        layout.addLayout(template_row)

        toolbox_scroll = QScrollArea()
        toolbox_scroll.setWidgetResizable(True)
        toolbox_scroll.setObjectName("ToolboxScroll")
        toolbox_host = QWidget()
        toolbox_layout = QVBoxLayout(toolbox_host)
        toolbox_layout.setContentsMargins(0, 0, 0, 0)
        toolbox_layout.setSpacing(6)
        for component_type in TOOLBOX_ORDER:
            definition = COMPONENT_DEFINITIONS[component_type]
            button = QPushButton(f"+ {definition.title}")
            button.setToolTip(f"Add {definition.title} to the active category")
            button.clicked.connect(lambda checked=False, kind=component_type: self.add_component(kind))
            toolbox_layout.addWidget(button)
        toolbox_layout.addStretch(1)
        toolbox_scroll.setWidget(toolbox_host)
        layout.addWidget(toolbox_scroll, 2)

        categories_title = QLabel("Hierarchy")
        categories_title.setObjectName("PanelTitle")
        layout.addWidget(categories_title)

        self.hierarchy = QTreeWidget()
        self.hierarchy.setHeaderHidden(True)
        self.hierarchy.setAlternatingRowColors(False)
        self.hierarchy.setMinimumHeight(160)
        layout.addWidget(self.hierarchy, 2)

        row_one = QHBoxLayout()
        for label, slot in [
            ("Add Cat", self.add_category),
            ("Rename", self.rename_selected),
            ("Delete", self.delete_selected),
        ]:
            button = QPushButton(label)
            button.clicked.connect(slot)
            row_one.addWidget(button)
        layout.addLayout(row_one)

        row_two = QHBoxLayout()
        for label, slot in [
            ("Duplicate", self.duplicate_selected),
            ("Up", lambda: self.move_selected(-1)),
            ("Down", lambda: self.move_selected(1)),
        ]:
            button = QPushButton(label)
            button.clicked.connect(slot)
            row_two.addWidget(button)
        layout.addLayout(row_two)

        nav_title = QLabel("Layout")
        nav_title.setObjectName("PanelTitle")
        layout.addWidget(nav_title)

        self.nav_position_combo = QComboBox()
        self.nav_position_combo.addItems(SUPPORTED_NAV_POSITIONS)
        self.nav_style_combo = QComboBox()
        self.nav_style_combo.addItems(SUPPORTED_NAV_STYLES)
        self.layout_mode_combo = QComboBox()
        self.layout_mode_combo.addItems(SUPPORTED_LAYOUT_MODES)
        self.snap_check = QCheckBox("Snap to grid")
        self.grid_size_combo = QComboBox()
        self.grid_size_combo.addItems([str(size) for size in GRID_SIZES])
        layout.addWidget(QLabel("Nav position"))
        layout.addWidget(self.nav_position_combo)
        layout.addWidget(QLabel("Nav style"))
        layout.addWidget(self.nav_style_combo)
        layout.addWidget(QLabel("Layout mode"))
        layout.addWidget(self.layout_mode_combo)
        grid_row = QHBoxLayout()
        grid_row.addWidget(self.snap_check)
        grid_row.addWidget(self.grid_size_combo)
        layout.addLayout(grid_row)

        panel.setMinimumWidth(280)
        panel.setMaximumWidth(380)
        return panel

    def _build_right_panel(self) -> QWidget:
        tabs = QTabWidget()
        tabs.setObjectName("RightTabs")
        self.inspector = PropertiesInspector()
        self.theme_editor = ThemeEditor()
        self.presets_panel = PresetsPanel()
        tabs.addTab(self.inspector, "Properties")
        tabs.addTab(self.theme_editor, "Theme")
        tabs.addTab(self.presets_panel, "Presets")
        tabs.setMinimumWidth(320)
        tabs.setMaximumWidth(440)
        return tabs

    def _build_bottom_panel(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setObjectName("BottomTabs")
        self.code_output = QPlainTextEdit()
        self.code_output.setReadOnly(True)
        self.code_output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        tabs.addTab(self.code_output, "Generated C++")
        tabs.addTab(self.log_output, "Log")
        tabs.setMinimumHeight(150)
        return tabs

    def _connect_signals(self) -> None:
        self.canvas.component_selected.connect(self.select_component)
        self.canvas.category_selected.connect(self.select_category)
        self.canvas.before_mutation.connect(self._checkpoint)
        self.canvas.project_changed.connect(lambda: self._sync_ui(refresh_inspector=False, refresh_theme=False))

        self.inspector.before_change.connect(self._checkpoint)
        self.inspector.changed.connect(lambda: self._sync_ui(refresh_inspector=False, refresh_theme=False))
        self.theme_editor.before_change.connect(self._checkpoint)
        self.theme_editor.changed.connect(lambda: self._sync_ui(refresh_inspector=False, refresh_theme=False))
        self.presets_panel.add_preset_requested.connect(self.insert_preset)
        self.presets_panel.save_selected_requested.connect(self.save_selected_as_preset)

        self.hierarchy.itemClicked.connect(self._hierarchy_clicked)
        self.nav_position_combo.currentTextChanged.connect(lambda text: self._set_project_attr("nav_position", text))
        self.nav_style_combo.currentTextChanged.connect(lambda text: self._set_project_attr("nav_style", text))
        self.layout_mode_combo.currentTextChanged.connect(lambda text: self._set_project_attr("layout_mode", text))
        self.snap_check.stateChanged.connect(lambda state: self._set_project_attr("snap_to_grid", state == Qt.CheckState.Checked.value))
        self.grid_size_combo.currentTextChanged.connect(lambda text: self._set_project_attr("grid_size", int(text)))
        self.toolbar_theme_combo.currentTextChanged.connect(self.apply_theme_preset)

    # ---------------------------------------------------------------------
    # Project operations
    # ---------------------------------------------------------------------
    def new_project(self) -> None:
        self._checkpoint()
        self.project = self._build_project_from_template("Minimal ImGui Menu")
        self.selected_kind = "project"
        self.selected_id = ""
        self.last_project_path = None
        self._sync_ui(refresh_inspector=True, refresh_theme=True)
        self._append_log("New project created from the minimal template.")

    def apply_template(self, template_name: str) -> None:
        if template_name not in TEMPLATE_LIBRARY:
            return
        choice = QMessageBox(self)
        choice.setWindowTitle("Apply Template")
        choice.setText(f"Apply '{template_name}'?")
        replace_button = choice.addButton("Replace Project", QMessageBox.ButtonRole.AcceptRole)
        add_button = choice.addButton("Add to Current", QMessageBox.ButtonRole.ActionRole)
        choice.addButton(QMessageBox.StandardButton.Cancel)
        choice.setDefaultButton(replace_button)
        choice.exec()
        clicked = choice.clickedButton()
        if clicked is None or choice.standardButton(clicked) == QMessageBox.StandardButton.Cancel:
            return
        self._checkpoint()
        if clicked == add_button:
            template_project = self._build_project_from_template(template_name)
            self._merge_project(template_project)
            self.selected_kind = "category"
            self.selected_id = self.project.active_category_id
            self._append_log(f"Template added into current project: {template_name}")
        else:
            self.project = self._build_project_from_template(template_name)
            self.selected_kind = "project"
            self.selected_id = ""
            self._append_log(f"Template applied: {template_name}")
        self._sync_ui(refresh_inspector=True, refresh_theme=True)

    def apply_theme_preset(self, name: str) -> None:
        if self._refreshing or name not in THEME_PRESETS:
            return
        self._checkpoint()
        self.project.selected_theme = name
        self.project.theme = Theme.from_dict(THEME_PRESETS[name])
        self.project.background.primary_color = self.project.theme.primary_background
        self.project.background.secondary_color = self.project.theme.secondary_background
        self.project.background.accent_color = self.project.theme.accent
        self._sync_ui(refresh_inspector=False, refresh_theme=True)
        self._append_log(f"Theme preset applied: {name}")

    def add_category(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Category", "Category name:")
        if not ok:
            return
        self._checkpoint()
        category = self.project.add_category(name or "New Category", "[*]")
        self.selected_kind = "category"
        self.selected_id = category.id
        self._sync_ui(refresh_inspector=True, refresh_theme=False)
        self._append_log(f"Category added: {category.name}")

    def add_component(self, component_type: str) -> None:
        self._checkpoint()
        component = create_component(component_type)
        self._make_component_names_unique(component)
        self.project.add_component(component)
        self.selected_kind = "component"
        self.selected_id = component.id
        self._sync_ui(refresh_inspector=True, refresh_theme=False)
        self._append_log(f"Added component: {component.label}")

    def insert_preset(self, preset_name: str) -> None:
        preset = preset_by_name(preset_name)
        if not preset:
            self._append_log(f"Preset not found: {preset_name}")
            return
        self._checkpoint()
        group = self._insert_preset_data(preset, self.project, self.project.active_category_id)
        self._make_project_names_unique(self.project)
        if group:
            self.selected_kind = "group"
            self.selected_id = group.id
        else:
            self.selected_kind = "project"
            self.selected_id = ""
        self._sync_ui(refresh_inspector=True, refresh_theme=True)
        self._append_log(f"Preset inserted: {preset_name}")

    def rename_selected(self) -> None:
        if self.selected_kind == "group":
            group = self.project.find_group(self.selected_id)
            if not group:
                return
            text, ok = QInputDialog.getText(self, "Rename Group", "Group name:", text=group.name)
            if ok:
                self._checkpoint()
                group.name = text.strip() or "Preset Group"
                self._sync_ui(refresh_inspector=True, refresh_theme=False)
            return
        if self.selected_kind == "component":
            _, component = self.project.find_component(self.selected_id)
            if not component:
                return
            text, ok = QInputDialog.getText(self, "Rename Component", "Component label:", text=component.label)
            if ok:
                self._checkpoint()
                component.label = text
                self._sync_ui(refresh_inspector=True, refresh_theme=False)
            return

        category = self.project.find_category(self.selected_id) if self.selected_kind == "category" else self.project.active_category()
        text, ok = QInputDialog.getText(self, "Rename Category", "Category name:", text=category.name)
        if ok:
            self._checkpoint()
            category.name = text.strip() or "Category"
            self._sync_ui(refresh_inspector=True, refresh_theme=False)

    def delete_selected(self) -> None:
        if self.selected_kind == "group" and self.selected_id:
            group = self.project.find_group(self.selected_id)
            if group and QMessageBox.question(self, "Delete Group", f"Delete group '{group.name}' and its components?") == QMessageBox.StandardButton.Yes:
                self._checkpoint()
                self.project.delete_group(group.id, delete_components=True)
                self.selected_kind = "category"
                self.selected_id = self.project.active_category_id
                self._sync_ui(refresh_inspector=True, refresh_theme=False)
                self._append_log(f"Deleted group: {group.name}")
            return
        if self.selected_kind == "component" and self.selected_id:
            _, component = self.project.find_component(self.selected_id)
            if component and QMessageBox.question(self, "Delete Component", f"Delete '{component.label}'?") == QMessageBox.StandardButton.Yes:
                self._checkpoint()
                self.project.delete_component(component.id)
                self.selected_kind = "category"
                self.selected_id = self.project.active_category_id
                self._sync_ui(refresh_inspector=True, refresh_theme=False)
                self._append_log(f"Deleted component: {component.label}")
            return

        category = self.project.find_category(self.selected_id) if self.selected_kind == "category" else self.project.active_category()
        if len(self.project.categories) <= 1:
            QMessageBox.information(self, "Delete Category", "A project must keep at least one category.")
            return
        if QMessageBox.question(self, "Delete Category", f"Delete category '{category.name}' and its components?") == QMessageBox.StandardButton.Yes:
            self._checkpoint()
            self.project.delete_category(category.id)
            self.selected_kind = "category"
            self.selected_id = self.project.active_category_id
            self._sync_ui(refresh_inspector=True, refresh_theme=False)
            self._append_log(f"Deleted category: {category.name}")

    def duplicate_selected(self) -> None:
        if self.selected_kind == "group" and self.selected_id:
            self._checkpoint()
            duplicate = self.project.duplicate_group(self.selected_id)
            if duplicate:
                self._make_project_names_unique(self.project)
                self.selected_id = duplicate.id
                self._sync_ui(refresh_inspector=True, refresh_theme=False)
                self._append_log(f"Duplicated group: {duplicate.name}")
            return
        if self.selected_kind != "component" or not self.selected_id:
            return
        self._checkpoint()
        duplicate = self.project.duplicate_component(self.selected_id)
        if duplicate:
            self._make_component_names_unique(duplicate)
            self.selected_id = duplicate.id
            self._sync_ui(refresh_inspector=True, refresh_theme=False)
            self._append_log(f"Duplicated component: {duplicate.label}")

    def move_selected(self, delta: int) -> None:
        if self.selected_kind == "group" and self.selected_id:
            group = self.project.find_group(self.selected_id)
            if not group:
                return
            self._checkpoint()
            for component_id in group.component_ids:
                self.project.move_component(component_id, delta)
            self._sync_ui(refresh_inspector=False, refresh_theme=False)
            return
        if self.selected_kind == "component" and self.selected_id:
            self._checkpoint()
            if self.project.move_component(self.selected_id, delta):
                self._sync_ui(refresh_inspector=False, refresh_theme=False)
            return
        if self.selected_kind == "category" and self.selected_id:
            self._checkpoint()
            if self.project.move_category(self.selected_id, delta):
                self._sync_ui(refresh_inspector=False, refresh_theme=False)

    def select_component(self, component_id: str) -> None:
        if component_id:
            category, _ = self.project.find_component(component_id)
            if category:
                self.project.active_category_id = category.id
            self.selected_kind = "component"
            self.selected_id = component_id
        else:
            self.selected_kind = "project"
            self.selected_id = ""
        self._sync_ui(refresh_inspector=True, refresh_theme=False)

    def select_category(self, category_id: str) -> None:
        if not self.project.find_category(category_id):
            return
        self.project.active_category_id = category_id
        self.selected_kind = "category"
        self.selected_id = category_id
        self._sync_ui(refresh_inspector=True, refresh_theme=False)

    def select_group(self, group_id: str) -> None:
        group = self.project.find_group(group_id)
        if not group:
            return
        self.project.active_category_id = group.category_id
        self.selected_kind = "group"
        self.selected_id = group.id
        self._sync_ui(refresh_inspector=True, refresh_theme=False)

    def align_selected(self, mode: str) -> None:
        if self.selected_kind != "component":
            return
        _, component = self.project.find_component(self.selected_id)
        if not component:
            return
        self._checkpoint()
        content_width = self._approx_content_width()
        margin = self.project.theme.padding
        if mode == "center":
            component.x = max(0, int((content_width - component.width) / 2))
            component.auto_center = True
        elif mode == "right":
            component.x = max(0, int(content_width - component.width - margin))
            component.auto_center = False
        else:
            component.x = margin
            component.auto_center = False
        self.project.layout_mode = "free"
        self._sync_ui(refresh_inspector=True, refresh_theme=False)

    def distribute_active_components(self) -> None:
        category = self.project.active_category()
        if not category.components:
            return
        self._checkpoint()
        y = self.project.theme.padding
        for component in category.components:
            component.y = y
            if component.x < self.project.theme.padding:
                component.x = self.project.theme.padding
            y += component.height + self.project.theme.item_spacing
        self.project.layout_mode = "free"
        self._sync_ui(refresh_inspector=True, refresh_theme=False)
        self._append_log("Distributed active category components vertically.")

    def toggle_grid(self) -> None:
        self.canvas.show_grid = self.toggle_grid_action.isChecked()
        self.canvas.update()

    def toggle_animations(self) -> None:
        self.canvas.set_animations_playing(self.play_animations_action.isChecked())
        self.statusBar().showMessage("Animation preview playing" if self.play_animations_action.isChecked() else "Animation preview paused", 2000)

    def reset_animation_preview(self) -> None:
        self.canvas.reset_animation_preview()
        self.statusBar().showMessage("Animation preview reset", 2000)

    def toggle_preview_mode(self, checked: bool) -> None:
        self._preview_mode = checked
        self.left_panel.setVisible(not checked)
        self.right_panel.setVisible(not checked)
        self.bottom_panel.setVisible(not checked)
        self.statusBar().showMessage("Preview mode enabled" if checked else "Editor mode enabled", 2500)

    # ------------------------------------------------------------------
    # Save/load/export
    # ------------------------------------------------------------------
    def save_project_dialog(self) -> None:
        start = str(self.last_project_path or (Path.cwd() / DEFAULT_PROJECTS_DIR / "my_menu.json"))
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", start, "ImGui Forge Project (*.json)")
        if not path:
            return
        try:
            target = save_project(self.project, path)
        except SaveSystemError as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._append_log(str(exc))
            return
        self.last_project_path = target
        self._append_log(f"Project saved: {target}")

    def load_project_dialog(self) -> None:
        start = str(self.last_project_path or (Path.cwd() / DEFAULT_PROJECTS_DIR))
        path, _ = QFileDialog.getOpenFileName(self, "Load Project", start, "ImGui Forge Project (*.json);;All Files (*.*)")
        if not path:
            return
        try:
            project = load_project(path)
        except SaveSystemError as exc:
            QMessageBox.critical(self, "Load Failed", str(exc))
            self._append_log(str(exc))
            return
        self._checkpoint()
        self.project = project
        self.last_project_path = Path(path)
        self.selected_kind = "project"
        self.selected_id = ""
        self._sync_ui(refresh_inspector=True, refresh_theme=True)
        self._append_log(f"Project loaded: {path}")

    def export_code_dialog(self) -> None:
        warnings = validate_project(self.project)
        if warnings:
            self._append_log("Validation warnings before export:\n- " + "\n- ".join(warnings))
        start = str(Path.cwd() / "generated_menu.cpp")
        path, _ = QFileDialog.getSaveFileName(self, "Export Dear ImGui Code", start, "C++ Source (*.cpp);;All Files (*.*)")
        if not path:
            return
        try:
            Path(path).write_text(export_cpp(self.project), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
            self._append_log(f"Export failed: {exc}")
            return
        self._append_log(f"Generated Dear ImGui code exported: {path}")

    def copy_code(self) -> None:
        code = export_cpp(self.project)
        QApplication.clipboard().setText(code)
        warnings = validate_project(self.project)
        if warnings:
            self._append_log("Copied generated code with validation warnings:\n- " + "\n- ".join(warnings))
        else:
            self._append_log("Generated code copied to clipboard.")

    def copy_selected_element_code(self) -> None:
        code = export_element_cpp(self.project, self.selected_kind, self.selected_id)
        if not code:
            QMessageBox.information(self, "Copy Element Code", "Select a component or preset group first.")
            return
        QApplication.clipboard().setText(code)
        self._append_log("Selected element code copied to clipboard.")

    def save_selected_as_preset(self) -> None:
        components = []
        default_name = ""
        if self.selected_kind == "group":
            group = self.project.find_group(self.selected_id)
            if not group:
                QMessageBox.information(self, "Save Preset", "Select a group first.")
                return
            components = self.project.components_in_group(group.id)
            default_name = group.name
        elif self.selected_kind == "component":
            _, component = self.project.find_component(self.selected_id)
            if not component:
                QMessageBox.information(self, "Save Preset", "Select a component first.")
                return
            components = [component]
            default_name = component.label
        else:
            QMessageBox.information(self, "Save Preset", "Select a component or group first.")
            return
        name, ok = QInputDialog.getText(self, "Save as Preset", "Preset name:", text=default_name)
        if not ok or not name.strip():
            return
        category, ok = QInputDialog.getItem(
            self,
            "Preset Category",
            "Category:",
            [
                "Hero Sections",
                "Feature Cards",
                "Buttons",
                "Sliders",
                "Toggles",
                "Social Blocks",
                "Status Panels",
                "Login/Auth Blocks",
                "Config Blocks",
                "Info Panels",
                "Dashboard Cards",
                "Custom",
            ],
            editable=True,
        )
        if not ok:
            return
        preset = {
            "name": name.strip(),
            "category": category.strip() or "Custom",
            "description": "Custom preset saved from the current project.",
            "tags": ["custom"],
            "components": [component_to_preset_spec(component) for component in components],
        }
        if self.selected_kind == "group":
            group = self.project.find_group(self.selected_id)
            if group:
                preset["animation"] = group.animation.to_dict()
        try:
            target = save_custom_preset(preset)
        except OSError as exc:
            QMessageBox.critical(self, "Save Preset Failed", str(exc))
            return
        self.presets_panel.reload()
        self._append_log(f"Custom preset saved: {target}")

    # ------------------------------------------------------------------
    # Undo/redo and refresh
    # ------------------------------------------------------------------
    def undo(self) -> None:
        if not self.undo_stack:
            return
        self.redo_stack.append(self._snapshot())
        snapshot = self.undo_stack.pop()
        self._restore_snapshot(snapshot)
        self._append_log("Undo.")

    def redo(self) -> None:
        if not self.redo_stack:
            return
        self.undo_stack.append(self._snapshot())
        snapshot = self.redo_stack.pop()
        self._restore_snapshot(snapshot)
        self._append_log("Redo.")

    def _checkpoint(self) -> None:
        if self._refreshing:
            return
        snapshot = self._snapshot()
        if self.undo_stack and self.undo_stack[-1]["project"] == snapshot["project"]:
            return
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > MAX_UNDO_STATES:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _snapshot(self) -> dict:
        return {
            "project": self.project.to_dict(),
            "selected_kind": self.selected_kind,
            "selected_id": self.selected_id,
            "last_project_path": str(self.last_project_path) if self.last_project_path else "",
        }

    def _restore_snapshot(self, snapshot: dict) -> None:
        self.project = ProjectModel.from_dict(snapshot.get("project", {}))
        self.selected_kind = snapshot.get("selected_kind", "project")
        self.selected_id = snapshot.get("selected_id", "")
        path = snapshot.get("last_project_path") or ""
        self.last_project_path = Path(path) if path else None
        self._sync_ui(refresh_inspector=True, refresh_theme=True)

    def _sync_ui(self, refresh_inspector: bool, refresh_theme: bool) -> None:
        self._refreshing = True
        self.canvas.set_project(self.project)
        self.canvas.set_selected_component(self.selected_id if self.selected_kind == "component" else "")
        self._refresh_hierarchy()
        self._refresh_layout_controls()
        self._refresh_toolbar_theme()
        self.code_output.setPlainText(export_cpp(self.project))
        warnings = validate_project(self.project)
        self.statusBar().showMessage("Ready" if not warnings else f"{len(warnings)} validation warning(s)")
        self._refreshing = False
        if refresh_inspector:
            self.inspector.set_project(self.project)
            self.inspector.set_selection(self.selected_kind, self.selected_id)
        if refresh_theme:
            self.theme_editor.set_project(self.project)

    def _refresh_hierarchy(self) -> None:
        self.hierarchy.blockSignals(True)
        self.hierarchy.clear()
        for category in self.project.categories:
            category_label = f"{category.icon} {category.name}".strip()
            category_item = QTreeWidgetItem([category_label])
            category_item.setData(0, Qt.ItemDataRole.UserRole, "category")
            category_item.setData(0, Qt.ItemDataRole.UserRole + 1, category.id)
            if category.id == self.project.active_category_id:
                category_item.setSelected(self.selected_kind == "category" and self.selected_id == category.id)
                category_item.setText(0, f"* {category_label}")
            grouped_ids: set[str] = set()
            for group in self.project.groups_for_category(category.id):
                group_item = QTreeWidgetItem([f"[Group] {group.name}"])
                group_item.setData(0, Qt.ItemDataRole.UserRole, "group")
                group_item.setData(0, Qt.ItemDataRole.UserRole + 1, group.id)
                category_item.addChild(group_item)
                if self.selected_kind == "group" and self.selected_id == group.id:
                    group_item.setSelected(True)
                    category_item.setExpanded(True)
                for component in self.project.components_in_group(group.id):
                    grouped_ids.add(component.id)
                    definition = COMPONENT_DEFINITIONS.get(component.type)
                    type_title = definition.title if definition else component.type
                    component_item = QTreeWidgetItem([f"{component.label}  ({type_title})"])
                    component_item.setData(0, Qt.ItemDataRole.UserRole, "component")
                    component_item.setData(0, Qt.ItemDataRole.UserRole + 1, component.id)
                    group_item.addChild(component_item)
                    if self.selected_kind == "component" and self.selected_id == component.id:
                        component_item.setSelected(True)
                        category_item.setExpanded(True)
                        group_item.setExpanded(True)
                group_item.setExpanded(True)
            for component in category.components:
                if component.id in grouped_ids:
                    continue
                definition = COMPONENT_DEFINITIONS.get(component.type)
                type_title = definition.title if definition else component.type
                component_item = QTreeWidgetItem([f"{component.label}  ({type_title})"])
                component_item.setData(0, Qt.ItemDataRole.UserRole, "component")
                component_item.setData(0, Qt.ItemDataRole.UserRole + 1, component.id)
                category_item.addChild(component_item)
                if self.selected_kind == "component" and self.selected_id == component.id:
                    component_item.setSelected(True)
                    category_item.setExpanded(True)
            self.hierarchy.addTopLevelItem(category_item)
            category_item.setExpanded(True)
        self.hierarchy.blockSignals(False)

    def _refresh_layout_controls(self) -> None:
        for widget in [self.nav_position_combo, self.nav_style_combo, self.layout_mode_combo, self.grid_size_combo, self.snap_check]:
            widget.blockSignals(True)
        self.nav_position_combo.setCurrentText(self.project.nav_position)
        self.nav_style_combo.setCurrentText(self.project.nav_style)
        self.layout_mode_combo.setCurrentText(self.project.layout_mode)
        self.grid_size_combo.setCurrentText(str(self.project.grid_size))
        self.snap_check.setChecked(self.project.snap_to_grid)
        for widget in [self.nav_position_combo, self.nav_style_combo, self.layout_mode_combo, self.grid_size_combo, self.snap_check]:
            widget.blockSignals(False)

    def _refresh_toolbar_theme(self) -> None:
        self.toolbar_theme_combo.blockSignals(True)
        if self.project.selected_theme in THEME_PRESETS:
            self.toolbar_theme_combo.setCurrentText(self.project.selected_theme)
        self.toolbar_theme_combo.blockSignals(False)

    def _hierarchy_clicked(self, item: QTreeWidgetItem) -> None:
        kind = item.data(0, Qt.ItemDataRole.UserRole)
        object_id = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if kind == "component":
            self.select_component(object_id)
        elif kind == "category":
            self.select_category(object_id)
        elif kind == "group":
            self.select_group(object_id)

    def _set_project_attr(self, attr: str, value) -> None:
        if self._refreshing:
            return
        if getattr(self.project, attr) == value:
            return
        self._checkpoint()
        setattr(self.project, attr, value)
        self._sync_ui(refresh_inspector=False, refresh_theme=False)

    # ------------------------------------------------------------------
    # Template/model helpers
    # ------------------------------------------------------------------
    def _build_project_from_template(self, template_name: str) -> ProjectModel:
        template = TEMPLATE_LIBRARY[template_name]
        project = ProjectModel.create_default()
        project.categories = []
        project.project_name = template.get("project_name", "Untitled Menu")
        project.menu_title = template.get("menu_title", "ImGui Menu")
        project.nav_position = template.get("nav_position", "left")
        project.nav_style = template.get("nav_style", "vertical sidebar")
        project.layout_mode = template.get("layout_mode", "auto")
        theme_name = template.get("theme", "Dark Blue")
        project.selected_theme = theme_name if theme_name in THEME_PRESETS else "Dark Blue"
        project.theme = Theme.from_dict(THEME_PRESETS[project.selected_theme])
        if isinstance(template.get("background"), dict):
            project.background = Background.from_dict(template["background"])
        else:
            project.background.primary_color = project.theme.primary_background
            project.background.secondary_color = project.theme.secondary_background
            project.background.accent_color = project.theme.accent
        if isinstance(template.get("animation"), dict):
            project.animation = Animation.from_dict(template["animation"])

        for category_spec in template.get("categories", []):
            category = Category(name=category_spec.get("name", "Category"), icon=category_spec.get("icon", "[*]"))
            project.categories.append(category)
            project.active_category_id = category.id
            for preset_name in category_spec.get("presets", []):
                preset = preset_by_name(preset_name)
                if preset:
                    self._insert_preset_data(preset, project, category.id)
            for component_spec in category_spec.get("components", []):
                component = create_component(component_spec.get("type", "text_label"), component_spec.get("label"))
                for attr in ["width", "height", "x", "y", "auto_center", "visible", "enabled", "color", "text_color", "tooltip"]:
                    if attr in component_spec:
                        setattr(component, attr, component_spec[attr])
                if "props" in component_spec and isinstance(component_spec["props"], dict):
                    component.props.update(component_spec["props"])
                if "animation" in component_spec and isinstance(component_spec["animation"], dict):
                    component.animation = Animation.from_dict(component_spec["animation"])
                if component.type == "feature_card" and not component_spec.get("label"):
                    component.label = str(component.props.get("title", component.label))
                if component.type == "status_badge" and not component_spec.get("label"):
                    component.label = str(component.props.get("status", component.label))
                if component.type in {"checkbox", "slider_float", "slider_int", "combo_box", "input_text", "color_picker", "keybind"}:
                    component.variable_name = make_variable_name(component.label, component.type)
                if component.type in {"button", "icon_button"}:
                    component.props["callback_name"] = make_callback_name(component.label)
                component.category_id = category.id
                project.add_component(component, category.id)
        if not project.categories:
            project.categories.append(Category(name="Home", icon="[H]"))
        project.active_category_id = project.categories[0].id
        self._make_project_names_unique(project)
        return project

    def _insert_preset_data(self, preset: dict, project: ProjectModel, category_id: str):
        previous_active = project.active_category_id
        project.active_category_id = category_id
        if isinstance(preset.get("background"), dict):
            project.background = Background.from_dict({**project.background.to_dict(), **preset["background"]})
        theme_name = preset.get("theme")
        if theme_name in THEME_PRESETS:
            project.selected_theme = theme_name
            project.theme = Theme.from_dict(THEME_PRESETS[theme_name])
            project.background.primary_color = project.background.primary_color or project.theme.primary_background
            project.background.secondary_color = project.background.secondary_color or project.theme.secondary_background
            project.background.accent_color = project.background.accent_color or project.theme.accent
        if preset.get("nav_position"):
            project.nav_position = str(preset["nav_position"])
        if preset.get("nav_style"):
            project.nav_style = str(preset["nav_style"])
        components = instantiate_components_from_preset(preset, project)
        group = None
        if components:
            group = project.add_group(str(preset.get("name", "Preset Group")), category_id, [component.id for component in components], str(preset.get("name", "")))
            if isinstance(preset.get("animation"), dict):
                group.animation = Animation.from_dict(preset["animation"])
        project.active_category_id = category_id or previous_active
        return group

    def _merge_project(self, template_project: ProjectModel) -> None:
        self.project.selected_theme = template_project.selected_theme
        self.project.theme = Theme.from_dict(template_project.theme.to_dict())
        self.project.background = Background.from_dict(template_project.background.to_dict())
        self.project.animation = Animation.from_dict(template_project.animation.to_dict())
        self.project.nav_position = template_project.nav_position
        self.project.nav_style = template_project.nav_style
        for source_category in template_project.categories:
            category = self.project.add_category(self._unique_category_name(source_category.name), source_category.icon)
            id_map: dict[str, str] = {}
            for source_component in source_category.components:
                component = create_component(source_component.type, source_component.label)
                restored = source_component.to_dict()
                restored.pop("id", None)
                restored.pop("category_id", None)
                component = type(source_component).from_dict({**restored, "id": component.id})
                component.group_id = ""
                self.project.add_component(component, category.id)
                id_map[source_component.id] = component.id
            for source_group in template_project.groups_for_category(source_category.id):
                mapped_ids = [id_map[item] for item in source_group.component_ids if item in id_map]
                if mapped_ids:
                    group = self.project.add_group(source_group.name, category.id, mapped_ids, source_group.preset_name)
                    group.animation = Animation.from_dict(source_group.animation.to_dict())
        self._make_project_names_unique(self.project)

    def _unique_category_name(self, base_name: str) -> str:
        existing = {category.name for category in self.project.categories}
        if base_name not in existing:
            return base_name
        index = 2
        while f"{base_name} {index}" in existing:
            index += 1
        return f"{base_name} {index}"

    def _make_project_names_unique(self, project: ProjectModel) -> None:
        seen_vars: set[str] = set()
        seen_callbacks: set[str] = set()
        for component in project.all_components():
            self._make_component_names_unique(component, seen_vars, seen_callbacks, project)

    def _make_component_names_unique(
        self,
        component,
        seen_vars: set[str] | None = None,
        seen_callbacks: set[str] | None = None,
        project: ProjectModel | None = None,
    ) -> None:
        project = project or self.project
        seen_vars = seen_vars if seen_vars is not None else {item.variable_name for item in project.all_components() if item.id != component.id and item.variable_name}
        seen_callbacks = seen_callbacks if seen_callbacks is not None else {
            str(item.props.get("callback_name", "")) for item in project.all_components() if item.id != component.id and item.props.get("callback_name")
        }
        if component.variable_name:
            base = make_variable_name(component.variable_name, component.type)
            candidate = base
            index = 2
            while candidate in seen_vars:
                candidate = f"{base}_{index}"
                index += 1
            component.variable_name = candidate
            seen_vars.add(candidate)
        if component.type in {"button", "icon_button"}:
            base = make_callback_name(str(component.props.get("callback_name") or component.label))
            candidate = base
            index = 2
            while candidate in seen_callbacks:
                candidate = f"{base}{index}"
                index += 1
            component.props["callback_name"] = candidate
            seen_callbacks.add(candidate)

    def _approx_content_width(self) -> int:
        nav_width = 68 if self.project.nav_style == "icon sidebar" else 158
        if self.project.nav_position in {"left", "right"}:
            return max(160, self.project.window_width - nav_width)
        return self.project.window_width

    def _append_log(self, text: str) -> None:
        self.log_output.appendPlainText(text)

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _apply_dark_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #0f1117;
                color: #ecf1f8;
            }
            QWidget {
                color: #ecf1f8;
                font-size: 12px;
            }
            #SidePanel, #RightTabs, #BottomTabs {
                background: #141821;
            }
            QWidget#PropertiesInspector,
            QWidget#ThemeEditor,
            QWidget#PresetsPanel,
            QWidget#InspectorFormHost,
            QWidget#PresetListHost,
            QScrollArea QWidget#qt_scrollarea_viewport {
                background: #141821;
            }
            QFrame#PresetCard {
                background: #101722;
                border: 1px solid #30394b;
                border-radius: 8px;
            }
            QLabel#PresetTitle {
                font-size: 13px;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel#PresetThumb {
                background: #0d121a;
                border: 1px solid #263143;
                border-radius: 6px;
                color: #9ec1ff;
                padding: 6px;
            }
            QLabel#PresetDescription {
                color: #cbd5e1;
            }
            QLabel#PresetTags {
                color: #8fa3bd;
                font-size: 11px;
            }
            QLabel#PanelTitle {
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                padding: 2px 0 4px 0;
            }
            QLabel#InspectorSection {
                color: #9ec1ff;
                font-weight: 700;
                padding-top: 10px;
            }
            QPushButton, QToolButton {
                background: #232a37;
                border: 1px solid #343d4d;
                border-radius: 6px;
                padding: 6px 9px;
                color: #f2f5fb;
            }
            QPushButton:hover, QToolButton:hover {
                background: #2d3749;
                border-color: #4f8cff;
            }
            QPushButton:pressed, QToolButton:pressed {
                background: #315fbd;
            }
            QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTreeWidget {
                background: #10141c;
                border: 1px solid #30394b;
                border-radius: 6px;
                padding: 5px;
                selection-background-color: #315fbd;
                color: #f2f5fb;
            }
            QComboBox QAbstractItemView {
                background: #10141c;
                color: #f2f5fb;
                border: 1px solid #30394b;
                outline: 0;
                selection-background-color: #315fbd;
                selection-color: #ffffff;
            }
            QComboBox QAbstractItemView::item {
                min-height: 24px;
                padding: 5px 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #2d3749;
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #315fbd;
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #c7d2e3;
                margin-right: 7px;
            }
            QPlainTextEdit {
                font-family: Consolas, "Cascadia Mono", monospace;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background: #315fbd;
            }
            QTabWidget::pane {
                border: 1px solid #252c39;
                background: #141821;
            }
            QTabBar::tab {
                background: #1b2130;
                border: 1px solid #293244;
                padding: 7px 10px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #263147;
                color: #ffffff;
            }
            QToolBar {
                background: #111620;
                border-bottom: 1px solid #252c39;
                spacing: 6px;
                padding: 6px;
            }
            QToolBar QToolButton {
                margin-right: 3px;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QSplitter::handle {
                background: #202633;
            }
            QCheckBox {
                spacing: 6px;
            }
            QStatusBar {
                background: #10141c;
                color: #aab4c5;
            }
            """
        )


def serialize_project_for_debug(project: ProjectModel) -> str:
    """Small debug helper used during manual development."""

    return json.dumps(project.to_dict(), indent=2)
