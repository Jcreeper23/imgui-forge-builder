# ImGui Forge Builder

ImGui Forge Builder is a local visual builder for designing Dear ImGui-style menus, tools, launchers, overlays, debug panels, and software interfaces. It gives you a toolbox, live preview canvas, hierarchy, properties inspector, theme editor, JSON project save/load, validation, and clean Dear ImGui C++ export.

## Install

```bash
pip install PySide6
```

## Run

From this folder:

```bash
python main.py
```

From the workspace root:

```bash
python imgui_forge_builder/main.py
```

## Basic Workflow

1. Pick a starter template from the left panel and press **Apply**, or use **New** for the minimal template.
2. Add categories with **Add Cat** in the hierarchy panel.
3. Click toolbox components to add them to the active category.
4. Select a component in the hierarchy or preview canvas.
5. Edit labels, variable names, sizes, defaults, tooltip text, colors, and type-specific settings in the **Properties** tab.
6. Use **Theme** to change colors, spacing, rounding, font scale, border thickness, and shadow style.
7. Use **Presets** to insert polished multi-component blocks such as hero sections, login forms, status panels, social footers, animated backgrounds, and config managers.
8. Use the bottom **Generated C++** tab to inspect exported Dear ImGui code live.

## Components

The toolbox currently includes:

- Button
- Toggle / Checkbox
- Slider Float
- Slider Int
- Combo Box
- Text Label
- Header Text
- Separator
- Input Text
- Color Picker placeholder
- Keybind placeholder
- Icon Button
- Social Link
- Feature Card
- Status Badge
- Image/Icon placeholder
- Nav Category
- Tab Button
- Footer Text

Interactive widgets create config variables automatically. You can rename those variables in the inspector before export.

## Element Presets

The **Presets** tab contains reusable blocks with a thumbnail card, description, tags, filter, and one-click **Add to Menu** button. Inserting a preset creates real editable components in the active category and wraps them in a lightweight group.

Built-in preset families include:

- Hero CTA and launch blocks
- Slider and toggle cards
- Combo selector cards
- Social link blocks
- Feature and locked feature cards
- Account/license status panels
- Config manager panels
- Modern login/auth blocks
- Animated background presets
- Navigation starter blocks

Select a component or group and use **Save as Preset** to store a custom preset in `projects/custom_presets.json`.

## Animations And Backgrounds

Animation settings are available in the inspector for the whole menu, selected groups, and individual components. Supported animation metadata includes fade, slide, pulse glow, hover glow/scale, floating, shake, loading dots, animated gradient, particle drift, and scanline sweep.

The **Theme** tab also includes background controls:

- Solid Color
- Linear Gradient Preview
- Animated Gradient
- Cyber Grid
- Floating Particles
- Glow Orbs
- Starfield
- Scanlines
- Glassmorphism Blur Preview
- Noise Texture Simulation

Use **Play Animations** and **Reset Anim** in the toolbar to preview motion in the canvas.

## Categories And Navigation

Categories are shown in the hierarchy and preview navigation. Select a category to make it active. You can add, rename, delete, reorder, and assign icons to categories.

Navigation options:

- left
- right
- top
- bottom

Navigation styles:

- vertical sidebar
- top tabs
- pill tabs
- icon sidebar

## Layout

Auto layout stacks components vertically using theme spacing and padding. Free layout lets you drag components around the preview canvas and stores `x` / `y` coordinates. Snap-to-grid can be toggled from the toolbar or layout panel.

Toolbar layout helpers:

- **Align Left**
- **Align Center**
- **Align Right**
- **Distribute**

## Save And Load

Use **Save** and **Load** to store projects as JSON. The JSON includes project metadata, menu size, theme, navigation settings, categories, components, properties, and layout state.

The default save location is:

```text
projects/my_menu.json
```

## Export Dear ImGui Code

Use **Copy Code** to copy generated C++ to the clipboard, or **Export Code** to save a `.cpp` file.

Use **Copy Element Code** to copy only the selected component or preset group as a standalone ImGui block.

The generated code includes:

- `ApplyCustomTheme()`
- `RenderBackground()`
- `RenderMenu()`
- navigation rendering
- one render function per category
- static config variables for checkboxes, sliders, combos, inputs, color pickers, and keybind placeholders
- placeholder callbacks for buttons and icon buttons
- animation helper stubs/comments when animations are used
- TODO comments where real runtime behavior should be connected

The exported code is a clean starting point. You still connect real application behavior, texture loading, URL opening, key capture, persistence, and callback bodies manually in your own project.

## Validation

Before export/copy, the builder checks for common issues:

- duplicate variable names
- empty menu title
- empty category names
- empty component labels
- invalid social URLs
- missing image/icon paths
- unusually small menu sizes

Warnings are shown in the bottom log panel and status bar.

## Extending Components

New component types are easiest to add in this order:

1. Add a `ComponentDefinition` in `components.py`.
2. Add preview drawing in `canvas.py`.
3. Add editable fields in `properties.py`.
4. Add C++ export logic in `code_exporter.py`.
5. Optionally add template usage in `assets.py`.

The project model is intentionally UI-agnostic, so new widgets can be serialized, previewed, and exported without rewriting the whole app.
