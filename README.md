# ImGui Forge Builder

**ImGui Forge Builder** is a local visual editor for designing modern Dear ImGui-style menus without manually writing every UI element first.

It lets you visually create menu layouts, organize components into categories, customize themes, preview the design live, save/load projects, insert polished presets, and export clean Dear ImGui C++ code.

> Built for designing legitimate GUI menus, tools, launchers, overlays, debug panels, software panels, and custom interfaces.

---

## Preview

ImGui Forge Builder includes a professional editor layout with:

- Left-side component toolbox
- Center live preview canvas
- Right-side properties inspector
- Theme editor
- Presets library
- Category/navigation builder
- Bottom output/log/code panel
- Save/load project system
- Dear ImGui C++ exporter

---

## Features

### Visual Menu Builder

Create ImGui-style menus visually using editable components such as:

- Buttons
- Text labels
- Header text
- Checkboxes/toggles
- Sliders
- Combo boxes
- Input fields
- Separators
- Social links
- Feature cards
- Status badges
- Image/icon placeholders
- Footer text
- Navigation categories
- Tab buttons

The preview canvas gives a live visual approximation of what the final menu will look like.

---

### Component Toolbox

Quickly add UI elements into the selected category or tab.

Supported actions include:

- Add components
- Select components
- Edit properties
- Duplicate elements
- Delete elements
- Reorder elements
- Auto-layout support
- Free-layout positioning
- Snap-to-grid style editing

---

### Categories and Navigation

Build organized menu layouts with custom categories.

Example categories:

- Home
- Settings
- Configs
- Socials
- Dashboard
- Tools
- About

Navigation supports multiple styles and positions:

- Left sidebar
- Right sidebar
- Top tabs
- Bottom navigation
- Pill tabs
- Icon/sidebar style layouts

---

### Properties Inspector

Every selected component can be edited from the properties panel.

Common editable properties include:

- Label/text
- Variable name
- Width and height
- X/Y position
- Category assignment
- Tooltip
- Visibility
- Enabled/disabled state
- Colors
- Component-specific options

Examples:

Checkboxes create boolean variables.

Sliders create integer or float variables.

Combo boxes create selectable option lists.

Buttons create callback placeholder names.

---

### Theme Editor

Customize the full look of the menu with advanced theme controls.

Theme options include:

- Primary background
- Secondary background
- Panel color
- Card color
- Sidebar color
- Accent color
- Secondary accent color
- Navigation active color
- Navigation hover color
- Text color
- Muted text color
- Border color
- Shadow/glow color
- Success color
- Warning color
- Danger color
- Rounding
- Border thickness
- Item spacing
- Frame padding
- Window padding
- Font scale
- Button height
- Card padding
- Glow intensity
- Transparency/alpha

Included theme presets:

- Cyber Blue
- Neon Purple
- Emerald Matrix
- Redline Dark
- Frosted Glass
- Minimal Pro
- Midnight Gold
- Toxic Green
- Ocean Glow
- Sunset Neon

---

### Animated Backgrounds

ImGui Forge Builder supports animated background presets in the preview.

Background types include:

- Solid color
- Linear gradient
- Animated gradient
- Cyber grid
- Floating particles
- Glow orbs
- Starfield
- Scanlines
- Glassmorphism preview
- Noise texture simulation

Background settings include:

- Primary color
- Secondary color
- Accent color
- Animation speed
- Particle count
- Grid size
- Glow intensity
- Opacity
- Blur/softness approximation

Exported code includes commented ImGui draw-list stubs so the background can be recreated in a real Dear ImGui project.

---

### Animation System

Components, groups, presets, and backgrounds can store animation settings.

Supported animation types include:

- None
- Fade In
- Slide In Left
- Slide In Right
- Slide In Up
- Slide In Down
- Pulse Glow
- Hover Scale
- Hover Glow
- Border Glow
- Floating
- Shake Error
- Loading Dots
- Animated Gradient
- Particle Drift
- Scanline Sweep

Animation properties include:

- Enabled/disabled
- Animation type
- Duration
- Delay
- Speed
- Intensity
- Looping
- Easing mode

Exported code includes comments and helper stubs showing where to connect animation logic using `ImGui::GetTime()`.

---

### Element Presets Library

The builder includes a presets panel for inserting polished reusable UI blocks.

Each preset includes:

- Name
- Description
- Tags
- Category
- Preview-style card
- One-click add button
- Real editable components after insertion

Preset categories include:

- Hero Sections
- Feature Cards
- Buttons
- Sliders
- Toggles
- Social Blocks
- Status Panels
- Login/Auth Blocks
- Config Blocks
- Animated Backgrounds
- Navigation Styles
- Info Panels
- Dashboard Cards

Included preset examples:

- Hero CTA Block
- Launch Panel
- Welcome Action Card
- Premium Slider Row
- Settings Slider Card
- Glow Toggle Card
- Feature Toggle Row
- Mode Selector
- Theme Dropdown Card
- Creator Social Footer
- Social Hub Block
- Premium Feature Card
- Locked Feature Tile
- Account Status Panel
- License Info Card
- Config Manager Panel
- Modern Login Block
- Cyber Grid Background
- Floating Particles Background
- Gradient Glow Background

Presets are inserted as real components, not fake mockups, so they can be edited after being added.

---

### Full Menu Templates

ImGui Forge Builder includes animated full-menu templates.

Templates include:

- Premium Software Launcher
- Cyber Settings Menu
- Creator/Social Hub
- Config Manager UI
- Minimal Professional Menu

Templates can include:

- Categories
- Components
- Presets
- Themes
- Backgrounds
- Animations
- Social blocks
- Feature cards
- Config panels
- Status panels

---

### Save and Load Projects

Projects can be saved and loaded as JSON.

Saved project data includes:

- Project name
- Menu title
- Window size
- Theme settings
- Background settings
- Navigation style
- Navigation position
- Categories
- Components
- Groups
- Preset blocks
- Animation settings
- Layout mode

Default save location:

```txt
projects/
