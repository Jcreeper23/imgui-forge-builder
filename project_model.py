"""Serializable data model used by the builder, preview, and exporter."""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
import uuid
from typing import Any

try:
    from .settings import DEFAULT_MENU_HEIGHT, DEFAULT_MENU_WIDTH
except ImportError:  # pragma: no cover - keeps direct module execution friendly.
    from settings import DEFAULT_MENU_HEIGHT, DEFAULT_MENU_WIDTH


def make_id(prefix: str) -> str:
    """Create compact, stable-enough ids for project objects."""

    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class Animation:
    """Reusable animation settings for components, groups, menus, and backgrounds."""

    enabled: bool = False
    type: str = "None"
    duration: float = 0.45
    delay: float = 0.0
    speed: float = 1.0
    intensity: float = 1.0
    loop: bool = True
    easing: str = "ease in out"

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "type": self.type,
            "duration": self.duration,
            "delay": self.delay,
            "speed": self.speed,
            "intensity": self.intensity,
            "loop": self.loop,
            "easing": self.easing,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Animation":
        base = cls()
        if not isinstance(data, dict):
            return base
        base.enabled = _as_bool(data.get("enabled"), False)
        base.type = str(data.get("type", "None"))
        base.duration = _as_float(data.get("duration"), 0.45)
        base.delay = _as_float(data.get("delay"), 0.0)
        base.speed = _as_float(data.get("speed"), 1.0)
        base.intensity = _as_float(data.get("intensity"), 1.0)
        base.loop = _as_bool(data.get("loop"), True)
        base.easing = str(data.get("easing", "ease in out"))
        return base


@dataclass
class Background:
    """Preview/export configuration for animated or styled menu backgrounds."""

    type: str = "Solid Color"
    primary_color: str = "#151922"
    secondary_color: str = "#1f2633"
    accent_color: str = "#4f8cff"
    animation_speed: float = 1.0
    particle_count: int = 36
    grid_size: int = 28
    glow_intensity: float = 0.55
    opacity: float = 1.0
    softness: int = 18

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "accent_color": self.accent_color,
            "animation_speed": self.animation_speed,
            "particle_count": self.particle_count,
            "grid_size": self.grid_size,
            "glow_intensity": self.glow_intensity,
            "opacity": self.opacity,
            "softness": self.softness,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Background":
        base = cls()
        if not isinstance(data, dict):
            return base
        for key in base.to_dict():
            if key in data:
                setattr(base, key, data[key])
        base.animation_speed = _as_float(base.animation_speed, 1.0)
        base.particle_count = _as_int(base.particle_count, 36)
        base.grid_size = _as_int(base.grid_size, 28)
        base.glow_intensity = _as_float(base.glow_intensity, 0.55)
        base.opacity = _as_float(base.opacity, 1.0)
        base.softness = _as_int(base.softness, 18)
        return base


