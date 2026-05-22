import json
import os
import re
from dataclasses import dataclass
from typing import Any

import carb
import omni.kit.app
import omni.kit.context_menu
import omni.kit.menu.utils
import omni.usd
from omni.kit.menu.utils import MenuItemDescription, MenuItemOrder


@dataclass(frozen=True, slots=True)
class _MenuEntry:
    name: str
    usd_path: str


class VacCreateMenu:
    _DEFAULT_VAC_PARENT_ICON = "eye.svg"
    _STAGE_SCOPE = "omni.kit.widget.stage"
    _GLOBAL_SCOPES = ("omni.kit.viewport.window", "omni.kit.viewport")
    _CONTEXT_SECTIONS = ("CREATE", "MENU")
    _CONTEXT_PATH_KEYS = (
        "hovered_prim_path",
        "hover_prim_path",
        "clicked_prim_path",
        "target_prim_path",
        "prim_path",
        "path",
    )
    _CONTEXT_PATH_LIST_KEYS = (
        "hovered_prim_paths",
        "prim_paths",
        "prim_list",
        "selected_prim_paths",
        "selection",
    )

    def __init__(
        self,
        ext_id: str,
        *,
        enable_create_menu: bool = True,
        enable_stage_context_menu: bool = True,
        enable_global_context_menu: bool = True,
    ) -> None:
        self._ext_id = ext_id
        self._enable_create_menu = enable_create_menu
        self._enable_stage_context_menu = enable_stage_context_menu
        self._enable_global_context_menu = enable_global_context_menu
        self._material_menu_list = []
        self._stage_context_subs = []
        self._global_context_subs = []

        ext_manager = omni.kit.app.get_app().get_extension_manager()
        self._ext_path = ext_manager.get_extension_path(ext_id)
        self._vac_parent_icon = self._resolve_vac_parent_icon()

        self._build_menu()

    def _resolve_vac_parent_icon(self) -> str:
        svg_icon_path = os.path.join(self._ext_path, "data", "icon_automation.svg")
        if os.path.exists(svg_icon_path):
            return svg_icon_path

        png_icon_path = os.path.join(self._ext_path, "data", "icon.png")
        if os.path.exists(png_icon_path):
            return png_icon_path

        return self._DEFAULT_VAC_PARENT_ICON

    def _build_menu(self) -> None:
        menu_entries = self._load_menu_config()

        if self._enable_create_menu:
            sub_menu = [
                MenuItemDescription(
                    name=entry.name,
                    onclick_fn=self._make_create_onclick(entry.usd_path, entry.name),
                )
                for entry in menu_entries
            ]

            self._material_menu_list = [
                MenuItemDescription(
                    name="VAC",
                    glyph=self._vac_parent_icon,
                    appear_after=["Xform", MenuItemOrder.LAST],
                    sub_menu=sub_menu,
                )
            ]
            omni.kit.menu.utils.add_menu_items(self._material_menu_list, "Create")

        if self._enable_stage_context_menu or self._enable_global_context_menu:
            self._add_context_menu_items(menu_entries)

    def _add_context_menu_items(self, menu_entries: list[_MenuEntry]) -> None:
        context_sub_menu = []

        for entry in menu_entries:
            onclick_fn = self._make_context_onclick(entry.usd_path, entry.name)

            context_sub_menu.append(
                {
                    "name": entry.name,
                    "onclick_fn": onclick_fn,
                    "show_fn": self._always_show_fn,
                }
            )

        stage_menu = None
        global_menu = None

        if self._enable_stage_context_menu:
            stage_menu = {
                "name": {"VAC": context_sub_menu},
                "glyph": self._vac_parent_icon,
                "icon": self._vac_parent_icon,
                "show_fn": self._always_show_fn,
            }

        if self._enable_global_context_menu:
            global_menu = {
                "name": {"VAC": context_sub_menu},
                "glyph": self._vac_parent_icon,
                "icon": self._vac_parent_icon,
                "show_fn": self._always_show_fn,
            }

        self._register_context_menus(stage_menu, global_menu)

    def _register_context_menus(self, stage_menu: dict[str, Any] | None, global_menu: dict[str, Any] | None) -> None:
        if stage_menu is None and global_menu is None:
            return

        for section in self._CONTEXT_SECTIONS:
            stage_registered = False
            global_registered = False

            if stage_menu is not None:
                stage_registered = self._register_stage_menu(stage_menu, section)

            if global_menu is not None:
                global_registered = self._register_global_menu_with_fallback(global_menu, section)

            if stage_registered or global_registered:
                carb.log_info(f"Registered VAC context menus via {section} section")
                return

        carb.log_warn("VAC context menu registration failed for CREATE and MENU sections")

    def _register_stage_menu(self, menu_def: dict[str, Any], section: str) -> bool:
        try:
            sub = omni.kit.context_menu.add_menu(menu_def, section, self._STAGE_SCOPE)
        except Exception as exc:
            carb.log_warn(f"VAC {section} stage registration failed: {exc}")
            return False

        if sub is None:
            return False

        self._stage_context_subs.append(sub)
        return True

    def _register_global_menu_with_fallback(self, menu_def: dict[str, Any], section: str) -> bool:
        sub = self._register_global_menu(menu_def, section)
        if sub is None:
            return False
        self._global_context_subs.append(sub)
        return True

    def _register_global_menu(self, menu_def: dict[str, Any], section: str):
        for scope in self._GLOBAL_SCOPES:
            try:
                sub = omni.kit.context_menu.add_menu(menu_def, section, scope)
                carb.log_info(f"Registered VAC global context menu in section '{section}' with scope '{scope}'")
                return sub
            except Exception:
                pass
        carb.log_warn(f"Unable to register VAC global context menu in section '{section}'")
        return None

    @staticmethod
    def _always_show_fn(_objects: dict[str, Any]) -> bool:
        return True

    def _load_menu_config(self) -> list[_MenuEntry]:
        config_path = os.path.join(self._ext_path, "data", "vac", "menu_items.json")
        if not os.path.exists(config_path):
            carb.log_warn(f"VAC menu config not found: {config_path}")
            return []

        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                content = json.load(handle)
        except Exception as exc:
            carb.log_error(f"Failed to read VAC menu config '{config_path}': {exc}")
            return []

        if not isinstance(content, list):
            carb.log_error(f"VAC menu config must be a list: {config_path}")
            return []

        entries: list[_MenuEntry] = []
        for index, value in enumerate(content):
            entry = self._parse_menu_entry(index, value)
            if entry is not None:
                entries.append(entry)

        return entries

    def _parse_menu_entry(self, index: int, value: Any) -> _MenuEntry | None:
        if not isinstance(value, dict):
            carb.log_warn(f"Skipping invalid menu entry at index {index}: expected object")
            return None

        if "name" not in value or "usd_path" not in value:
            carb.log_warn(f"Skipping invalid menu entry at index {index}: missing name/usd_path")
            return None

        display_name = str(value.get("name", "VAC Item")).strip() or "VAC Item"
        usd_path = str(value.get("usd_path", "")).strip()
        if not usd_path:
            carb.log_warn(f"Skipping invalid menu entry at index {index}: empty usd_path")
            return None

        return _MenuEntry(name=display_name, usd_path=usd_path)

    def _create_from_usd(self, relative_usd_path: str, display_name: str, context_payload: Any | None = None) -> None:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            carb.log_warn("Cannot create VAC item: no open stage")
            return

        source_path = os.path.join(self._ext_path, relative_usd_path)
        if not os.path.exists(source_path):
            carb.log_error(f"VAC source file not found: {source_path}")
            return

        base_name = self._sanitize_name(display_name)
        parent_path = self._get_target_parent_path(stage, context_payload)
        prim_path = self._get_next_prim_path(stage, f"{parent_path}/{base_name}")

        prim = stage.DefinePrim(prim_path, "Xform")
        prim.GetReferences().AddReference(source_path)

        omni.usd.get_context().get_selection().set_selected_prim_paths([prim_path], True)
        carb.log_info(f"Created VAC prim '{prim_path}' from '{relative_usd_path}'")

    def _make_create_onclick(self, relative_usd_path: str, display_name: str):
        def _onclick(*_args, **_kwargs):
            self._create_from_usd(relative_usd_path, display_name)

        return _onclick

    def _make_context_onclick(self, relative_usd_path: str, display_name: str):
        def _onclick(*args, **kwargs):
            context_payload = self._extract_context_payload(args, kwargs)
            self._create_from_usd(relative_usd_path, display_name, context_payload)

        return _onclick

    def _extract_context_payload(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any | None:
        for key in ("objects", "context", "payload"):
            if key in kwargs:
                return kwargs[key]

        if args:
            return args[0] if len(args) == 1 else args

        if kwargs:
            return kwargs

        return None

    def _get_target_parent_path(self, stage, context_payload: Any | None) -> str:
        candidate_paths: list[str] = []

        candidate_paths.extend(self._extract_context_prim_paths(context_payload))

        if not candidate_paths:
            selection = omni.usd.get_context().get_selection().get_selected_prim_paths()
            candidate_paths.extend(str(path) for path in selection if path)

        for path in candidate_paths:
            target_path = self._resolve_target_parent_path(stage, path)
            if target_path is not None:
                return target_path

        world = stage.GetPrimAtPath("/World")
        if world and world.IsValid():
            return "/World"
        return "/"

    def _extract_context_prim_paths(self, context_payload: Any | None) -> list[str]:
        if context_payload is None:
            return []

        candidate_paths: list[str] = []
        self._collect_prim_paths(context_payload, candidate_paths, depth=0)

        seen: set[str] = set()
        unique_paths: list[str] = []
        for path in candidate_paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)
        return unique_paths

    def _collect_prim_paths(self, value: Any, candidate_paths: list[str], depth: int) -> None:
        if value is None or depth > 6:
            return

        normalized_path = self._normalize_prim_path(value)
        if normalized_path is not None:
            candidate_paths.append(normalized_path)
            return

        if isinstance(value, dict):
            for key in self._CONTEXT_PATH_KEYS:
                if key in value:
                    self._collect_prim_paths(value[key], candidate_paths, depth + 1)

            for key in self._CONTEXT_PATH_LIST_KEYS:
                if key in value:
                    self._collect_prim_paths(value[key], candidate_paths, depth + 1)

            for key, nested in value.items():
                key_lower = str(key).lower()
                if "prim" in key_lower or key_lower.endswith("_path"):
                    self._collect_prim_paths(nested, candidate_paths, depth + 1)

            for nested in value.values():
                if isinstance(nested, (dict, list, tuple, set)):
                    self._collect_prim_paths(nested, candidate_paths, depth + 1)

        elif isinstance(value, (list, tuple, set)):
            for item in value:
                self._collect_prim_paths(item, candidate_paths, depth + 1)

    def _normalize_prim_path(self, value: Any) -> str | None:
        if hasattr(value, "GetPath"):
            try:
                value = value.GetPath()
            except Exception:
                return None

        if not isinstance(value, str):
            return None

        path = value.strip()
        if not path:
            return None

        if path.startswith("Sdf.Path("):
            match = re.search(r"['\"]([^'\"]+)['\"]", path)
            if not match:
                return None
            path = match.group(1)

        if "." in path:
            path = path.split(".", 1)[0]

        if not path.startswith("/"):
            return None

        path = path.rstrip("/") or "/"
        if path == "/":
            return None

        return path

    def _resolve_target_parent_path(self, stage, candidate_path: str) -> str | None:
        prim = stage.GetPrimAtPath(candidate_path)
        if not prim or not prim.IsValid() or prim.IsPseudoRoot():
            return None

        if hasattr(prim, "IsInstanceProxy") and prim.IsInstanceProxy():
            parent = prim.GetParent()
            if parent and parent.IsValid() and not parent.IsPseudoRoot():
                return str(parent.GetPath())
            return None

        return str(prim.GetPath())

    def _get_next_prim_path(self, stage, base_path: str) -> str:
        if not stage.GetPrimAtPath(base_path).IsValid():
            return base_path

        index = 1
        while True:
            candidate = f"{base_path}_{index:02d}"
            if not stage.GetPrimAtPath(candidate).IsValid():
                return candidate
            index += 1

    def _sanitize_name(self, value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value.strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        return cleaned or "VAC"

    def shutdown(self) -> None:
        if self._material_menu_list:
            omni.kit.menu.utils.remove_menu_items(self._material_menu_list, "Create")
        self._material_menu_list = []

        self._release_subscriptions(self._stage_context_subs, "stage")
        self._release_subscriptions(self._global_context_subs, "global")

    def _release_subscriptions(self, subscriptions: list[Any], scope: str) -> None:
        for sub in subscriptions:
            try:
                sub.release()
            except Exception as exc:
                carb.log_warn(f"Failed to release VAC {scope} context menu subscription: {exc}")
        subscriptions.clear()
