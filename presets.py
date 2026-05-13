"""Element preset library, custom preset storage, and Presets panel UI."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

try:
    from .assets import ELEMENT_PRESETS, PRESET_CATEGORIES
    from .components import create_component, make_callback_name, make_variable_name
    from .project_model import Animation, Component, ProjectModel
    from .settings import CUSTOM_PRESETS_PATH
except ImportError:  # pragma: no cover
    from assets import ELEMENT_PRESETS, PRESET_CATEGORIES
    from components import create_component, make_callback_name, make_variable_name
    from project_model import Animation, Component, ProjectModel
    from settings import CUSTOM_PRESETS_PATH


def load_custom_presets(path: str | Path = CUSTOM_PRESETS_PATH) -> list[dict[str, Any]]:
    """Load user-created presets. Missing/corrupt files are treated as empty."""

    source = Path(path)
    if not source.exists():
        return []
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        data = data.get("presets", [])
    if not isinstance(data, list):
        return []
    presets = []
    for item in data:
        if isinstance(item, dict) and item.get("name") and isinstance(item.get("components", []), list):
            preset = copy.deepcopy(item)
            preset.setdefault("category", "Custom")
            preset.setdefault("description", "Custom user preset.")
            preset.setdefault("tags", ["custom"])
            preset["custom"] = True
            presets.append(preset)
    return presets


def save_custom_presets(presets: list[dict[str, Any]], path: str | Path = CUSTOM_PRESETS_PATH) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"presets": presets}, indent=2), encoding="utf-8")
    return target


def save_custom_preset(preset: dict[str, Any], path: str | Path = CUSTOM_PRESETS_PATH) -> Path:
    presets = load_custom_presets(path)
    presets = [item for item in presets if item.get("name") != preset.get("name")]
    item = copy.deepcopy(preset)
    item["custom"] = True
    presets.append(item)
    return save_custom_presets(presets, path)


def all_presets() -> list[dict[str, Any]]:
    return copy.deepcopy(ELEMENT_PRESETS) + load_custom_presets()


def preset_by_name(name: str) -> dict[str, Any] | None:
    for preset in all_presets():
        if preset.get("name") == name:
            return preset
    return None


def component_to_preset_spec(component: Component) -> dict[str, Any]:
    spec = component.to_dict()
    for key in ["id", "category_id", "group_id"]:
        spec.pop(key, None)
    return spec


def instantiate_components_from_preset(preset: dict[str, Any], project: ProjectModel) -> list[Component]:
    """Create real Component objects from a preset definition."""

    components: list[Component] = []
    base_y = project.theme.padding
    active_category = project.active_category()
    if active_category.components:
        base_y = max(item.y + item.height for item in active_category.components) + project.theme.item_spacing
    for index, spec in enumerate(preset.get("components", [])):
        if not isinstance(spec, dict):
            continue
        component = create_component(str(spec.get("type", "text_label")), spec.get("label"))
        component.width = int(spec.get("width", component.width))
        component.height = int(spec.get("height", component.height))
        component.x = int(spec.get("x", project.theme.padding))
        component.y = int(spec.get("y", base_y + index * (component.height + project.theme.item_spacing)))
        component.auto_center = bool(spec.get("auto_center", project.layout_mode == "auto"))
        component.visible = bool(spec.get("visible", component.visible))
        component.enabled = bool(spec.get("enabled", component.enabled))
        component.color = str(spec.get("color", component.color or ""))
        component.text_color = str(spec.get("text_color", component.text_color or ""))
        component.tooltip = str(spec.get("tooltip", component.tooltip or ""))
        if isinstance(spec.get("props"), dict):
            component.props.update(copy.deepcopy(spec["props"]))
        if isinstance(spec.get("animation"), dict):
            component.animation = Animation.from_dict(spec["animation"])
        if component.type in {"checkbox", "slider_float", "slider_int", "combo_box", "input_text", "color_picker", "keybind", "progress_bar"}:
            component.variable_name = make_variable_name(component.variable_name or component.label, component.type)
        if component.type in {"button", "icon_button"}:
            component.props["callback_name"] = make_callback_name(str(component.props.get("callback_name") or component.label))
        project.add_component(component)
        components.append(component)
    return components


class PresetCard(QFrame):
    add_requested = Signal(str)

    def __init__(self, preset: dict[str, Any], parent=None):
        super().__init__(parent)
        self.preset = preset
        self.setObjectName("PresetCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        title = QLabel(str(preset.get("name", "Preset")))
        title.setObjectName("PresetTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        thumb = QLabel(self._thumbnail_text(preset))
        thumb.setObjectName("PresetThumb")
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setMinimumHeight(54)
        layout.addWidget(thumb)

        description = QLabel(str(preset.get("description", "")))
        description.setWordWrap(True)
        description.setObjectName("PresetDescription")
        layout.addWidget(description)

        tags = preset.get("tags", [])
        tag_label = QLabel(", ".join(str(tag) for tag in tags[:5]) if isinstance(tags, list) else str(tags))
        tag_label.setObjectName("PresetTags")
        tag_label.setWordWrap(True)
        layout.addWidget(tag_label)

        button = QPushButton("Add to Menu")
        button.clicked.connect(lambda: self.add_requested.emit(str(preset.get("name", ""))))
        layout.addWidget(button)

    @staticmethod
    def _thumbnail_text(preset: dict[str, Any]) -> str:
        category = str(preset.get("category", "Preset"))
        count = len(preset.get("components", [])) if isinstance(preset.get("components"), list) else 0
        if preset.get("background"):
            return f"{category}\nBackground + {count} item(s)"
        return f"{category}\n{count} editable item(s)"


class PresetsPanel(QWidget):
    add_preset_requested = Signal(str)
    save_selected_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PresetsPanel")
        self._presets: list[dict[str, Any]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("Element Presets")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search presets")
        layout.addWidget(self.search)

        self.category_filter = QComboBox()
        self.category_filter.addItems(PRESET_CATEGORIES + ["Custom"])
        layout.addWidget(self.category_filter)

        save_button = QPushButton("Save Selected as Preset")
        save_button.clicked.connect(self.save_selected_requested.emit)
        layout.addWidget(save_button)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.host = QWidget()
        self.host.setObjectName("PresetListHost")
        self.list_layout = QVBoxLayout(self.host)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.scroll.setWidget(self.host)
        layout.addWidget(self.scroll, 1)

        self.search.textChanged.connect(self.refresh)
        self.category_filter.currentTextChanged.connect(self.refresh)
        self.reload()

    def reload(self) -> None:
        self._presets = all_presets()
        self.refresh()

    def refresh(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        query = self.search.text().strip().lower()
        category = self.category_filter.currentText()
        matches = []
        for preset in self._presets:
            tags = preset.get("tags", [])
            haystack = " ".join(
                [
                    str(preset.get("name", "")),
                    str(preset.get("description", "")),
                    str(preset.get("category", "")),
                    " ".join(str(tag) for tag in tags) if isinstance(tags, list) else str(tags),
                ]
            ).lower()
            if query and query not in haystack:
                continue
            if category not in {"All", str(preset.get("category", ""))}:
                continue
            matches.append(preset)
        for preset in matches:
            card = PresetCard(preset)
            card.add_requested.connect(self.add_preset_requested)
            self.list_layout.addWidget(card)
        if not matches:
            empty = QLabel("No presets match the current filter.")
            empty.setWordWrap(True)
            self.list_layout.addWidget(empty)
        self.list_layout.addStretch(1)
