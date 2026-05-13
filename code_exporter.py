"""Dear ImGui C++ export and project validation."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse
from typing import Any

try:
    from .components import INTERACTIVE_TYPES, make_callback_name, make_variable_name
    from .project_model import Animation, Component, ProjectModel
except ImportError:  # pragma: no cover
    from components import INTERACTIVE_TYPES, make_callback_name, make_variable_name
    from project_model import Animation, Component, ProjectModel


def cpp_escape(text: Any) -> str:
    value = str(text)
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def clean_identifier(name: str, fallback: str = "value") -> str:
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", str(name).strip()).strip("_")
    if not value:
        value = fallback
    if value[0].isdigit():
        value = f"v_{value}"
    return value


def _safe_callback(name: str, label: str) -> str:
    return clean_identifier(name or make_callback_name(label), "OnButtonClick")


def _hex_to_rgba(hex_color: str, fallback: str = "#ffffff") -> tuple[float, float, float, float]:
    raw = (hex_color or fallback).strip()
    if raw.startswith("#"):
        raw = raw[1:]
    if len(raw) not in {6, 8}:
        raw = fallback.strip("#")
    try:
        r = int(raw[0:2], 16) / 255.0
        g = int(raw[2:4], 16) / 255.0
        b = int(raw[4:6], 16) / 255.0
        a = int(raw[6:8], 16) / 255.0 if len(raw) == 8 else 1.0
    except ValueError:
        return _hex_to_rgba(fallback, "#ffffff")
    return r, g, b, a


def _vec4(hex_color: str, fallback: str = "#ffffff") -> str:
    r, g, b, a = _hex_to_rgba(hex_color, fallback)
    return f"ImVec4({r:.3f}f, {g:.3f}f, {b:.3f}f, {a:.3f}f)"


def _component_var(component: Component) -> str:
    if component.type not in INTERACTIVE_TYPES:
        return ""
    return clean_identifier(component.variable_name or make_variable_name(component.label, component.type), component.type)


def _as_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _as_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def validate_project(project: ProjectModel) -> list[str]:
    """Return export warnings. Validation stays permissive so work is not lost."""

    warnings: list[str] = []
    if not project.menu_title.strip():
        warnings.append("Menu title is empty.")
    if project.window_width < 220 or project.window_height < 180:
        warnings.append("Window size is very small; exported menu may be cramped.")
    if not project.categories:
        warnings.append("Project has no categories.")

    seen_vars: dict[str, str] = {}
    for category in project.categories:
        if not category.name.strip():
            warnings.append("A category has an empty name.")
        for component in category.components:
            if component.type != "separator" and not component.label.strip():
                warnings.append(f"Component {component.id} has an empty label.")
            var_name = _component_var(component)
            if var_name:
                if var_name in seen_vars:
                    warnings.append(f"Duplicate variable name '{var_name}' on '{component.label}' and '{seen_vars[var_name]}'.")
                seen_vars[var_name] = component.label
            if component.type == "social_link":
                url = str(component.props.get("url", "")).strip()
                parsed = urlparse(url)
                if url and parsed.scheme not in {"http", "https"}:
                    warnings.append(f"Social link '{component.label}' has an invalid URL.")
            if component.type == "image_placeholder":
                icon_path = str(component.props.get("icon_path", "")).strip()
                if icon_path and not os.path.exists(icon_path):
                    warnings.append(f"Image placeholder '{component.label}' references a missing file.")
    return warnings


def _variable_declaration(component: Component) -> str:
    var_name = _component_var(component)
    if not var_name:
        return ""
    props = component.props
    if component.type == "checkbox":
        return f"static bool {var_name} = {'true' if _as_bool(props.get('default_value')) else 'false'};"
    if component.type == "slider_float":
        return f"static float {var_name} = {_as_float(props.get('default_value'), 0.0):.3f}f;"
    if component.type in {"slider_int", "combo_box", "keybind"}:
        default_key = 0 if component.type != "combo_box" else _as_int(props.get("default_index"), 0)
        if component.type == "slider_int":
            default_key = _as_int(props.get("default_value"), 0)
        return f"static int {var_name} = {default_key};"
    if component.type == "input_text":
        size = max(8, _as_int(props.get("buffer_size"), 128))
        default_text = cpp_escape(props.get("default_text", ""))
        return f'static char {var_name}[{size}] = "{default_text}";'
    if component.type == "color_picker":
        color = props.get("default_color", [1.0, 1.0, 1.0, 1.0])
        if not isinstance(color, list) or len(color) != 4:
            color = [1.0, 1.0, 1.0, 1.0]
        values = ", ".join(f"{_as_float(item, 1.0):.3f}f" for item in color)
        return f"static float {var_name}[4] = {{ {values} }};"
    if component.type == "progress_bar":
        return f"static float {var_name} = {_as_float(props.get('value', props.get('default_value', 0.65)), 0.65):.3f}f;"
    return ""


def _animation_lines(animation: Animation, label: str) -> list[str]:
    if not animation.enabled or animation.type == "None":
        return []
    return [
        f"// Animation: {animation.type} ({label})",
        f"// duration={animation.duration:.2f}s delay={animation.delay:.2f}s speed={animation.speed:.2f} intensity={animation.intensity:.2f} easing={animation.easing}",
        "// Use ImGui::GetTime() plus the helper functions below to animate alpha, position, border color, or glow.",
    ]


def _project_uses_animation(project: ProjectModel, components: list[Component] | None = None) -> bool:
    components = components if components is not None else project.all_components()
    if project.animation.enabled and project.animation.type != "None":
        return True
    if project.background.type in {"Animated Gradient", "Cyber Grid", "Floating Particles", "Glow Orbs", "Starfield", "Scanlines", "Noise Texture Simulation"}:
        return True
    for group in project.groups:
        if group.animation.enabled and group.animation.type != "None":
            return True
    return any(component.animation.enabled and component.animation.type != "None" for component in components)


def _animation_helpers() -> list[str]:
    return [
        "float ForgePulse(float speed = 2.0f, float minVal = 0.35f, float maxVal = 1.0f) {",
        "    return minVal + (maxVal - minVal) * (0.5f + 0.5f * sinf((float)ImGui::GetTime() * speed));",
        "}",
        "",
        "float ForgeEaseInOut(float t) {",
        "    t = t < 0.0f ? 0.0f : (t > 1.0f ? 1.0f : t);",
        "    return 0.5f - 0.5f * cosf(t * 3.14159265f);",
        "}",
        "",
    ]


def _background_code(project: ProjectModel) -> list[str]:
    bg = project.background
    lines = [
        "void RenderBackground() {",
        f"    // Background: {cpp_escape(bg.type)}",
        f"    // speed={bg.animation_speed:.2f}, particles={int(bg.particle_count)}, grid={int(bg.grid_size)}, glow={bg.glow_intensity:.2f}, opacity={bg.opacity:.2f}",
        "    ImDrawList* draw = ImGui::GetWindowDrawList();",
        "    ImVec2 pos = ImGui::GetWindowPos();",
        "    ImVec2 size = ImGui::GetWindowSize();",
        "    ImVec2 max = ImVec2(pos.x + size.x, pos.y + size.y);",
        f"    ImU32 primary = ImGui::ColorConvertFloat4ToU32({_vec4(bg.primary_color, project.theme.primary_background)});",
        f"    ImU32 secondary = ImGui::ColorConvertFloat4ToU32({_vec4(bg.secondary_color, project.theme.secondary_background)});",
        f"    ImU32 accent = ImGui::ColorConvertFloat4ToU32({_vec4(bg.accent_color, project.theme.accent)});",
    ]
    if bg.type == "Solid Color":
        lines.append("    draw->AddRectFilled(pos, max, primary);")
    elif bg.type in {"Linear Gradient Preview", "Animated Gradient", "Glassmorphism Blur Preview"}:
        lines.extend(
            [
                "    // Dear ImGui does not provide a high-level gradient widget; draw-list gradients are a good lightweight approximation.",
                "    draw->AddRectFilledMultiColor(pos, max, primary, secondary, secondary, primary);",
                "    // TODO: for Animated Gradient, offset colors over time with ImGui::GetTime().",
            ]
        )
    elif bg.type == "Cyber Grid":
        lines.extend(
            [
                "    draw->AddRectFilled(pos, max, primary);",
                f"    float grid = {float(bg.grid_size):.1f}f;",
                f"    float offset = fmodf((float)ImGui::GetTime() * {float(bg.animation_speed * 24):.2f}f, grid);",
                "    for (float x = pos.x - grid + offset; x < max.x; x += grid) draw->AddLine(ImVec2(x, pos.y), ImVec2(x, max.y), accent, 1.0f);",
                "    for (float y = pos.y - grid + offset; y < max.y; y += grid) draw->AddLine(ImVec2(pos.x, y), ImVec2(max.x, y), accent, 1.0f);",
            ]
        )
    elif bg.type in {"Floating Particles", "Starfield"}:
        lines.extend(
            [
                "    draw->AddRectFilled(pos, max, primary);",
                "    // Deterministic placeholder particles. Replace with your app's particle state if needed.",
                f"    for (int i = 0; i < {max(4, min(180, int(bg.particle_count)))}; ++i) {{",
                "        float x = pos.x + fmodf(i * 53.0f + (float)ImGui::GetTime() * 18.0f, size.x);",
                "        float y = pos.y + fmodf(i * 97.0f + (float)ImGui::GetTime() * 11.0f, size.y);",
                "        draw->AddCircleFilled(ImVec2(x, y), 1.8f + (i % 3), accent);",
                "    }",
            ]
        )
    elif bg.type == "Glow Orbs":
        lines.extend(
            [
                "    draw->AddRectFilled(pos, max, primary);",
                "    // TODO: approximate glow with layered translucent circles or your renderer's blur pass.",
                "    draw->AddCircleFilled(ImVec2(pos.x + size.x * 0.25f, pos.y + size.y * 0.35f), 80.0f, accent);",
                "    draw->AddCircleFilled(ImVec2(pos.x + size.x * 0.78f, pos.y + size.y * 0.68f), 95.0f, secondary);",
            ]
        )
    elif bg.type == "Scanlines":
        lines.extend(
            [
                "    draw->AddRectFilled(pos, max, primary);",
                "    float offset = fmodf((float)ImGui::GetTime() * 36.0f, 8.0f);",
                "    for (float y = pos.y + offset; y < max.y; y += 8.0f) draw->AddLine(ImVec2(pos.x, y), ImVec2(max.x, y), accent, 1.0f);",
            ]
        )
    else:
        lines.extend(
            [
                "    draw->AddRectFilled(pos, max, primary);",
                f"    // TODO: implement draw-list approximation for {cpp_escape(bg.type)}.",
            ]
        )
    lines.extend(["}", ""])
    return lines


def _combo_items(component: Component) -> list[str]:
    options = component.props.get("options", [])
    if isinstance(options, str):
        options = [item.strip() for item in options.split(",") if item.strip()]
    if not isinstance(options, list) or not options:
        options = ["Option A", "Option B"]
    return [str(item) for item in options]


def _component_code(component: Component) -> list[str]:
    label = cpp_escape(component.label)
    width = max(0, _as_int(component.width, 0))
    height = max(0, _as_int(component.height, 0))
    size_expr = f", ImVec2({width}, {height})" if width and height and component.type in {"button", "icon_button", "social_link"} else ""
    var_name = _component_var(component)
    props = component.props

    if not component.visible:
        return [f"// Hidden component skipped: {label}"]

    disabled_open = []
    disabled_close = []
    if not component.enabled:
        disabled_open = ["ImGui::BeginDisabled();"]
        disabled_close = ["ImGui::EndDisabled();"]

    body: list[str]
    body = _animation_lines(component.animation, component.label)

    if component.type == "button":
        callback = _safe_callback(str(props.get("callback_name", "")), component.label)
        body += [f'if (ImGui::Button("{label}"{size_expr})) {{', f"    {callback}();", "}"]
    elif component.type == "checkbox":
        body += [f'ImGui::Checkbox("{label}", &{var_name});']
    elif component.type == "slider_float":
        body += [
            f'ImGui::SliderFloat("{label}", &{var_name}, {_as_float(props.get("min"), 0.0):.3f}f, '
            f'{_as_float(props.get("max"), 1.0):.3f}f, "{cpp_escape(props.get("format", "%.2f"))}");'
        ]
    elif component.type == "slider_int":
        body += [
            f'ImGui::SliderInt("{label}", &{var_name}, {_as_int(props.get("min"), 0)}, '
            f'{_as_int(props.get("max"), 100)}, "{cpp_escape(props.get("format", "%d"))}");'
        ]
    elif component.type == "combo_box":
        items_name = f"{var_name}_items"
        items = ", ".join(f'"{cpp_escape(item)}"' for item in _combo_items(component))
        body += [
            f"static const char* {items_name}[] = {{ {items} }};",
            f'ImGui::Combo("{label}", &{var_name}, {items_name}, IM_ARRAYSIZE({items_name}));',
        ]
    elif component.type == "text_label":
        body += [f'ImGui::TextUnformatted("{label}");']
    elif component.type == "header_text":
        body += [
            f'ImGui::TextColored(ImVec4(0.75f, 0.85f, 1.0f, 1.0f), "{label}");',
            "ImGui::Separator();",
        ]
    elif component.type == "separator":
        body += ["ImGui::Separator();"]
    elif component.type == "input_text":
        body += [f'ImGui::InputText("{label}", {var_name}, IM_ARRAYSIZE({var_name}));']
    elif component.type == "color_picker":
        body += [f'ImGui::ColorEdit4("{label}", {var_name});']
    elif component.type == "keybind":
        body += [
            f'ImGui::TextUnformatted("{label}");',
            'ImGui::SameLine();',
            f'ImGui::Button("{cpp_escape(props.get("default_key", "None"))}"); // TODO: wire key capture logic.',
        ]
    elif component.type == "icon_button":
        callback = _safe_callback(str(props.get("callback_name", "")), component.label)
        icon_label = cpp_escape(f"{props.get('icon', '[*]')} {component.label}".strip())
        body += [f'if (ImGui::Button("{icon_label}"{size_expr})) {{', f"    {callback}();", "}"]
    elif component.type == "social_link":
        platform = cpp_escape(props.get("platform", component.label))
        url = cpp_escape(props.get("url", ""))
        icon = cpp_escape(props.get("icon", ""))
        body += [
            f'if (ImGui::Button("{icon} {platform}"{size_expr})) {{',
            f'    // TODO: open URL: {url}',
            "}",
        ]
    elif component.type == "feature_card":
        title = cpp_escape(props.get("title", component.label))
        description = cpp_escape(props.get("description", ""))
        button_text = cpp_escape(props.get("button_text", "Open"))
        body += [
            f'ImGui::BeginChild("{clean_identifier(title, "feature_card")}", ImVec2({max(width, 260)}, {max(height, 86)}), true);',
            f'ImGui::TextUnformatted("{title}");',
            f'ImGui::TextWrapped("{description}");',
            f'if (ImGui::Button("{button_text}")) {{',
            "    // TODO: connect feature action.",
            "}",
            "ImGui::EndChild();",
        ]
    elif component.type == "status_badge":
        status = cpp_escape(props.get("status", component.label))
        body += [f'ImGui::TextColored({_vec4(str(props.get("badge_color", "#2ecc71")), "#2ecc71")}, "{status}");']
    elif component.type == "progress_bar":
        overlay = cpp_escape(props.get("overlay", ""))
        body += [f'ImGui::ProgressBar({var_name}, ImVec2({max(width, 160)}, {max(height, 18)}), "{overlay}");']
    elif component.type == "image_placeholder":
        body += [
            f'ImGui::Button("{label}", ImVec2({max(width, 80)}, {max(height, 64)}));',
            "// TODO: replace placeholder with an ImTextureID-backed ImageButton/Image.",
        ]
    elif component.type == "nav_category":
        body += [f'ImGui::BulletText("{label}");']
    elif component.type == "tab_button":
        body += [f'ImGui::Button("{label}");']
    elif component.type == "footer_text":
        body += [f'ImGui::TextDisabled("{label}");']
    else:
        body += [f'ImGui::TextUnformatted("{label}");']

    if component.tooltip:
        body.extend(
            [
                "if (ImGui::IsItemHovered()) {",
                f'    ImGui::SetTooltip("{cpp_escape(component.tooltip)}");',
                "}",
            ]
        )
    return disabled_open + body + disabled_close


def export_cpp(project: ProjectModel) -> str:
    """Generate a complete, readable Dear ImGui C++ snippet."""

    theme = project.theme
    lines: list[str] = [
        "// Generated by ImGui Forge Builder.",
        "// This is a starting point; connect callbacks and runtime state to your own application.",
        "#include \"imgui.h\"",
        "#include <cmath>",
        "#include <cstring>",
        "",
        "namespace ImGuiForgeGenerated {",
        "",
    ]

    if _project_uses_animation(project):
        lines.extend(_animation_helpers())

    declarations = []
    callbacks: dict[str, str] = {}
    for component in project.all_components():
        declaration = _variable_declaration(component)
        if declaration:
            declarations.append(declaration)
        if component.type in {"button", "icon_button"}:
            callback = _safe_callback(str(component.props.get("callback_name", "")), component.label)
            callbacks[callback] = component.label

    if declarations:
        lines.extend(declarations)
        lines.append("")
    for callback, label in callbacks.items():
        lines.extend(
            [
                f"void {callback}() {{",
                f"    // TODO: implement action for {cpp_escape(label)}.",
                "}",
                "",
            ]
        )

    lines.extend(
        [
            "void ApplyCustomTheme() {",
            "    ImGuiStyle& style = ImGui::GetStyle();",
            f"    style.WindowRounding = {int(theme.rounding)}.0f;",
            f"    style.ChildRounding = {int(theme.rounding)}.0f;",
            f"    style.FrameRounding = {max(0, int(theme.rounding) - 2)}.0f;",
            f"    style.WindowBorderSize = {int(theme.border_thickness)}.0f;",
            f"    style.Alpha = {float(theme.alpha):.2f}f;",
            f"    style.WindowPadding = ImVec2({int(theme.window_padding)}, {int(theme.window_padding)});",
            f"    style.FramePadding = ImVec2({int(theme.frame_padding)}, {int(max(2, theme.frame_padding * 0.62))});",
            f"    style.ItemSpacing = ImVec2({int(theme.item_spacing)}, {int(theme.item_spacing)});",
            f"    // Font scale requested by the builder: {float(theme.font_scale):.2f}.",
            "    // Apply it in your host app with io.FontGlobalScale or your font atlas setup if needed.",
            "",
            "    ImVec4* colors = style.Colors;",
            f"    colors[ImGuiCol_WindowBg] = {_vec4(theme.primary_background or theme.background, '#151922')};",
            f"    colors[ImGuiCol_ChildBg] = {_vec4(theme.panel, '#1e2430')};",
            f"    colors[ImGuiCol_PopupBg] = {_vec4(theme.card or theme.panel, '#242c3a')};",
            f"    colors[ImGuiCol_Border] = {_vec4(theme.border, '#30384a')};",
            f"    colors[ImGuiCol_Text] = {_vec4(theme.text, '#f2f5fa')};",
            f"    colors[ImGuiCol_TextDisabled] = {_vec4(theme.muted_text, '#96a0b5')};",
            f"    colors[ImGuiCol_Button] = {_vec4(theme.accent, '#4f8cff')};",
            f"    colors[ImGuiCol_ButtonHovered] = {_vec4(theme.nav_hover or theme.hover, '#2f3b52')};",
            f"    colors[ImGuiCol_ButtonActive] = {_vec4(theme.nav_active or theme.active, '#365d9f')};",
            f"    colors[ImGuiCol_FrameBg] = {_vec4(theme.panel, '#1e2430')};",
            f"    colors[ImGuiCol_FrameBgHovered] = {_vec4(theme.hover, '#2f3b52')};",
            f"    colors[ImGuiCol_FrameBgActive] = {_vec4(theme.active, '#365d9f')};",
            "}",
            "",
        ]
    )

    lines.extend(_background_code(project))

    for index, category in enumerate(project.categories):
        func_name = clean_identifier(f"Render_{category.name}", f"RenderCategory{index}")
        lines.extend([f"void {func_name}() {{"])
        if not category.components:
            lines.append('    ImGui::TextDisabled("No components in this category yet.");')
        emitted_group_comments: set[str] = set()
        for component in category.components:
            if component.group_id and component.group_id not in emitted_group_comments:
                group = project.find_group(component.group_id)
                if group:
                    lines.append(f"    // Preset group: {cpp_escape(group.name)}")
                    for comment in _animation_lines(group.animation, group.name):
                        lines.append(f"    {comment}")
                    emitted_group_comments.add(component.group_id)
            for code_line in _component_code(component):
                lines.append(f"    {code_line}")
        lines.extend(["}", ""])

    lines.extend(
        [
            "void RenderNavigation(int& activeCategory) {",
            f"    // Nav style: {cpp_escape(project.nav_style)} / position: {cpp_escape(project.nav_position)}",
        ]
    )
    if project.nav_position in {"top", "bottom"}:
        for index, category in enumerate(project.categories):
            same_line = "ImGui::SameLine();" if index > 0 else ""
            if same_line:
                lines.append(f"    {same_line}")
            lines.append(f'    if (ImGui::Button("{cpp_escape(category.icon + " " if category.icon else "")}{cpp_escape(category.name)}")) activeCategory = {index};')
        lines.append("    ImGui::Separator();")
    else:
        for index, category in enumerate(project.categories):
            label = cpp_escape(f"{category.icon} {category.name}".strip())
            lines.append(f'    if (ImGui::Selectable("{label}", activeCategory == {index})) activeCategory = {index};')
    lines.extend(["}", ""])

    lines.extend(
        [
            "void RenderMenu() {",
            "    ApplyCustomTheme();",
            f"    ImGui::SetNextWindowSize(ImVec2({int(project.window_width)}, {int(project.window_height)}), ImGuiCond_FirstUseEver);",
            f'    if (ImGui::Begin("{cpp_escape(project.menu_title)}")) {{',
            "        RenderBackground();",
            "        static int activeCategory = 0;",
        ]
    )

    if project.nav_position == "top":
        lines.extend(
            [
                "        RenderNavigation(activeCategory);",
                '        ImGui::BeginChild("Content", ImVec2(0, 0), false);',
            ]
        )
    elif project.nav_position == "right":
        lines.extend(
            [
                '        ImGui::BeginChild("Content", ImVec2(-170, 0), false);',
            ]
        )
    elif project.nav_position == "bottom":
        lines.extend(
            [
                '        ImGui::BeginChild("Content", ImVec2(0, -54), false);',
            ]
        )
    else:
        lines.extend(
            [
                '        ImGui::BeginChild("Navigation", ImVec2(160, 0), true);',
                "        RenderNavigation(activeCategory);",
                "        ImGui::EndChild();",
                "        ImGui::SameLine();",
                '        ImGui::BeginChild("Content", ImVec2(0, 0), false);',
            ]
        )

    lines.extend(["        switch (activeCategory) {"])
    for index, category in enumerate(project.categories):
        func_name = clean_identifier(f"Render_{category.name}", f"RenderCategory{index}")
        lines.append(f"        case {index}: {func_name}(); break;")
    lines.extend(
        [
            "        default: break;",
            "        }",
            "        ImGui::EndChild();",
        ]
    )

    if project.nav_position == "right":
        lines.extend(
            [
                "        ImGui::SameLine();",
                '        ImGui::BeginChild("Navigation", ImVec2(160, 0), true);',
                "        RenderNavigation(activeCategory);",
                "        ImGui::EndChild();",
            ]
        )
    elif project.nav_position == "bottom":
        lines.extend(
            [
                '        ImGui::BeginChild("Navigation", ImVec2(0, 44), true);',
                "        RenderNavigation(activeCategory);",
                "        ImGui::EndChild();",
            ]
        )

    lines.extend(
        [
            "    }",
            "    ImGui::End();",
            "}",
            "",
            "} // namespace ImGuiForgeGenerated",
            "",
        ]
    )
    return "\n".join(lines)


def export_element_cpp(project: ProjectModel, selection_kind: str, selection_id: str) -> str:
    """Export only the selected component or preset group as a standalone block."""

    components: list[Component] = []
    title = "Selected Element"
    group_animation = Animation()
    if selection_kind == "component":
        _, component = project.find_component(selection_id)
        if not component:
            return ""
        components = [component]
        title = component.label
    elif selection_kind == "group":
        group = project.find_group(selection_id)
        if not group:
            return ""
        components = project.components_in_group(group.id)
        title = group.name
        group_animation = group.animation
    else:
        return ""

    lines: list[str] = [
        "// Generated element block from ImGui Forge Builder.",
        f"// Element: {cpp_escape(title)}",
        "#include \"imgui.h\"",
        "#include <cmath>",
        "#include <cstring>",
        "",
    ]
    if _project_uses_animation(project, components) or (group_animation.enabled and group_animation.type != "None"):
        lines.extend(_animation_helpers())

    declarations = []
    callbacks: dict[str, str] = {}
    for component in components:
        declaration = _variable_declaration(component)
        if declaration:
            declarations.append(declaration)
        if component.type in {"button", "icon_button"}:
            callback = _safe_callback(str(component.props.get("callback_name", "")), component.label)
            callbacks[callback] = component.label
    if declarations:
        lines.extend(declarations)
        lines.append("")
    for callback, label in callbacks.items():
        lines.extend(
            [
                f"void {callback}() {{",
                f"    // TODO: implement action for {cpp_escape(label)}.",
                "}",
                "",
            ]
        )

    func_name = clean_identifier(f"Render_{title}", "RenderSelectedElement")
    lines.append(f"void {func_name}() {{")
    for comment in _animation_lines(group_animation, title):
        lines.append(f"    {comment}")
    for component in components:
        for code_line in _component_code(component):
            lines.append(f"    {code_line}")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)
