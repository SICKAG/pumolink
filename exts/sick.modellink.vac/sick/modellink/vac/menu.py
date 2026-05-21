import json
import os
import re
from typing import Any

import carb
import omni.kit.app
import omni.kit.context_menu
import omni.kit.menu.utils
import omni.usd
from omni.kit.menu.utils import MenuItemDescription, MenuItemOrder


class VacCreateMenu:
    def __init__(self, ext_id: str) -> None:
        self._ext_id = ext_id
        self._material_menu_list = []
        self._stage_context_subs = []
        self._global_context_subs = []

        ext_manager = omni.kit.app.get_app().get_extension_manager()
        self._ext_path = ext_manager.get_extension_path(ext_id)

        self._build_menu()

    def _build_menu(self) -> None:
        menu_entries = self._load_menu_config()

        sub_menu = []
        for entry in menu_entries:
            display_name = str(entry.get("name", "VAC Item"))
            usd_path = str(entry.get("usd_path", "")).strip()
            if not usd_path:
                continue
            sub_menu.append(
                MenuItemDescription(
                    name=display_name,
                    onclick_fn=lambda path=usd_path, label=display_name: self._create_from_usd(path, label),
                )
            )

        self._material_menu_list = [
            MenuItemDescription(
                name="VAC",
                glyph="eye.svg",
                appear_after=["Xform", MenuItemOrder.LAST],
                sub_menu=sub_menu,
            )
        ]

        omni.kit.menu.utils.add_menu_items(self._material_menu_list, "Create")
        self._add_context_menu_items(menu_entries)

    def _add_context_menu_items(self, menu_entries: list[dict[str, Any]]) -> None:
        stage_sub_menu = []
        global_sub_menu = []
        for entry in menu_entries:
            display_name = str(entry.get("name", "VAC Item"))
            usd_path = str(entry.get("usd_path", "")).strip()
            if not usd_path:
                continue

            stage_sub_menu.append(
                {
                    "name": display_name,
                    "onclick_fn": self._make_context_onclick(usd_path, display_name),
                    "show_fn": self._stage_show_fn,
                }
            )
            global_sub_menu.append(
                {
                    "name": display_name,
                    "onclick_fn": self._make_context_onclick(usd_path, display_name),
                    "show_fn": self._global_show_fn,
                }
            )

        stage_menu = {
            "name": {"VAC": stage_sub_menu},
            "show_fn": self._stage_show_fn,
        }
        global_menu = {
            "name": {"VAC": global_sub_menu},
            "show_fn": self._global_show_fn,
        }

        stage_registered = False
        global_registered = False

        try:
            stage_sub = omni.kit.context_menu.add_menu(stage_menu, "CREATE", "omni.kit.widget.stage")
            if stage_sub is not None:
                self._stage_context_subs.append(stage_sub)
                stage_registered = True
        except Exception as exc:
            carb.log_warn(f"VAC CREATE stage registration failed: {exc}")

        global_sub = self._register_global_menu(global_menu, "CREATE")
        if global_sub is not None:
            self._global_context_subs.append(global_sub)
            global_registered = True

        if stage_registered or global_registered:
            carb.log_info("Registered VAC context menus via CREATE section")
            return

        try:
            stage_sub = omni.kit.context_menu.add_menu(stage_menu, "MENU", "omni.kit.widget.stage")
            if stage_sub is not None:
                self._stage_context_subs.append(stage_sub)
                stage_registered = True
        except Exception as exc:
            carb.log_warn(f"VAC MENU stage registration failed: {exc}")

        global_sub = self._register_global_menu(global_menu, "MENU")
        if global_sub is not None:
            self._global_context_subs.append(global_sub)
            global_registered = True

        if stage_registered or global_registered:
            carb.log_info("Registered VAC context menus via MENU section")
            return

        carb.log_warn("VAC context menu registration failed for CREATE and MENU sections")

    def _register_global_menu(self, menu_def: dict[str, Any], section: str):
        for scope in ("omni.kit.viewport.window", "omni.kit.viewport"):
            try:
                sub = omni.kit.context_menu.add_menu(menu_def, section, scope)
                carb.log_info(f"Registered VAC global context menu in section '{section}' with scope '{scope}'")
                return sub
            except Exception:
                pass
        carb.log_warn(f"Unable to register VAC global context menu in section '{section}'")
        return None

    def _stage_show_fn(self, objects: dict[str, Any]) -> bool:
        return True

    def _global_show_fn(self, _objects: dict[str, Any]) -> bool:
        return True

    def _load_menu_config(self) -> list[dict[str, Any]]:
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

        entries: list[dict[str, Any]] = []
        for index, value in enumerate(content):
            if not isinstance(value, dict):
                carb.log_warn(f"Skipping invalid menu entry at index {index}: expected object")
                continue
            if "name" not in value or "usd_path" not in value:
                carb.log_warn(f"Skipping invalid menu entry at index {index}: missing name/usd_path")
                continue
            entries.append(value)
        return entries

    def _create_from_usd(self, relative_usd_path: str, display_name: str, objects: dict[str, Any] | None = None) -> None:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            carb.log_warn("Cannot create VAC item: no open stage")
            return

        source_path = os.path.join(self._ext_path, relative_usd_path)
        if not os.path.exists(source_path):
            carb.log_error(f"VAC source file not found: {source_path}")
            return

        base_name = self._sanitize_name(display_name)
        parent_path = self._get_target_parent_path(stage, objects)
        prim_path = self._get_next_prim_path(stage, f"{parent_path}/{base_name}")

        prim = stage.DefinePrim(prim_path, "Xform")
        prim.GetReferences().AddReference(source_path)

        omni.usd.get_context().get_selection().set_selected_prim_paths([prim_path], True)
        carb.log_info(f"Created VAC prim '{prim_path}' from '{relative_usd_path}'")

    def _make_context_onclick(self, relative_usd_path: str, display_name: str):
        def _onclick(*args, **kwargs):
            objects = self._extract_context_objects(args, kwargs)
            self._create_from_usd(relative_usd_path, display_name, objects)

        return _onclick

    def _extract_context_objects(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any] | None:
        if "objects" in kwargs and isinstance(kwargs["objects"], dict):
            return kwargs["objects"]

        if "context" in kwargs and isinstance(kwargs["context"], dict):
            return kwargs["context"]

        for value in args:
            if isinstance(value, dict):
                return value

        return None

    def _get_target_parent_path(self, stage, objects: dict[str, Any] | None) -> str:
        candidate_paths: list[str] = []

        context_objects = objects or {}
        for key in ("prim_list", "prim_paths"):
            value = context_objects.get(key)
            if isinstance(value, list):
                candidate_paths.extend(str(path) for path in value if path)

        if not candidate_paths:
            selection = omni.usd.get_context().get_selection().get_selected_prim_paths()
            candidate_paths.extend(str(path) for path in selection if path)

        for path in candidate_paths:
            selected_prim = stage.GetPrimAtPath(path)
            if not selected_prim or not selected_prim.IsValid() or selected_prim.IsPseudoRoot():
                continue

            type_name = selected_prim.GetTypeName() or ""
            if type_name in {"Xform", "Scope"}:
                return str(selected_prim.GetPath())

            parent = selected_prim.GetParent()
            if parent and parent.IsValid() and not parent.IsPseudoRoot():
                return str(parent.GetPath())

        world = stage.GetPrimAtPath("/World")
        if world and world.IsValid():
            return "/World"
        return "/"

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

        for sub in self._stage_context_subs:
            try:
                sub.release()
            except Exception as exc:
                carb.log_warn(f"Failed to release VAC stage context menu subscription: {exc}")
        self._stage_context_subs = []

        for sub in self._global_context_subs:
            try:
                sub.release()
            except Exception as exc:
                carb.log_warn(f"Failed to release VAC global context menu subscription: {exc}")
        self._global_context_subs = []
