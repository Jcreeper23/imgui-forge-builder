"""Component registry and factory functions."""

from __future__ import annotations

from dataclasses import dataclass, field
import copy
import re
from typing import Any

try:
    from .project_model import Component
except ImportError:  # pragma: no cover
    from project_model import Component


@dataclass(frozen=True)
class ComponentDefinition:
    type: str
    title: str
    default_label: str
    default_width: int = 240
    default_height: int = 32
    variable_kind: str = ""
    default_props: dict[str, Any] = field(default_factory=dict)


def make_variable_name(label: str, fallback: str = "value") -> str:
    text = re.sub(r"[^a-zA-Z0-9_]+", "_", label.strip().lower()).strip("_")
    if not text:
        text = fallback
    if text[0].isdigit():
        text = f"v_{text}"
    return text


COMPONENT_DEFINITIONS: dict[str, ComponentDefinition] = {
    "button": ComponentDefinition(
        "button",
        "Button",
        "Run Action",
        180,
        34,
        default_props={"callback_name": "OnRunAction", "icon": "", "button_style": "accent"},
    ),
    "checkbox": ComponentDefinition(
        "checkbox",
        "Toggle / Checkbox",
        "Enable Option",
        240,
        30,
        "bool",
        {"default_value": False},
    ),
    "slider_float": ComponentDefinition(
        "slider_float",
        "Slider Float",
        "Float Value",
        280,
        38,
        "float",
        {"min": 0.0, "max": 1.0, "default_value": 0.5, "format": "%.2f"},
    ),
    "slider_int": ComponentDefinition(
        "slider_int",
        "Slider Int",
        "Integer Value",
        280,
        38,
        "int",
        {"min": 0, "max": 100, "default_value": 50, "format": "%d"},
    ),
    "combo_box": ComponentDefinition(
        "combo_box",
        "Combo Box",
        "Mode",
        260,
        34,
        "int",
        {"options": ["Option A", "Option B", "Option C"], "default_index": 0},
    ),
    "text_label": ComponentDefinition("text_label", "Text Label", "Informational text", 260, 26),
    "header_text": ComponentDefinition("header_text", "Header Text", "Section Header", 300, 34),
    "separator": ComponentDefinition("separator", "Separator", "Separator", 300, 18),
    "input_text": ComponentDefinition(
        "input_text",
        "Input Text",
        "Name",
        280,
        34,
        "char_buffer",
        {"default_text": "", "buffer_size": 128},
    ),
    "color_picker": ComponentDefinition(
        "color_picker",
        "Color Picker",
        "Accent Color",
        280,
        36,
        "color4",
        {"default_color": [1.0, 0.35, 0.2, 1.0]},
    ),
    "keybind": ComponentDefinition(
        "keybind",
        "Keybind Placeholder",
        "Shortcut",
        240,
        34,
        "int",
        {"default_key": "None"},
    ),
    "icon_button": ComponentDefinition(
        "icon_button",
        "Icon Button",
        "Tool",
        140,
        34,
        default_props={"callback_name": "OnTool", "icon": "[*]"},
    ),
    "social_link": ComponentDefinition(
        "social_link",
        "Social Link",
        "GitHub",
        190,
        34,
        default_props={"platform": "GitHub", "url": "https://github.com/", "icon": "[GH]", "button_style": "outline"},
    ),
    "feature_card": ComponentDefinition(
        "feature_card",
        "Feature Card",
        "Feature",
        320,
        96,
        default_props={
            "title": "Feature Title",
            "description": "Describe the feature or tool here.",
            "icon": "[*]",
            "button_text": "Open",
            "locked": False,
        },
    ),
    "status_badge": ComponentDefinition(
        "status_badge",
        "Status Badge",
        "Ready",
        150,
        28,
        default_props={"status": "Ready", "badge_color": "#2ecc71"},
    ),
    "progress_bar": ComponentDefinition(
        "progress_bar",
        "Progress Bar",
        "Progress",
        280,
        30,
        "float",
        {"value": 0.65, "min": 0.0, "max": 1.0, "overlay": "65%"},
    ),
    "image_placeholder": ComponentDefinition(
        "image_placeholder",
        "Image/Icon Placeholder",
        "Image",
        120,
        88,
        default_props={"icon_path": "", "placeholder": "[image]"},
    ),
    "nav_category": ComponentDefinition(
        "nav_category",
        "Nav Category",
        "Category Link",
        200,
        32,
        default_props={"icon": "[>]"},
    ),
    "tab_button": ComponentDefinition(
        "tab_button",
        "Tab Button",
        "Tab",
        140,
        32,
        default_props={"active": False},
    ),
    "footer_text": ComponentDefinition("footer_text", "Footer Text", "Footer text", 260, 26),
}


TOOLBOX_ORDER = [
    "button",
    "checkbox",
    "slider_float",
    "slider_int",
    "combo_box",
    "text_label",
    "header_text",
    "separator",
    "input_text",
    "color_picker",
    "keybind",
    "icon_button",
    "social_link",
    "feature_card",
    "status_badge",
    "progress_bar",
    "image_placeholder",
    "nav_category",
    "tab_button",
    "footer_text",
]


INTERACTIVE_TYPES = {
    "checkbox",
    "slider_float",
    "slider_int",
    "combo_box",
    "input_text",
    "color_picker",
    "keybind",
    "progress_bar",
}


def create_component(component_type: str, label: str | None = None) -> Component:
    definition = COMPONENT_DEFINITIONS.get(component_type, COMPONENT_DEFINITIONS["text_label"])
    display_label = label or definition.default_label
    variable_name = ""
    if definition.variable_kind:
        variable_name = make_variable_name(display_label, component_type)
    component = Component(
        type=definition.type,
        label=display_label,
        variable_name=variable_name,
        width=definition.default_width,
        height=definition.default_height,
        props=copy.deepcopy(definition.default_props),
    )
    if component_type == "button":
        component.props["callback_name"] = make_callback_name(display_label)
    if component_type == "icon_button":
        component.props["callback_name"] = make_callback_name(display_label)
    return component


def make_callback_name(label: str) -> str:
    words = re.sub(r"[^a-zA-Z0-9]+", " ", label).strip().split()
    if not words:
        return "OnButtonClick"
    return "On" + "".join(word[:1].upper() + word[1:] for word in words)
