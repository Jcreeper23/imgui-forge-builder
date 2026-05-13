"""Live theme editor panel."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QColorDialog,
)

try:
    from .assets import THEME_PRESETS
    from .project_model import ProjectModel, Theme
    from .settings import BACKGROUND_TYPES
except ImportError:  # pragma: no cover
    from assets import THEME_PRESETS
    from project_model import ProjectModel, Theme
    from settings import BACKGROUND_TYPES


class ThemeEditor(QWidget):
    before_change = Signal()
    changed = Signal()

    COLOR_FIELDS = [
        ("background", "Legacy background"),
        ("primary_background", "Primary background"),
        ("secondary_background", "Secondary background"),
        ("panel", "Panel"),
        ("card", "Card"),
        ("sidebar", "Sidebar"),
        ("nav_active", "Nav active"),
        ("nav_hover", "Nav hover"),
        ("accent", "Accent"),
        ("accent2", "Second accent"),
        ("danger", "Danger"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("hover", "Hover"),
        ("active", "Active"),
        ("border", "Border"),
        ("shadow_color", "Shadow/glow"),
        ("text", "Text"),
        ("muted_text", "Muted text"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ThemeEditor")
        self.project: ProjectModel | None = None
        self._refreshing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("Theme")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)

        self.form = QFormLayout()
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addLayout(self.form)
        layout.addStretch(1)

    def set_project(self, project: ProjectModel) -> None:
        self.project = project
        self.refresh()

    def refresh(self) -> None:
        if not self.project:
            return
        self._refreshing = True
        while self.form.rowCount():
            self.form.removeRow(0)
        self._build_form()
        self._refreshing = False

    def _mutate(self, callback: Callable[[], None]) -> None:
        if self._refreshing:
            return
        self.before_change.emit()
        callback()
        self.changed.emit()

    def _build_form(self) -> None:
        assert self.project is not None
        theme = self.project.theme

        preset = QComboBox()
        preset.addItems(list(THEME_PRESETS.keys()))
        if self.project.selected_theme in THEME_PRESETS:
            preset.setCurrentText(self.project.selected_theme)
        preset.currentTextChanged.connect(lambda name: self._mutate(lambda: self._apply_preset(name)))
        self.form.addRow("Preset", preset)

        for attr, label in self.COLOR_FIELDS:
            self._color_row(label, getattr(theme, attr), lambda value, attr=attr: setattr(theme, attr, value))

        self._spin("Rounding", theme.rounding, lambda value: setattr(theme, "rounding", value), 0, 32)
        self._spin("Window padding", theme.window_padding, lambda value: setattr(theme, "window_padding", value), 2, 64)
        self._spin("Padding", theme.padding, lambda value: setattr(theme, "padding", value), 4, 48)
        self._spin("Frame padding", theme.frame_padding, lambda value: setattr(theme, "frame_padding", value), 2, 32)
        self._spin("Item spacing", theme.item_spacing, lambda value: setattr(theme, "item_spacing", value), 2, 40)
        self._double_spin("Font scale", theme.font_scale, lambda value: setattr(theme, "font_scale", value), 0.6, 2.0)
        self._spin("Border", theme.border_thickness, lambda value: setattr(theme, "border_thickness", value), 0, 6)
        self._spin("Button height", theme.button_height, lambda value: setattr(theme, "button_height", value), 20, 72)
        self._spin("Card padding", theme.card_padding, lambda value: setattr(theme, "card_padding", value), 4, 48)
        self._double_spin("Glow intensity", theme.glow_intensity, lambda value: setattr(theme, "glow_intensity", value), 0.0, 2.0)
        self._double_spin("Transparency", theme.alpha, lambda value: setattr(theme, "alpha", value), 0.2, 1.0)
        shadow = QComboBox()
        shadow.addItems(["none", "soft", "glow", "glass"])
        shadow.setCurrentText(theme.shadow if theme.shadow in {"none", "soft", "glow", "glass"} else "soft")
        shadow.currentTextChanged.connect(lambda text: self._mutate(lambda: setattr(theme, "shadow", text)))
        self.form.addRow("Shadow", shadow)

        self.form.addRow(self._section_label("Background"))
        background = self.project.background
        bg_type = QComboBox()
        bg_type.addItems(BACKGROUND_TYPES)
        bg_type.setCurrentText(background.type if background.type in BACKGROUND_TYPES else "Solid Color")
        bg_type.currentTextChanged.connect(lambda text: self._mutate(lambda: setattr(background, "type", text)))
        self.form.addRow("Type", bg_type)
        self._color_row("Primary", background.primary_color, lambda value: setattr(background, "primary_color", value))
        self._color_row("Secondary", background.secondary_color, lambda value: setattr(background, "secondary_color", value))
        self._color_row("Accent", background.accent_color, lambda value: setattr(background, "accent_color", value))
        self._double_spin("Animation speed", background.animation_speed, lambda value: setattr(background, "animation_speed", value), 0.0, 5.0)
        self._spin("Particles", background.particle_count, lambda value: setattr(background, "particle_count", value), 0, 240)
        self._spin("Grid size", background.grid_size, lambda value: setattr(background, "grid_size", value), 4, 96)
        self._double_spin("Glow", background.glow_intensity, lambda value: setattr(background, "glow_intensity", value), 0.0, 2.0)
        self._double_spin("Opacity", background.opacity, lambda value: setattr(background, "opacity", value), 0.05, 1.0)
        self._spin("Softness", background.softness, lambda value: setattr(background, "softness", value), 0, 80)

    def _apply_preset(self, name: str) -> None:
        assert self.project is not None
        data = THEME_PRESETS.get(name)
        if not data:
            return
        self.project.selected_theme = name
        self.project.theme = Theme.from_dict(data)
        self.project.background.primary_color = self.project.theme.primary_background
        self.project.background.secondary_color = self.project.theme.secondary_background
        self.project.background.accent_color = self.project.theme.accent
        self.refresh()

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("InspectorSection")
        return label

    def _color_row(self, label: str, value: str, setter: Callable[[str], None]) -> None:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        button = QPushButton(value)
        button.setMinimumHeight(26)
        swatch = QPushButton()
        swatch.setFixedWidth(34)

        def set_button_color(hex_value: str) -> None:
            color = QColor(hex_value)
            if not color.isValid():
                color = QColor("#555555")
            swatch.setStyleSheet(f"background: {color.name()}; border: 1px solid #596275;")

        def choose_color() -> None:
            chosen = QColorDialog.getColor(QColor(button.text()), self, f"Choose {label}")
            if chosen.isValid():
                hex_value = chosen.name()
                button.setText(hex_value)
                set_button_color(hex_value)
                self._mutate(lambda: setter(hex_value))

        def edit_text() -> None:
            text = button.text().strip()
            set_button_color(text)
            self._mutate(lambda: setter(text))

        set_button_color(value)
        button.clicked.connect(choose_color)
        button.setToolTip("Click to choose a color")
        swatch.clicked.connect(choose_color)
        layout.addWidget(button, 1)
        layout.addWidget(swatch)
        self.form.addRow(label, row)

    def _spin(self, label: str, value: int, setter: Callable[[int], None], minimum: int, maximum: int) -> None:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(int(value))
        spin.valueChanged.connect(lambda number: self._mutate(lambda: setter(int(number))))
        self.form.addRow(label, spin)

    def _double_spin(self, label: str, value: Any, setter: Callable[[float], None], minimum: float, maximum: float) -> None:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(2)
        spin.setSingleStep(0.05)
        try:
            spin.setValue(float(value))
        except (TypeError, ValueError):
            spin.setValue(1.0)
        spin.valueChanged.connect(lambda number: self._mutate(lambda: setter(float(number))))
        self.form.addRow(label, spin)