@dataclass
class Theme:
    """Visual style shared by the preview and generated ImGui code."""

    background: str = "#151922"
    primary_background: str = "#151922"
    secondary_background: str = "#1a2030"
    panel: str = "#1e2430"
    card: str = "#242c3a"
    sidebar: str = "#111620"
    accent: str = "#4f8cff"
    accent2: str = "#7dd3fc"
    hover: str = "#2f3b52"
    active: str = "#365d9f"
    nav_active: str = "#365d9f"
    nav_hover: str = "#2f3b52"
    danger: str = "#ef4444"
    success: str = "#28c487"
    warning: str = "#f59e0b"
    border: str = "#30384a"
    shadow_color: str = "#000000"
    text: str = "#f2f5fa"
    muted_text: str = "#96a0b5"
    rounding: int = 8
    padding: int = 14
    item_spacing: int = 10
    frame_padding: int = 8
    window_padding: int = 14
    font_scale: float = 1.0
    border_thickness: int = 1
    button_height: int = 34
    card_padding: int = 14
    glow_intensity: float = 0.55
    alpha: float = 1.0
    shadow: str = "soft"

    def to_dict(self) -> dict[str, Any]:
        return {
            "background": self.background,
            "primary_background": self.primary_background,
            "secondary_background": self.secondary_background,
            "panel": self.panel,
            "card": self.card,
            "sidebar": self.sidebar,
            "accent": self.accent,
            "accent2": self.accent2,
            "hover": self.hover,
            "active": self.active,
            "nav_active": self.nav_active,
            "nav_hover": self.nav_hover,
            "danger": self.danger,
            "success": self.success,
            "warning": self.warning,
            "border": self.border,
            "shadow_color": self.shadow_color,
            "text": self.text,
            "muted_text": self.muted_text,
            "rounding": self.rounding,
            "padding": self.padding,
            "item_spacing": self.item_spacing,
            "frame_padding": self.frame_padding,
            "window_padding": self.window_padding,
            "font_scale": self.font_scale,
            "border_thickness": self.border_thickness,
            "button_height": self.button_height,
            "card_padding": self.card_padding,
            "glow_intensity": self.glow_intensity,
            "alpha": self.alpha,
            "shadow": self.shadow,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Theme":
        base = cls()
        if not isinstance(data, dict):
            return base
        for key in base.to_dict():
            if key in data:
                setattr(base, key, data[key])
        base.rounding = _as_int(base.rounding, 8)
        base.padding = _as_int(base.padding, 14)
        base.item_spacing = _as_int(base.item_spacing, 10)
        base.frame_padding = _as_int(base.frame_padding, 8)
        base.window_padding = _as_int(base.window_padding, base.padding)
        base.border_thickness = _as_int(base.border_thickness, 1)
        base.button_height = _as_int(base.button_height, 34)
        base.card_padding = _as_int(base.card_padding, 14)
        base.glow_intensity = _as_float(base.glow_intensity, 0.55)
        base.alpha = _as_float(base.alpha, 1.0)
        try:
            base.font_scale = float(base.font_scale)
        except (TypeError, ValueError):
            base.font_scale = 1.0
        if not base.primary_background:
            base.primary_background = base.background
        if not base.secondary_background:
            base.secondary_background = base.panel
        if not base.card:
            base.card = base.panel
        if not base.nav_active:
            base.nav_active = base.active
        if not base.nav_hover:
            base.nav_hover = base.hover
        return base


@dataclass
class Component:
    """One visual ImGui-like widget in a category."""

    type: str
    label: str
    id: str = field(default_factory=lambda: make_id("cmp"))
    variable_name: str = ""
    category_id: str = ""
    x: int = 24
    y: int = 24
    width: int = 240
    height: int = 32
    auto_center: bool = False
    visible: bool = True
    enabled: bool = True
    color: str = ""
    text_color: str = ""
    tooltip: str = ""
    group_id: str = ""
    animation: Animation = field(default_factory=Animation)
    props: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "variable_name": self.variable_name,
            "category_id": self.category_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "auto_center": self.auto_center,
            "visible": self.visible,
            "enabled": self.enabled,
            "color": self.color,
            "text_color": self.text_color,
            "tooltip": self.tooltip,
            "group_id": self.group_id,
            "animation": self.animation.to_dict(),
            "props": copy.deepcopy(self.props),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Component":
        component = cls(
            type=str(data.get("type", "text_label")),
            label=str(data.get("label", "Component")),
            id=str(data.get("id") or make_id("cmp")),
        )
        component.variable_name = str(data.get("variable_name", ""))
        component.category_id = str(data.get("category_id", ""))
        component.x = _as_int(data.get("x"), 24)
        component.y = _as_int(data.get("y"), 24)
        component.width = _as_int(data.get("width"), 240)
        component.height = _as_int(data.get("height"), 32)
        component.auto_center = _as_bool(data.get("auto_center"), False)
        component.visible = _as_bool(data.get("visible"), True)
        component.enabled = _as_bool(data.get("enabled"), True)
        component.color = str(data.get("color", ""))
        component.text_color = str(data.get("text_color", ""))
        component.tooltip = str(data.get("tooltip", ""))
        component.group_id = str(data.get("group_id", ""))
        component.animation = Animation.from_dict(data.get("animation", {}))
        props = data.get("props", {})
        component.props = copy.deepcopy(props) if isinstance(props, dict) else {}
        return component


@dataclass
class Group:
    """A lightweight preset/group wrapper around real editable components."""

    name: str
    category_id: str
    id: str = field(default_factory=lambda: make_id("grp"))
    component_ids: list[str] = field(default_factory=list)
    preset_name: str = ""
    animation: Animation = field(default_factory=Animation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category_id": self.category_id,
            "component_ids": list(self.component_ids),
            "preset_name": self.preset_name,
            "animation": self.animation.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Group":
        group = cls(
            id=str(data.get("id") or make_id("grp")),
            name=str(data.get("name", "Preset Group")),
            category_id=str(data.get("category_id", "")),
        )
        raw_ids = data.get("component_ids", [])
        group.component_ids = [str(item) for item in raw_ids] if isinstance(raw_ids, list) else []
        group.preset_name = str(data.get("preset_name", ""))
        group.animation = Animation.from_dict(data.get("animation", {}))
        return group


@dataclass
class Category:
    """A navigation target that owns a list of components."""

    name: str
    icon: str = ""
    id: str = field(default_factory=lambda: make_id("cat"))
    components: list[Component] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "components": [component.to_dict() for component in self.components],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Category":
        category = cls(
            id=str(data.get("id") or make_id("cat")),
            name=str(data.get("name", "Category")),
            icon=str(data.get("icon", "")),
        )
        raw_components = data.get("components", [])
        if isinstance(raw_components, list):
            category.components = [Component.from_dict(item) for item in raw_components if isinstance(item, dict)]
            for component in category.components:
                component.category_id = category.id
        return category


@dataclass
class ProjectModel:
    """Top-level project state. Keep this class UI-agnostic."""

    project_name: str = "Untitled Menu"
    menu_title: str = "ImGui Forge Menu"
    window_width: int = DEFAULT_MENU_WIDTH
    window_height: int = DEFAULT_MENU_HEIGHT
    nav_position: str = "left"
    nav_style: str = "vertical sidebar"
    layout_mode: str = "auto"
    snap_to_grid: bool = True
    grid_size: int = 12
    selected_theme: str = "Dark Blue"
    theme: Theme = field(default_factory=Theme)
    background: Background = field(default_factory=Background)
    animation: Animation = field(default_factory=Animation)
    categories: list[Category] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    active_category_id: str = ""

    @classmethod
    def create_default(cls) -> "ProjectModel":
        home = Category(name="Home", icon="[H]")
        model = cls(categories=[home], active_category_id=home.id)
        return model

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "menu_title": self.menu_title,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "nav_position": self.nav_position,
            "nav_style": self.nav_style,
            "layout_mode": self.layout_mode,
            "snap_to_grid": self.snap_to_grid,
            "grid_size": self.grid_size,
            "selected_theme": self.selected_theme,
            "theme": self.theme.to_dict(),
            "background": self.background.to_dict(),
            "animation": self.animation.to_dict(),
            "active_category_id": self.active_category_id,
            "categories": [category.to_dict() for category in self.categories],
            "groups": [group.to_dict() for group in self.groups],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectModel":
        if not isinstance(data, dict):
            return cls.create_default()
        categories = [Category.from_dict(item) for item in data.get("categories", []) if isinstance(item, dict)]
        if not categories:
            categories = [Category(name="Home", icon="[H]")]
        groups = [Group.from_dict(item) for item in data.get("groups", []) if isinstance(item, dict)]
        model = cls(
            project_name=str(data.get("project_name", "Untitled Menu")),
            menu_title=str(data.get("menu_title", "ImGui Forge Menu")),
            window_width=_as_int(data.get("window_width"), DEFAULT_MENU_WIDTH),
            window_height=_as_int(data.get("window_height"), DEFAULT_MENU_HEIGHT),
            nav_position=str(data.get("nav_position", "left")),
            nav_style=str(data.get("nav_style", "vertical sidebar")),
            layout_mode=str(data.get("layout_mode", "auto")),
            snap_to_grid=_as_bool(data.get("snap_to_grid"), True),
            grid_size=_as_int(data.get("grid_size"), 12),
            selected_theme=str(data.get("selected_theme", "Dark Blue")),
            theme=Theme.from_dict(data.get("theme", {})),
            background=Background.from_dict(data.get("background", {})),
            animation=Animation.from_dict(data.get("animation", {})),
            categories=categories,
            groups=groups,
            active_category_id=str(data.get("active_category_id", "")),
        )
        if not model.find_category(model.active_category_id):
            model.active_category_id = model.categories[0].id
        return model

    def clone(self) -> "ProjectModel":
        return ProjectModel.from_dict(self.to_dict())

    def find_category(self, category_id: str) -> Category | None:
        for category in self.categories:
            if category.id == category_id:
                return category
        return None

    def active_category(self) -> Category:
        category = self.find_category(self.active_category_id)
        if category:
            return category
        if not self.categories:
            category = Category(name="Home", icon="[H]")
            self.categories.append(category)
        self.active_category_id = self.categories[0].id
        return self.categories[0]

    def add_category(self, name: str = "New Category", icon: str = "[*]") -> Category:
        category = Category(name=name.strip() or "New Category", icon=icon.strip())
        self.categories.append(category)
        self.active_category_id = category.id
        return category

    def delete_category(self, category_id: str) -> bool:
        if len(self.categories) <= 1:
            return False
        index = next((i for i, category in enumerate(self.categories) if category.id == category_id), -1)
        if index < 0:
            return False
        del self.categories[index]
        if self.active_category_id == category_id:
            self.active_category_id = self.categories[max(0, index - 1)].id
        return True

    def move_category(self, category_id: str, delta: int) -> bool:
        index = next((i for i, category in enumerate(self.categories) if category.id == category_id), -1)
        target = index + delta
        if index < 0 or target < 0 or target >= len(self.categories):
            return False
        self.categories[index], self.categories[target] = self.categories[target], self.categories[index]
        return True

    def find_component(self, component_id: str) -> tuple[Category, Component] | tuple[None, None]:
        for category in self.categories:
            for component in category.components:
                if component.id == component_id:
                    return category, component
        return None, None

    def all_components(self) -> list[Component]:
        return [component for category in self.categories for component in category.components]

    def find_group(self, group_id: str) -> Group | None:
        for group in self.groups:
            if group.id == group_id:
                return group
        return None

    def groups_for_category(self, category_id: str) -> list[Group]:
        return [group for group in self.groups if group.category_id == category_id]

    def add_group(self, name: str, category_id: str, component_ids: list[str], preset_name: str = "") -> Group:
        group = Group(name=name.strip() or "Preset Group", category_id=category_id, component_ids=list(component_ids), preset_name=preset_name)
        self.groups.append(group)
        for component_id in component_ids:
            _, component = self.find_component(component_id)
            if component:
                component.group_id = group.id
        return group

    def delete_group(self, group_id: str, delete_components: bool = False) -> bool:
        group = self.find_group(group_id)
        if not group:
            return False
        if delete_components:
            for component_id in list(group.component_ids):
                self.delete_component(component_id)
        else:
            for component_id in group.component_ids:
                _, component = self.find_component(component_id)
                if component:
                    component.group_id = ""
        self.groups.remove(group)
        return True

    def components_in_group(self, group_id: str) -> list[Component]:
        group = self.find_group(group_id)
        if not group:
            return []
        components: list[Component] = []
        for component_id in group.component_ids:
            _, component = self.find_component(component_id)
            if component:
                components.append(component)
        return components

    def add_component(self, component: Component, category_id: str | None = None, index: int | None = None) -> Component:
        category = self.find_category(category_id or self.active_category_id) or self.active_category()
        component.category_id = category.id
        if index is None or index < 0 or index > len(category.components):
            category.components.append(component)
        else:
            category.components.insert(index, component)
        return component

    def delete_component(self, component_id: str) -> bool:
        category, component = self.find_component(component_id)
        if not category or not component:
            return False
        category.components.remove(component)
        for group in list(self.groups):
            if component_id in group.component_ids:
                group.component_ids = [item for item in group.component_ids if item != component_id]
                if not group.component_ids:
                    self.groups.remove(group)
        return True

    def duplicate_component(self, component_id: str) -> Component | None:
        category, component = self.find_component(component_id)
        if not category or not component:
            return None
        duplicate = Component.from_dict(component.to_dict())
        duplicate.id = make_id("cmp")
        duplicate.label = f"{duplicate.label} Copy"
        duplicate.variable_name = f"{duplicate.variable_name}_copy" if duplicate.variable_name else ""
        duplicate.x += 18
        duplicate.y += 18
        duplicate.group_id = ""
        index = category.components.index(component) + 1
        category.components.insert(index, duplicate)
        return duplicate

    def duplicate_group(self, group_id: str) -> Group | None:
        group = self.find_group(group_id)
        category = self.find_category(group.category_id) if group else None
        if not group or not category:
            return None
        new_ids: list[str] = []
        insert_after = 0
        for component_id in group.component_ids:
            _, component = self.find_component(component_id)
            if not component:
                continue
            duplicate = Component.from_dict(component.to_dict())
            duplicate.id = make_id("cmp")
            duplicate.label = f"{duplicate.label} Copy"
            duplicate.variable_name = f"{duplicate.variable_name}_copy" if duplicate.variable_name else ""
            duplicate.x += 18
            duplicate.y += 18
            duplicate.group_id = ""
            insert_after = max(insert_after, category.components.index(component) + 1)
            category.components.insert(insert_after, duplicate)
            insert_after += 1
            new_ids.append(duplicate.id)
        if not new_ids:
            return None
        new_group = self.add_group(f"{group.name} Copy", group.category_id, new_ids, group.preset_name)
        new_group.animation = Animation.from_dict(group.animation.to_dict())
        return new_group

    def move_component(self, component_id: str, delta: int) -> bool:
        category, component = self.find_component(component_id)
        if not category or not component:
            return False
        index = category.components.index(component)
        target = index + delta
        if target < 0 or target >= len(category.components):
            return False
        category.components[index], category.components[target] = category.components[target], category.components[index]
        return True

    def move_component_to_category(self, component_id: str, category_id: str) -> bool:
        old_category, component = self.find_component(component_id)
        new_category = self.find_category(category_id)
        if not old_category or not component or not new_category:
            return False
        if old_category.id == new_category.id:
            return True
        old_category.components.remove(component)
        component.category_id = new_category.id
        new_category.components.append(component)
        return True
