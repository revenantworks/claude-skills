# Surfaces: what changes per medium

Load when the surface is a plugin pane, a game menu or HUD, or a store page. A web page or a
single-page artifact needs nothing here: the brief in `direction.md` and the probe in `probe.md`
cover it as written.

## Plugin pane

A pane lives inside a host that sets its width, its theme and its fonts.

- **Widths.** Add the narrowest width the host lets the pane shrink to, measured in the host, to the
  probe's set. A side panel is often narrower than a phone.
- **Theme from the host.** Colours come from the host's variables, never from values written into
  the pane (law 1). A VS Code webview gets a body class per theme kind (`vscode-light`,
  `vscode-dark`, `vscode-high-contrast`) and every theme colour as a CSS variable named `--vscode-`
  plus the colour id with dots turned into hyphens (`--vscode-editor-foreground`). The probe sets
  each body class in turn (`probe.md` section 2).
- **High contrast is a theme.** When the host offers one, it is in the theme set.
- **Density.** A pane is a task surface: dense, scannable, one primary action per view.

## Game menu and HUD

The probe does not run inside a game. Fit is checked from the user's screenshots, one per
resolution and state, against the brief; run proof and the scene review are godotsmith's. Godot 4
is the worked case.

- **A resolution set, not a width set.** The brief lists every target display as resolution and
  aspect ratio (a 16:9 set from 1280 by 720 up, plus 16:10, ultrawide or 4:3 when the game supports
  them, and a handheld's own screen). The stretch mode and aspect setting that make the UI scale are
  project settings godotsmith reads and guards.
- **Layout by anchors and containers.** Controls sit in containers or are anchored to the screen
  edges, never at fixed pixel positions, so a change of aspect moves them instead of cutting them.
- **The focus path.** Every interactive Control can take focus by keyboard and gamepad; each screen
  names its first focus; where the container order would move focus the wrong way, the brief sets
  the neighbours. In Godot 4 a Control's focus mode decides whether it takes keyboard and
  controller focus, the focus neighbour properties fix the direction, and `grab_focus()` (usually
  deferred in `_ready()`) gives the first focus; without it, controller input does nothing at
  start-up (Godot docs, "Keyboard/Controller Navigation and Focus").
- **Text at distance.** A game played from a couch needs larger text than one played at a desk. The
  brief states the minimum text height at its lowest target resolution and cites where the figure
  comes from (the target platform's own accessibility guideline); it never invents one.
- **The HUD.** It shows what the moment needs, keeps clear of where the player looks, and stays
  inside the display's safe area on platforms that have one. Scaling or hiding HUD elements is an
  option the brief offers when the platform guideline asks for it.
- **Pixel-art UI.** Integer scaling and nearest filtering are pixelsmith's precondition and
  godotsmith's settings; icons and sprites are pixelsmith's. uismith places them.

## Store page

uismith gives the section order, the hierarchy, and the fit of a store page the builder can preview
(the preview URL is probed like any page). Every word on it (title, blurb, tags, feature list) is
commscribe's; pixel-art capsules and screenshots are pixelsmith's to direct; a brand pass is
brandscribe's.
