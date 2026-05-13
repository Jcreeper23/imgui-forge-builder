"""Right-side properties inspector for project, category, and component edits."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

try:
    from .assets import ICON_PRESETS, SOCIAL_PLATFORMS
    from .components import COMPONENT_DEFINITIONS, INTERACTIVE_TYPES
    from .project_model import Animation, Category, Component, Group, ProjectModel
    from .settings import ANIMATION_TYPES, EASING_TYPES, GRID_SIZES, SUPPORTED_LAYOUT_MODES, SUPPORTED_NAV_POSITIONS, SUPPORTED_NAV_STYLES
except ImportError:  # pragma: no cover
    from assets import ICON_PRESETS, SOCIAL_PLATFORMS
    from components import COMPONENT_DEFINITIONS, INTERACTIVE_TYPES
    from project_model import Animation, Category, Component, Group, ProjectModel
    from settings import ANIMATION_TYPES, EASING_TYPES, GRID_SIZES, SUPPORTED_LAYOUT_MODES, SUPPORTED_NAV_POSITIONS, SUPPORTED_NAV_STYLES


class PropertiesInspector(QWidget):
    before_change = Signal()
    changed = Signal()
    selection_changed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PropertiesInspector")
        self.project: ProjectModel | None = None
        self.selection_kind = "project"
        self.selection_id = ""
        self._refreshing = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        self.title_label = QLabel("Properties")
        self.title_label.setObjectName("PanelTitle")
        outer.addWidget(self.title_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(self.scroll, 1)

        self.form_host = QWidget()
        self.form_host.setObjectName("InspectorFormHost")
        self.form = QFormLayout(self.form_host)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        self.form.setContentsMargins(4, 4, 4, 4)
        self.form.setVerticalSpacing(8)
        self.scroll.setWidget(self.form_host)

    def set_project(self, project: ProjectModel) -> None:
        self.project = project
        self.refresh()

    def set_selection(self, kind: str, object_id: str = "") -> None:
        self.selection_kind = kind or "project"
        self.selection_id = object_id or ""
        self.refresh()

    def refresh(self) -> None:
        if not self.project:
            return
        self._refreshing = True
        self._clear_form()

        if self.selection_kind == "component" and self.selection_id:
            _, component = self.project.find_component(self.selection_id)
            if component:
                self.title_label.setText(f"Component: {component.label}")
                self._build_component_form(component)
            else:
                self.selection_kind = "project"
                self._build_project_form()
        elif self.selection_kind == "group" and self.selection_id:
            group = self.project.find_group(self.selection_id)
            if group:
                self.title_label.setText(f"Group: {group.name}")
                self._build_group_form(group)
            else:
                self.selection_kind = "project"
                self._build_project_form()
        elif self.selection_kind == "category" and self.selection_id:
            category = self.project.find_category(self.selection_id)
            if category:
                self.title_label.setText(f"Category: {category.name}")
                self._build_category_form(category)
            else:
                self.selection_kind = "project"
                self._build_project_form()
        else:
            self.title_label.setText("Project Properties")
            self._build_project_form()

        self._refreshing = False

    def _clear_form(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)

    def _mutate(self, callback: Callable[[], None]) -> None:
        if self._refreshing:
            return
        self.before_change.emit()
        callback()
        self.changed.emit()

    def _section(self, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("InspectorSection")
        self.form.addRow(label)

    def _line(self, label: str, value: Any, setter: Callable[[str], None], placeholder: str = "") -> QLineEdit:
        edit = QLineEdit(str(value if value is not None else ""))
        edit.setPlaceholderText(placeholder)
        edit.editingFinished.connect(lambda: self._mutate(lambda: setter(edit.text())))
        self.form.addRow(label, edit)
        return edit

    def _color_line(self, label: str, value: str, setter: Callable[[str], None]) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        edit = QLineEdit(value)
        button = QPushButton()
        button.setFixedWidth(34)

        def update_button(hex_value: str) -> None:
            color = QColor(hex_value)
            if not color.isValid():
                color = QColor("#555555")
            button.setStyleSheet(f"background: {color.name()}; border: 1px solid #596275;")

        def pick() -> None:
            chosen = QColorDialog.getColor(QColor(edit.text() or "#ffffff"), self, "Choose Color")
            if chosen.isValid():
                edit.setText(chosen.name())
                self._mutate(lambda: setter(chosen.name()))
                update_button(chosen.name())

        update_button(value)
        edit.editingFinished.connect(lambda: self._mutate(lambda: setter(edit.text())))
        edit.textChanged.connect(update_button)
        button.clicked.connect(pick)
        layout.addWidget(edit, 1)
        layout.addWidget(button)
        self.form.addRow(label, row)

    def _spin(self, label: str, value: int, setter: Callable[[int], None], minimum: int = 0, maximum: int = 5000) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(int(value))
        spin.valueChanged.connect(lambda number: self._mutate(lambda: setter(int(number))))
        self.form.addRow(label, spin)
        return spin

    def _double_spin(
        self,
        label: str,
        value: float,
        setter: Callable[[float], None],
        minimum: float = -10000.0,
        maximum: float = 10000.0,
        decimals: int = 3,
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setSingleStep(0.1)
        try:
            spin.setValue(float(value))
        except (TypeError, ValueError):
            spin.setValue(0.0)
        spin.valueChanged.connect(lambda number: self._mutate(lambda: setter(float(number))))
        self.form.addRow(label, spin)
        return spin

    def _check(self, label: str, value: bool, setter: Callable[[bool], None]) -> QCheckBox:
        check = QCheckBox()
        check.setChecked(bool(value))
        check.stateChanged.connect(lambda state: self._mutate(lambda: setter(state == Qt.CheckState.Checked.value)))
        self.form.addRow(label, check)
        return check

    def _combo(self, label: str, options: list[str], value: str, setter: Callable[[str], None]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(options)
        if value in options:
            combo.setCurrentText(value)
        combo.currentTextChanged.connect(lambda text: self._mutate(lambda: setter(text)))
        self.form.addRow(label, combo)
        return combo

    def _build_project_form(self) -> None:
        assert self.project is not None
        project = self.project
        self._section("Project")
        self._line("Project name", project.project_name, lambda text: setattr(project, "project_name", text))
        self._line("Menu title", project.menu_title, lambda text: setattr(project, "menu_title", text))
        self._spin("Window width", project.window_width, lambda value: setattr(project, "window_width", value), 220, 2400)
        self._spin("Window height", project.window_height, lambda value: setattr(project, "window_height", value), 180, 1800)

        self._section("Navigation")
        self._combo("Position", SUPPORTED_NAV_POSITIONS, project.nav_position, lambda text: setattr(project, "nav_position", text))
        self._combo("Style", SUPPORTED_NAV_STYLES, project.nav_style, lambda text: setattr(project, "nav_style", text))
        self._combo("Layout mode", SUPPORTED_LAYOUT_MODES, project.layout_mode, lambda text: setattr(project, "layout_mode", text))
        self._check("Snap to grid", project.snap_to_grid, lambda value: setattr(project, "snap_to_grid", value))
        self._combo("Grid size", [str(size) for size in GRID_SIZES], str(project.grid_size), lambda text: setattr(project, "grid_size", int(text)))
        self._section("Menu Animation")
        self._animation_fields(project.animation)

    def _build_category_form(self, category: Category) -> None:
        assert self.project is not None
        self._section("Category")
        self._line("Name", category.name, lambda text: setattr(category, "name", text.strip() or "Category"))
        icon_combo = self._combo("Icon", ICON_PRESETS, category.icon, lambda text: setattr(category, "icon", text))
        icon_combo.setEditable(True)
        self._check("Active", category.id == self.project.active_category_id, lambda value: setattr(self.project, "active_category_id", category.id) if value else None)
        self._section("Stats")
        self.form.addRow("Components", QLabel(str(len(category.components))))
        self.form.addRow("Groups", QLabel(str(len(self.project.groups_for_category(category.id)))))

    def _build_group_form(self, group: Group) -> None:
        assert self.project is not None
        self._section("Preset Group")
        self._line("Name", group.name, lambda text: setattr(group, "name", text.strip() or "Preset Group"))
        self.form.addRow("Preset", QLabel(group.preset_name or "Custom group"))
        category_names = [category.name for category in self.project.categories]
        category_by_name = {category.name: category.id for category in self.project.categories}
        current_category = self.project.find_category(group.category_id) or self.project.active_category()

        def move_group(category_name: str) -> None:
            category_id = category_by_name[category_name]
            group.category_id = category_id
            for component in self.project.components_in_group(group.id):
                self.project.move_component_to_category(component.id, category_id)

        self._combo("Category", category_names, current_category.name, move_group)
        self.form.addRow("Components", QLabel(str(len(group.component_ids))))
        self._section("Group Animation")
        self._animation_fields(group.animation)

    def _build_component_form(self, component: Component) -> None:
        assert self.project is not None
        definition = COMPONENT_DEFINITIONS.get(component.type)
        type_name = definition.title if definition else component.type

        self._section("Component")
        self.form.addRow("Type", QLabel(type_name))
        self._line("Label / text", component.label, lambda text: setattr(component, "label", text))
        if component.type in INTERACTIVE_TYPES:
            self._line("Variable", component.variable_name, lambda text: setattr(component, "variable_name", text.strip()))
        self._spin("Width", component.width, lambda value: setattr(component, "width", value), 20, 1600)
        self._spin("Height", component.height, lambda value: setattr(component, "height", value), 12, 900)
        self._spin("X", component.x, lambda value: setattr(component, "x", value), 0, 5000)
        self._spin("Y", component.y, lambda value: setattr(component, "y", value), 0, 5000)
        self._check("Auto center", component.auto_center, lambda value: setattr(component, "auto_center", value))
        self._check("Visible", component.visible, lambda value: setattr(component, "visible", value))
        self._check("Enabled", component.enabled, lambda value: setattr(component, "enabled", value))
        self._color_line("Override color", component.color, lambda text: setattr(component, "color", text.strip()))
        self._color_line("Text color", component.text_color, lambda text: setattr(component, "text_color", text.strip()))
        self._line("Tooltip", component.tooltip, lambda text: setattr(component, "tooltip", text))

        category_names = [category.name for category in self.project.categories]
        category_by_name = {category.name: category.id for category in self.project.categories}
        current_category = self.project.find_category(component.category_id) or self.project.active_category()
        self._combo("Category", category_names, current_category.name, lambda name: self.project.move_component_to_category(component.id, category_by_name[name]))
        if component.group_id:
            group = self.project.find_group(component.group_id)
            self.form.addRow("Group", QLabel(group.name if group else component.group_id))

        self._section("Type Settings")
        self._component_type_fields(component)
        self._section("Animation")
        self._animation_fields(component.animation)

    def _prop_line(self, component: Component, label: str, key: str, placeholder: str = "") -> None:
        self._line(label, component.props.get(key, ""), lambda text: component.props.__setitem__(key, text), placeholder)

    def _prop_color(self, component: Component, label: str, key: str) -> None:
        self._color_line(label, str(component.props.get(key, "")), lambda text: component.props.__setitem__(key, text))

    def _prop_check(self, component: Component, label: str, key: str) -> None:
        self._check(label, bool(component.props.get(key, False)), lambda value: component.props.__setitem__(key, value))

    def _component_type_fields(self, component: Component) -> None:
        props = component.props
        if component.type in {"button", "icon_button"}:
            self._prop_line(component, "Callback", "callback_name")
            icon_combo = self._combo("Icon", ICON_PRESETS, str(props.get("icon", "")), lambda text: props.__setitem__("icon", text))
            icon_combo.setEditable(True)
            self._prop_line(component, "Button style", "button_style")
        elif component.type == "checkbox":
            self._prop_check(component, "Default value", "default_value")
        elif component.type == "slider_float":
            self._double_spin("Min", props.get("min", 0.0), lambda value: props.__setitem__("min", value))
            self._double_spin("Max", props.get("max", 1.0), lambda value: props.__setitem__("max", value))
            self._double_spin("Default", props.get("default_value", 0.5), lambda value: props.__setitem__("default_value", value))
            self._prop_line(component, "Format", "format", "%.2f")
        elif component.type == "slider_int":
            self._spin("Min", int(props.get("min", 0)), lambda value: props.__setitem__("min", value), -100000, 100000)
            self._spin("Max", int(props.get("max", 100)), lambda value: props.__setitem__("max", value), -100000, 100000)
            self._spin("Default", int(props.get("default_value", 50)), lambda value: props.__setitem__("default_value", value), -100000, 100000)
            self._prop_line(component, "Format", "format", "%d")
        elif component.type == "combo_box":
            options = props.get("options", [])
            text = ", ".join(options) if isinstance(options, list) else str(options)
            self._line("Options", text, lambda value: props.__setitem__("options", [item.strip() for item in value.split(",") if item.strip()]))
            self._spin("Default index", int(props.get("default_index", 0)), lambda value: props.__setitem__("default_index", value), 0, 200)
        elif component.type == "input_text":
            self._prop_line(component, "Default text", "default_text")
            self._spin("Buffer size", int(props.get("buffer_size", 128)), lambda value: props.__setitem__("buffer_size", value), 8, 4096)
        elif component.type == "color_picker":
            color = props.get("default_color", [1.0, 0.35, 0.2, 1.0])
            text = ", ".join(str(item) for item in color) if isinstance(color, list) else str(color)
            self._line("Default RGBA", text, lambda value: props.__setitem__("default_color", self._parse_float_list(value, 4)))
        elif component.type == "keybind":
            self._prop_line(component, "Default key", "default_key")
        elif component.type == "social_link":
            platform_combo = self._combo("Platform", list(SOCIAL_PLATFORMS.keys()), str(props.get("platform", "GitHub")), lambda text: self._set_social_platform(component, text))
            platform_combo.setEditable(True)
            self._prop_line(component, "URL", "url")
            icon_combo = self._combo("Icon", ICON_PRESETS, str(props.get("icon", "")), lambda text: props.__setitem__("icon", text))
            icon_combo.setEditable(True)
            self._prop_line(component, "Button style", "button_style")
        elif component.type == "feature_card":
            self._prop_line(component, "Title", "title")
            self._prop_line(component, "Description", "description")
            self._prop_line(component, "Icon", "icon")
            self._prop_line(component, "Button text", "button_text")
            self._prop_check(component, "Locked", "locked")
        elif component.type == "status_badge":
            self._prop_line(component, "Status", "status")
            self._prop_color(component, "Badge color", "badge_color")
        elif component.type == "progress_bar":
            self._double_spin("Value", component.props.get("value", 0.65), lambda value: component.props.__setitem__("value", value), 0.0, 1.0)
            self._double_spin("Min", component.props.get("min", 0.0), lambda value: component.props.__setitem__("min", value), -10000.0, 10000.0)
            self._double_spin("Max", component.props.get("max", 1.0), lambda value: component.props.__setitem__("max", value), -10000.0, 10000.0)
            self._prop_line(component, "Overlay", "overlay")
        elif component.type == "image_placeholder":
            self._prop_line(component, "Placeholder", "placeholder")
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit(str(props.get("icon_path", "")))
            browse = QPushButton("Browse")

            def choose() -> None:
                path, _ = QFileDialog.getOpenFileName(self, "Choose Icon/Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*.*)")
                if path:
                    edit.setText(path)
                    self._mutate(lambda: props.__setitem__("icon_path", path))

            edit.editingFinished.connect(lambda: self._mutate(lambda: props.__setitem__("icon_path", edit.text())))
            browse.clicked.connect(choose)
            layout.addWidget(edit, 1)
            layout.addWidget(browse)
            self.form.addRow("Image path", row)
        elif component.type == "nav_category":
            icon_combo = self._combo("Icon", ICON_PRESETS, str(props.get("icon", "[>]")), lambda text: props.__setitem__("icon", text))
            icon_combo.setEditable(True)
        elif component.type == "tab_button":
            self._prop_check(component, "Active", "active")
        else:
            self.form.addRow(QLabel("No extra settings."))

    def _animation_fields(self, animation: Animation) -> None:
        self._check("Enabled", animation.enabled, lambda value: setattr(animation, "enabled", value))
        self._combo("Type", ANIMATION_TYPES, animation.type if animation.type in ANIMATION_TYPES else "None", lambda text: setattr(animation, "type", text))
        self._double_spin("Duration", animation.duration, lambda value: setattr(animation, "duration", value), 0.0, 10.0)
        self._double_spin("Delay", animation.delay, lambda value: setattr(animation, "delay", value), 0.0, 10.0)
        self._double_spin("Speed", animation.speed, lambda value: setattr(animation, "speed", value), 0.0, 10.0)
        self._double_spin("Intensity", animation.intensity, lambda value: setattr(animation, "intensity", value), 0.0, 3.0)
        self._check("Loop", animation.loop, lambda value: setattr(animation, "loop", value))
        self._combo("Easing", EASING_TYPES, animation.easing if animation.easing in EASING_TYPES else "ease in out", lambda text: setattr(animation, "easing", text))

    def _set_social_platform(self, component: Component, platform: str) -> None:
        component.props["platform"] = platform
        preset = SOCIAL_PLATFORMS.get(platform)
        if preset:
            component.props["icon"] = preset["icon"]
            if not component.props.get("url"):
                component.props["url"] = preset["url"]

    @staticmethod
    def _parse_float_list(text: str, count: int) -> list[float]:
        values: list[float] = []
        for piece in text.split(","):
            try:
                values.append(float(piece.strip()))
            except ValueError:
                values.append(1.0)
        while len(values) < count:
            values.append(1.0)
        return values[:count]
