"""Central live preview canvas.

The canvas paints an ImGui-inspired approximation instead of embedding Dear ImGui.
That keeps the editor portable while preserving the important design feedback:
spacing, navigation placement, colors, widget order, and free-layout positions.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

try:
    from .project_model import Animation, Component, ProjectModel
except ImportError:  # pragma: no cover
    from project_model import Animation, Component, ProjectModel


def _color(hex_color: str, fallback: str = "#ffffff") -> QColor:
    value = QColor(hex_color or fallback)
    if not value.isValid():
        value = QColor(fallback)
    return value


def _with_alpha(color: QColor, alpha: int) -> QColor:
    copy = QColor(color)
    copy.setAlpha(max(0, min(255, alpha)))
    return copy


class PreviewCanvas(QWidget):
    component_selected = Signal(str)
    category_selected = Signal(str)
    before_mutation = Signal()
    project_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: ProjectModel | None = None
        self.selected_component_id = ""
        self.show_grid = True
        self.component_rects: dict[str, QRectF] = {}
        self.category_rects: dict[str, QRectF] = {}
        self._last_content_rect = QRectF()
        self._last_scale = 1.0
        self._animation_time = 0.0
        self.animations_playing = True
        self._hover_component_id = ""
        self._dragging_component: Component | None = None
        self._drag_offset = QPointF()
        self._drag_checkpoint_taken = False
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self.setMinimumSize(QSize(560, 420))
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def set_project(self, project: ProjectModel) -> None:
        self.project = project
        self.update()

    def set_selected_component(self, component_id: str) -> None:
        self.selected_component_id = component_id
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(760, 560)

    def set_animations_playing(self, playing: bool) -> None:
        self.animations_playing = playing
        self.update()

    def reset_animation_preview(self) -> None:
        self._animation_time = 0.0
        self.update()

    def _tick(self) -> None:
        if self.animations_playing:
            self._animation_time += 0.033
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#0f1117"))

        if not self.project:
            painter.setPen(QColor("#8c95a8"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No project loaded")
            return

        self.component_rects.clear()
        self.category_rects.clear()

        preview_rect, scale = self._preview_rect()
        self._last_scale = scale
        theme = self.project.theme

        if theme.shadow != "none":
            shadow_color = QColor("#000000")
            shadow_color.setAlpha(90 if theme.shadow != "glow" else 130)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(shadow_color)
            painter.drawRoundedRect(preview_rect.adjusted(8, 10, 8, 10), theme.rounding + 4, theme.rounding + 4)
            if theme.shadow == "glow":
                glow = _with_alpha(_color(theme.accent), 55)
                painter.setBrush(glow)
                painter.drawRoundedRect(preview_rect.adjusted(-5, -5, 5, 5), theme.rounding + 8, theme.rounding + 8)

        self._draw_menu_background(painter, preview_rect, scale)
        painter.setPen(QPen(_color(theme.border), max(1, theme.border_thickness)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(preview_rect, theme.rounding, theme.rounding)

        title_height = max(28.0, 34.0 * scale)
        title_rect = QRectF(preview_rect.left(), preview_rect.top(), preview_rect.width(), title_height)
        painter.setPen(Qt.PenStyle.NoPen)
        title_color = _color(theme.panel)
        title_color.setAlphaF(max(0.55, min(1.0, theme.alpha)))
        painter.setBrush(title_color)
        painter.drawRoundedRect(title_rect, theme.rounding, theme.rounding)
        painter.fillRect(title_rect.adjusted(0, title_height * 0.55, 0, 0), title_color)

        title_font = QFont(self.font())
        title_font.setBold(True)
        title_font.setPointSizeF(max(8.5, 10.5 * theme.font_scale * scale))
        painter.setFont(title_font)
        painter.setPen(_color(theme.text))
        painter.drawText(title_rect.adjusted(14 * scale, 0, -14 * scale, 0), Qt.AlignmentFlag.AlignVCenter, self.project.menu_title)

        body_rect = preview_rect.adjusted(0, title_height, 0, 0)
        nav_rect, content_rect = self._split_nav_and_content(body_rect, scale)
        self._last_content_rect = content_rect

        self._draw_navigation(painter, nav_rect, scale)
        self._draw_content_panel(painter, content_rect, scale)
        if self.show_grid and self.project.layout_mode == "free":
            self._draw_grid(painter, content_rect, scale)
        self._draw_components(painter, content_rect, scale)

    def _draw_menu_background(self, painter: QPainter, rect: QRectF, scale: float) -> None:
        assert self.project is not None
        bg = self.project.background
        theme = self.project.theme
        bg_type = bg.type
        phase = self._animation_time * bg.animation_speed
        primary = _color(bg.primary_color or theme.primary_background, theme.primary_background)
        secondary = _color(bg.secondary_color or theme.secondary_background, theme.secondary_background)
        accent = _color(bg.accent_color or theme.accent, theme.accent)
        primary.setAlphaF(max(0.05, min(1.0, bg.opacity)))
        secondary.setAlphaF(max(0.05, min(1.0, bg.opacity)))

        if bg_type in {"Linear Gradient Preview", "Animated Gradient", "Glassmorphism Blur Preview"}:
            angle_shift = math.sin(phase) * rect.width() * 0.25 if bg_type == "Animated Gradient" else 0
            gradient = QLinearGradient(rect.left() + angle_shift, rect.top(), rect.right() - angle_shift, rect.bottom())
            gradient.setColorAt(0.0, primary)
            gradient.setColorAt(0.55, secondary)
            glow = QColor(accent)
            glow.setAlphaF(max(0.08, min(0.55, bg.glow_intensity)))
            gradient.setColorAt(1.0, glow)
            painter.fillRect(rect, gradient)
        else:
            painter.fillRect(rect, primary)

        if bg_type in {"Cyber Grid", "Noise Texture Simulation"}:
            step = max(8.0, bg.grid_size * scale)
            alpha = 95 if bg_type == "Cyber Grid" else 34
            painter.setPen(QPen(_with_alpha(accent, alpha), 1))
            offset = (phase * 14 * scale) % step if bg_type == "Cyber Grid" else 0
            x = rect.left() - step + offset
            while x < rect.right() + step:
                painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
                x += step
            y = rect.top() - step + offset
            while y < rect.bottom() + step:
                painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
                y += step
            if bg_type == "Noise Texture Simulation":
                painter.setPen(QPen(_with_alpha(secondary, 35), 1))
                for i in range(90):
                    px = rect.left() + ((i * 37) % max(1, int(rect.width())))
                    py = rect.top() + ((i * 61 + int(phase * 12)) % max(1, int(rect.height())))
                    painter.drawPoint(int(px), int(py))

        if bg_type in {"Floating Particles", "Starfield"}:
            count = max(4, min(180, bg.particle_count))
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(count):
                x = rect.left() + ((i * 53 + phase * (12 + i % 7)) % max(1.0, rect.width()))
                y = rect.top() + ((i * 97 + phase * (8 + i % 5)) % max(1.0, rect.height()))
                radius = (1.2 + (i % 4) * 0.45) * scale
                color = QColor(accent if i % 3 else secondary)
                color.setAlpha(150 if bg_type == "Floating Particles" else 190)
                painter.setBrush(color)
                painter.drawEllipse(QPointF(x, y), radius, radius)

        if bg_type == "Glow Orbs":
            for i, anchor in enumerate([0.18, 0.78, 0.48]):
                cx = rect.left() + rect.width() * anchor + math.sin(phase + i) * 28 * scale
                cy = rect.top() + rect.height() * ([0.28, 0.68, 0.45][i]) + math.cos(phase * 0.8 + i) * 22 * scale
                radial = QRadialGradient(QPointF(cx, cy), 90 * scale)
                glow = QColor(accent if i != 1 else secondary)
                glow.setAlphaF(max(0.06, min(0.35, bg.glow_intensity)))
                radial.setColorAt(0.0, glow)
                clear = QColor(glow)
                clear.setAlpha(0)
                radial.setColorAt(1.0, clear)
                painter.fillRect(rect, radial)

        if bg_type == "Scanlines":
            painter.setPen(QPen(_with_alpha(accent, 55), 1))
            offset = int((phase * 38 * scale) % max(4.0, 8 * scale))
            y = rect.top() + offset
            while y < rect.bottom():
                painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
                y += max(4.0, 8 * scale)
            sweep_y = rect.top() + ((phase * 48 * scale) % max(1.0, rect.height()))
            painter.setPen(QPen(_with_alpha(accent, 125), 2))
            painter.drawLine(int(rect.left()), int(sweep_y), int(rect.right()), int(sweep_y))

    def _preview_rect(self) -> tuple[QRectF, float]:
        assert self.project is not None
        available = self.rect().adjusted(26, 22, -26, -22)
        scale = min(
            available.width() / max(1, self.project.window_width),
            available.height() / max(1, self.project.window_height),
        )
        scale = max(0.42, min(1.18, scale))
        width = self.project.window_width * scale
        height = self.project.window_height * scale
        left = available.left() + (available.width() - width) / 2
        top = available.top() + (available.height() - height) / 2
        return QRectF(left, top, width, height), scale

    def _split_nav_and_content(self, body_rect: QRectF, scale: float) -> tuple[QRectF, QRectF]:
        assert self.project is not None
        gap = 0.0
        icon_sidebar = self.project.nav_style == "icon sidebar"
        nav_width = (68 if icon_sidebar else 158) * scale
        nav_height = 48 * scale

        if self.project.nav_position == "right":
            nav_rect = QRectF(body_rect.right() - nav_width, body_rect.top(), nav_width, body_rect.height())
            content_rect = QRectF(body_rect.left(), body_rect.top(), body_rect.width() - nav_width - gap, body_rect.height())
        elif self.project.nav_position == "top":
            nav_rect = QRectF(body_rect.left(), body_rect.top(), body_rect.width(), nav_height)
            content_rect = QRectF(body_rect.left(), body_rect.top() + nav_height + gap, body_rect.width(), body_rect.height() - nav_height - gap)
        elif self.project.nav_position == "bottom":
            nav_rect = QRectF(body_rect.left(), body_rect.bottom() - nav_height, body_rect.width(), nav_height)
            content_rect = QRectF(body_rect.left(), body_rect.top(), body_rect.width(), body_rect.height() - nav_height - gap)
        else:
            nav_rect = QRectF(body_rect.left(), body_rect.top(), nav_width, body_rect.height())
            content_rect = QRectF(body_rect.left() + nav_width + gap, body_rect.top(), body_rect.width() - nav_width - gap, body_rect.height())
        return nav_rect, content_rect

    def _draw_navigation(self, painter: QPainter, nav_rect: QRectF, scale: float) -> None:
        assert self.project is not None
        theme = self.project.theme
        painter.setPen(QPen(_color(theme.border), max(1, theme.border_thickness)))
        painter.setBrush(_color(theme.sidebar))
        painter.drawRect(nav_rect)

        compact = self.project.nav_style == "icon sidebar"
        horizontal = self.project.nav_position in {"top", "bottom"}
        padding = max(8.0, theme.padding * scale)
        item_gap = max(5.0, theme.item_spacing * scale * 0.7)
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSizeF(max(7.5, 9.5 * theme.font_scale * scale))
        painter.setFont(font)

        if horizontal:
            x = nav_rect.left() + padding
            y = nav_rect.top() + (nav_rect.height() - 30 * scale) / 2
            for category in self.project.categories:
                text = category.icon if compact and category.icon else f"{category.icon} {category.name}".strip()
                width = max(68.0 * scale, min(170.0 * scale, painter.fontMetrics().horizontalAdvance(text) + 26 * scale))
                rect = QRectF(x, y, width, 30 * scale)
                self.category_rects[category.id] = rect
                self._draw_nav_item(painter, rect, text, category.id == self.project.active_category_id, compact, scale)
                x += width + item_gap
        else:
            y = nav_rect.top() + padding
            for category in self.project.categories:
                text = category.icon if compact and category.icon else f"{category.icon} {category.name}".strip()
                rect = QRectF(nav_rect.left() + padding * 0.65, y, nav_rect.width() - padding * 1.3, 32 * scale)
                self.category_rects[category.id] = rect
                self._draw_nav_item(painter, rect, text, category.id == self.project.active_category_id, compact, scale)
                y += rect.height() + item_gap

    def _draw_nav_item(self, painter: QPainter, rect: QRectF, text: str, active: bool, compact: bool, scale: float) -> None:
        assert self.project is not None
        theme = self.project.theme
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_color(theme.nav_active if active else theme.nav_hover if active else theme.sidebar))
        if active:
            painter.drawRoundedRect(rect, max(4.0, theme.rounding * scale), max(4.0, theme.rounding * scale))
        painter.setPen(_color(theme.text if active else theme.muted_text))
        flags = Qt.AlignmentFlag.AlignCenter if compact else Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        inset = 0 if compact else 10 * scale
        painter.drawText(rect.adjusted(inset, 0, -inset, 0), flags, text)

    def _draw_content_panel(self, painter: QPainter, content_rect: QRectF, scale: float) -> None:
        assert self.project is not None
        theme = self.project.theme
        painter.setPen(QPen(_color(theme.border), max(1, theme.border_thickness)))
        fill = _color(theme.panel)
        if self.project.background.type != "Solid Color":
            fill.setAlphaF(max(0.62, min(0.96, theme.alpha)))
        painter.setBrush(fill)
        painter.drawRect(content_rect)

    def _draw_grid(self, painter: QPainter, content_rect: QRectF, scale: float) -> None:
        assert self.project is not None
        step = max(6.0, self.project.grid_size * scale)
        pen = QPen(_with_alpha(_color(self.project.theme.border), 70), 1)
        painter.setPen(pen)
        x = content_rect.left()
        while x < content_rect.right():
            painter.drawLine(int(x), int(content_rect.top()), int(x), int(content_rect.bottom()))
            x += step
        y = content_rect.top()
        while y < content_rect.bottom():
            painter.drawLine(int(content_rect.left()), int(y), int(content_rect.right()), int(y))
            y += step

    def _draw_components(self, painter: QPainter, content_rect: QRectF, scale: float) -> None:
        assert self.project is not None
        category = self.project.active_category()
        theme = self.project.theme
        padding = max(10.0, theme.padding * scale)
        spacing = max(6.0, theme.item_spacing * scale)
        y = content_rect.top() + padding

        for component in category.components:
            if not component.visible:
                continue
            if self.project.layout_mode == "free":
                rect = QRectF(
                    content_rect.left() + component.x * scale,
                    content_rect.top() + component.y * scale,
                    max(28.0, component.width * scale),
                    max(14.0, component.height * scale),
                )
            else:
                width = min(max(40.0, component.width * scale), max(40.0, content_rect.width() - padding * 2))
                height = max(14.0, component.height * scale)
                x = content_rect.left() + padding
                if component.auto_center:
                    x = content_rect.left() + (content_rect.width() - width) / 2
                rect = QRectF(x, y, width, height)
                y += height + spacing
            self.component_rects[component.id] = rect
            self._draw_component(painter, component, rect, scale)

    def _draw_component(self, painter: QPainter, component: Component, rect: QRectF, scale: float) -> None:
        assert self.project is not None
        theme = self.project.theme
        rect, animation_opacity, animation_glow = self._apply_component_animation(component, rect, scale)
        accent = _color(component.color or theme.accent, theme.accent)
        panel = _color(theme.card or theme.panel, theme.panel)
        hover = _color(theme.hover)
        border = _color(theme.border)
        text = _color(component.text_color or theme.text, theme.text)
        muted = _color(theme.muted_text)
        rounding = max(3.0, theme.rounding * scale)
        selected = component.id == self.selected_component_id

        font = QFont(self.font())
        font.setPointSizeF(max(7.0, 9.4 * theme.font_scale * scale))
        font.setBold(component.type == "header_text")
        painter.setFont(font)

        if animation_glow > 0:
            glow = QColor(accent)
            glow.setAlphaF(max(0.05, min(0.45, animation_glow)))
            painter.setPen(QPen(glow, max(2, int(4 * scale))))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-5, -5, 5, 5), rounding + 5, rounding + 5)

        if selected:
            painter.setPen(QPen(accent, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-3, -3, 3, 3), rounding + 3, rounding + 3)

        disabled_alpha = 115 if not component.enabled else 255
        disabled_alpha = int(disabled_alpha * animation_opacity)
        painter.setOpacity(disabled_alpha / 255.0)

        if component.type == "button":
            self._rounded_box(painter, rect, accent, accent.darker(120), rounding)
            painter.setPen(QColor("#ffffff"))
            painter.drawText(rect.adjusted(8 * scale, 0, -8 * scale, 0), Qt.AlignmentFlag.AlignCenter, component.label)
        elif component.type == "checkbox":
            box = QRectF(rect.left(), rect.center().y() - 8 * scale, 16 * scale, 16 * scale)
            self._rounded_box(painter, box, hover, border, 3)
            if component.props.get("default_value"):
                painter.setPen(QPen(accent, 2))
                painter.drawLine(box.left() + 4 * scale, box.center().y(), box.center().x(), box.bottom() - 4 * scale)
                painter.drawLine(box.center().x(), box.bottom() - 4 * scale, box.right() - 3 * scale, box.top() + 4 * scale)
            painter.setPen(text)
            painter.drawText(rect.adjusted(24 * scale, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, component.label)
        elif component.type in {"slider_float", "slider_int"}:
            painter.setPen(text)
            painter.drawText(QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.45), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, component.label)
            track = QRectF(rect.left(), rect.bottom() - 13 * scale, rect.width(), 7 * scale)
            self._rounded_box(painter, track, hover, border, 3)
            minimum = float(component.props.get("min", 0))
            maximum = float(component.props.get("max", 1))
            value = float(component.props.get("default_value", minimum))
            ratio = 0.0 if maximum == minimum else max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))
            fill = QRectF(track.left(), track.top(), track.width() * ratio, track.height())
            self._rounded_box(painter, fill, accent, accent, 3)
        elif component.type == "combo_box":
            self._rounded_box(painter, rect, hover, border, rounding)
            options = component.props.get("options", ["Option A"])
            if isinstance(options, str):
                options = [item.strip() for item in options.split(",") if item.strip()]
            index = int(component.props.get("default_index", 0) or 0)
            value = options[index] if isinstance(options, list) and options and 0 <= index < len(options) else "Select"
            painter.setPen(text)
            painter.drawText(rect.adjusted(10 * scale, 0, -24 * scale, 0), Qt.AlignmentFlag.AlignVCenter, f"{component.label}: {value}")
            painter.setPen(muted)
            painter.drawText(rect.adjusted(0, 0, -9 * scale, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "v")
        elif component.type == "text_label":
            painter.setPen(text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, component.label)
        elif component.type == "header_text":
            painter.setPen(text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, component.label)
        elif component.type == "separator":
            painter.setPen(QPen(border, 1))
            painter.drawLine(rect.left(), rect.center().y(), rect.right(), rect.center().y())
        elif component.type == "input_text":
            self._rounded_box(painter, rect, hover, border, rounding)
            painter.setPen(muted)
            painter.drawText(rect.adjusted(10 * scale, 0, -10 * scale, 0), Qt.AlignmentFlag.AlignVCenter, component.props.get("default_text") or component.label)
        elif component.type == "color_picker":
            self._rounded_box(painter, rect, hover, border, rounding)
            swatch = QRectF(rect.right() - 34 * scale, rect.top() + 6 * scale, 22 * scale, rect.height() - 12 * scale)
            self._rounded_box(painter, swatch, accent, border, 4)
            painter.setPen(text)
            painter.drawText(rect.adjusted(10 * scale, 0, -40 * scale, 0), Qt.AlignmentFlag.AlignVCenter, component.label)
        elif component.type == "keybind":
            painter.setPen(text)
            painter.drawText(rect.adjusted(0, 0, -88 * scale, 0), Qt.AlignmentFlag.AlignVCenter, component.label)
            key_rect = QRectF(rect.right() - 82 * scale, rect.top() + 2 * scale, 82 * scale, rect.height() - 4 * scale)
            self._rounded_box(painter, key_rect, hover, border, rounding)
            painter.setPen(text)
            painter.drawText(key_rect, Qt.AlignmentFlag.AlignCenter, str(component.props.get("default_key", "None")))
        elif component.type == "icon_button":
            self._rounded_box(painter, rect, hover, border, rounding)
            painter.setPen(text)
            painter.drawText(rect.adjusted(8 * scale, 0, -8 * scale, 0), Qt.AlignmentFlag.AlignCenter, f"{component.props.get('icon', '[*]')} {component.label}")
        elif component.type == "social_link":
            self._rounded_box(painter, rect, hover, accent, rounding)
            painter.setPen(text)
            platform = component.props.get("platform", component.label)
            painter.drawText(rect.adjusted(8 * scale, 0, -8 * scale, 0), Qt.AlignmentFlag.AlignCenter, f"{component.props.get('icon', '')} {platform}".strip())
        elif component.type == "feature_card":
            self._rounded_box(painter, rect, panel.lighter(112), border, rounding)
            painter.setPen(text)
            title_font = QFont(font)
            title_font.setBold(True)
            painter.setFont(title_font)
            painter.drawText(rect.adjusted(12 * scale, 8 * scale, -12 * scale, -rect.height() * 0.55), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(component.props.get("title", component.label)))
            painter.setFont(font)
            painter.setPen(muted)
            painter.drawText(rect.adjusted(12 * scale, 30 * scale, -12 * scale, -26 * scale), Qt.TextFlag.TextWordWrap, str(component.props.get("description", "")))
            button_rect = QRectF(rect.right() - 86 * scale, rect.bottom() - 28 * scale, 74 * scale, 20 * scale)
            self._rounded_box(painter, button_rect, accent if not component.props.get("locked") else hover, border, 4)
            painter.setPen(QColor("#ffffff") if not component.props.get("locked") else muted)
            painter.drawText(button_rect, Qt.AlignmentFlag.AlignCenter, str(component.props.get("button_text", "Open")))
        elif component.type == "status_badge":
            badge_color = _color(str(component.props.get("badge_color", "#2ecc71")), "#2ecc71")
            self._rounded_box(painter, rect, _with_alpha(badge_color, 80), badge_color, rect.height() / 2)
            painter.setPen(text)
            painter.drawText(rect.adjusted(10 * scale, 0, -10 * scale, 0), Qt.AlignmentFlag.AlignCenter, str(component.props.get("status", component.label)))
        elif component.type == "progress_bar":
            self._rounded_box(painter, rect, hover, border, rounding)
            value = float(component.props.get("value", component.props.get("default_value", 0.65)) or 0.0)
            minimum = float(component.props.get("min", 0.0) or 0.0)
            maximum = float(component.props.get("max", 1.0) or 1.0)
            ratio = 0.0 if maximum == minimum else max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))
            fill_rect = QRectF(rect.left(), rect.top(), rect.width() * ratio, rect.height())
            self._rounded_box(painter, fill_rect, accent, accent, rounding)
            painter.setPen(text)
            overlay = str(component.props.get("overlay", f"{int(ratio * 100)}%"))
            painter.drawText(rect.adjusted(8 * scale, 0, -8 * scale, 0), Qt.AlignmentFlag.AlignCenter, overlay)
        elif component.type == "image_placeholder":
            self._rounded_box(painter, rect, hover, border, rounding)
            painter.setPen(muted)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(component.props.get("placeholder", "[image]")))
        elif component.type == "tab_button":
            self._rounded_box(painter, rect, accent if component.props.get("active") else hover, border, rounding)
            painter.setPen(text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, component.label)
        elif component.type == "nav_category":
            painter.setPen(text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{component.props.get('icon', '[>]')} {component.label}")
        elif component.type == "footer_text":
            painter.setPen(muted)
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, component.label)
        else:
            painter.setPen(text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, component.label)

        painter.setOpacity(1.0)

    def _effective_animation(self, component: Component) -> Animation:
        assert self.project is not None
        if component.animation.enabled and component.animation.type != "None":
            return component.animation
        if component.group_id:
            group = self.project.find_group(component.group_id)
            if group and group.animation.enabled and group.animation.type != "None":
                return group.animation
        if self.project.animation.enabled and self.project.animation.type != "None":
            return self.project.animation
        return Animation()

    def _apply_component_animation(self, component: Component, rect: QRectF, scale: float) -> tuple[QRectF, float, float]:
        animation = self._effective_animation(component)
        if not animation.enabled or animation.type == "None":
            return rect, 1.0, 0.0
        t = max(0.0, self._animation_time - animation.delay)
        progress = 1.0 if animation.duration <= 0 else min(1.0, t / animation.duration)
        if animation.easing == "ease in":
            eased = progress * progress
        elif animation.easing == "ease out":
            eased = 1 - (1 - progress) * (1 - progress)
        elif animation.easing == "linear":
            eased = progress
        else:
            eased = 0.5 - math.cos(progress * math.pi) * 0.5
        phase = t * max(0.01, animation.speed)
        intensity = max(0.0, animation.intensity)
        anim_type = animation.type
        out = QRectF(rect)
        opacity = 1.0
        glow = 0.0

        if anim_type == "Fade In":
            opacity = eased
        elif anim_type == "Slide In Left":
            out.translate(-(1 - eased) * 42 * scale * intensity, 0)
            opacity = max(0.25, eased)
        elif anim_type == "Slide In Right":
            out.translate((1 - eased) * 42 * scale * intensity, 0)
            opacity = max(0.25, eased)
        elif anim_type == "Slide In Up":
            out.translate(0, (1 - eased) * 34 * scale * intensity)
            opacity = max(0.25, eased)
        elif anim_type == "Slide In Down":
            out.translate(0, -(1 - eased) * 34 * scale * intensity)
            opacity = max(0.25, eased)
        elif anim_type in {"Pulse Glow", "Border Glow"}:
            glow = (0.25 + 0.25 * math.sin(phase * math.pi * 2)) * intensity
        elif anim_type == "Hover Glow" and self._hover_component_id == component.id:
            glow = 0.35 * intensity
        elif anim_type == "Hover Scale" and self._hover_component_id == component.id:
            grow = 0.025 * intensity
            out.adjust(-out.width() * grow, -out.height() * grow, out.width() * grow, out.height() * grow)
        elif anim_type == "Floating":
            out.translate(0, math.sin(phase * math.pi * 2) * 5 * scale * intensity)
        elif anim_type == "Shake Error":
            out.translate(math.sin(phase * math.pi * 8) * 5 * scale * intensity, 0)
        elif anim_type == "Loading Dots":
            glow = (0.18 + 0.12 * ((int(phase * 4) % 3) + 1)) * intensity
        elif anim_type in {"Animated Gradient", "Particle Drift", "Scanline Sweep"}:
            glow = (0.12 + 0.16 * math.sin(phase * math.pi * 2)) * intensity
        return out, opacity, glow

    def _rounded_box(self, painter: QPainter, rect: QRectF, fill: QColor, border: QColor, rounding: float) -> None:
        painter.setPen(QPen(border, 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, rounding, rounding)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if not self.project:
            return
        pos = event.position()
        for component_id, rect in reversed(list(self.component_rects.items())):
            if rect.contains(pos):
                self.component_selected.emit(component_id)
                _, component = self.project.find_component(component_id)
                if component and self.project.layout_mode == "free":
                    self._dragging_component = component
                    self._drag_offset = QPointF(pos.x() - rect.left(), pos.y() - rect.top())
                    self._drag_checkpoint_taken = False
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                return
        for category_id, rect in self.category_rects.items():
            if rect.contains(pos):
                self.category_selected.emit(category_id)
                return
        self.component_selected.emit("")

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self.project:
            return
        pos = event.position()
        if self._dragging_component and self.project.layout_mode == "free":
            if not self._drag_checkpoint_taken:
                self.before_mutation.emit()
                self._drag_checkpoint_taken = True
            scale = self._last_scale or 1.0
            x = (pos.x() - self._drag_offset.x() - self._last_content_rect.left()) / scale
            y = (pos.y() - self._drag_offset.y() - self._last_content_rect.top()) / scale
            x = max(0, min(x, self._last_content_rect.width() / scale - self._dragging_component.width))
            y = max(0, min(y, self._last_content_rect.height() / scale - self._dragging_component.height))
            if self.project.snap_to_grid:
                grid = max(1, self.project.grid_size)
                x = round(x / grid) * grid
                y = round(y / grid) * grid
            self._dragging_component.x = int(x)
            self._dragging_component.y = int(y)
            self.project_changed.emit()
            self.update()
            return

        hover_component = any(rect.contains(pos) for rect in self.component_rects.values())
        self._hover_component_id = ""
        for component_id, rect in self.component_rects.items():
            if rect.contains(pos):
                self._hover_component_id = component_id
                break
        hover_category = any(rect.contains(pos) for rect in self.category_rects.values())
        self.setCursor(Qt.CursorShape.PointingHandCursor if hover_component or hover_category else Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._dragging_component = None
        self._drag_checkpoint_taken = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
