from __future__ import annotations

import uuid
from dataclasses import dataclass

from pxr import Usd


PRIM_ID_KEYS = ("primID", "primId", "prim_id")
DEFAULT_PRIM_ID_KEY = "primID"


def _to_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _read_prim_id(prim: Usd.Prim) -> str | None:
    for key in PRIM_ID_KEYS:
        for value in (prim.GetCustomDataByKey(key), prim.GetAssetInfoByKey(key)):
            prim_id = _to_text(value)
            if prim_id:
                return prim_id
    for key in PRIM_ID_KEYS:
        attr = prim.GetAttribute(key)
        if attr and attr.IsValid():
            prim_id = _to_text(attr.Get())
            if prim_id:
                return prim_id
    return None


def ensure_prim_id(prim: Usd.Prim) -> str:
    prim_id = _read_prim_id(prim)
    if prim_id:
        return prim_id

    generated = str(uuid.uuid4())
    try:
        prim.SetCustomDataByKey(DEFAULT_PRIM_ID_KEY, generated)
        return generated
    except Exception:
        return str(prim.GetPrimPath())


@dataclass(frozen=True)
class ModelLinkStorageScope:
    prim_id: str
    detector_reference: str
    key: str
    storage: dict


class ModelLinkSharedStorage:
    def __init__(self) -> None:
        self._entries: dict[str, dict] = {}

    def get(self, key: str) -> dict:
        if key not in self._entries:
            self._entries[key] = {}
        return self._entries[key]

    def clear(self) -> None:
        self._entries.clear()


def build_scope(prim: Usd.Prim, detector_reference: str, shared_storage: ModelLinkSharedStorage) -> ModelLinkStorageScope:
    prim_id = ensure_prim_id(prim)
    key = f"{prim_id}::{detector_reference}"
    return ModelLinkStorageScope(
        prim_id=prim_id,
        detector_reference=detector_reference,
        key=key,
        storage=shared_storage.get(key),
    )
