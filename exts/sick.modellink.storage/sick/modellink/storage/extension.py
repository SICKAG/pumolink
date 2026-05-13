import carb
import inspect
import omni.ext
import omni.usd
import sick.modellink.core as ml

from .shared_storage import ModelLinkSharedStorage, ModelLinkStorageScope, build_scope


def storage_owner(clazz=None):
    def _decorate(target):
        owner = clazz or target
        setattr(target, "__modellink_storage_owner__", owner)
        return target

    return _decorate


class ModelLinkStorageService:
    def __init__(self, shared_storage: ModelLinkSharedStorage):
        self._shared_storage = shared_storage

    def scope_for(self, prim, detector_reference: str) -> ModelLinkStorageScope:
        return build_scope(prim, detector_reference, self._shared_storage)

    def storage_for(self, prim, detector_reference: str) -> dict:
        return self.scope_for(prim, detector_reference).storage

    def storage_for_link(self, prim, clazz) -> dict:
        detector_reference = _resolve_detector_reference(prim, clazz)
        if not detector_reference:
            detector_reference = clazz.__name__
        return self.storage_for(prim, detector_reference)

    def storage_for_current_link(self, prim) -> dict:
        clazz = _infer_calling_class()
        if clazz is None:
            raise RuntimeError("Could not infer calling class. Use storage_for_link(prim, YourClass).")
        return self.storage_for_link(prim, clazz)

    def storage_for_instance_link(self, prim, instance) -> dict:
        clazz = getattr(instance.__class__, "__modellink_storage_owner__", instance.__class__)
        return self.storage_for_link(prim, clazz)


def _infer_calling_class():
    frame = inspect.currentframe()
    try:
        caller = frame.f_back if frame else None
        while caller:
            if "self" in caller.f_locals:
                return caller.f_locals["self"].__class__
            if "cls" in caller.f_locals and isinstance(caller.f_locals["cls"], type):
                return caller.f_locals["cls"]
            caller = caller.f_back
    finally:
        del frame
    return None


def _normalize_class_refs(value) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        return [part.strip() for part in value.split(';') if part.strip()]

    try:
        values = list(value)
    except TypeError:
        values = [value]

    return [str(item).strip() for item in values if str(item).strip()]


def _linked_class_refs(prim) -> list[str]:
    refs = []
    for key in ("linkedClasses", "linkedClass"):
        for value in (prim.GetCustomDataByKey(key), prim.GetAssetInfoByKey(key)):
            for item in _normalize_class_refs(value):
                if item not in refs:
                    refs.append(item)
    return refs


def _matches_activator(prim, activator) -> bool:
    if activator.detectType == "schema":
        return prim.GetTypeName() == activator.reference

    if activator.detectType == "class":
        return activator.reference in _linked_class_refs(prim)

    if activator.detectType == "custom":
        return bool(activator.detectFunc(prim))

    return False


def _resolve_detector_reference(prim, clazz) -> str | None:
    manager = ml.ModelLinkManager()
    for activator in manager.get_activators():
        if activator.enabled and activator.clazz is clazz and _matches_activator(prim, activator):
            return activator.reference
    return None


class ModelLinkStorageExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("[sick.modellink.storage] startup")
        self._shared_storage = ModelLinkSharedStorage()
        self._service = ModelLinkStorageService(self._shared_storage)

        manager = ml.ModelLinkManager()
        manager.bind_instance(ModelLinkSharedStorage, self._shared_storage)
        manager.bind_instance(ModelLinkStorageService, self._service)
        self._subscription = ml.get_event_stream().create_subscription_to_push(self._on_modellink_event)

    def on_shutdown(self):
        print("[sick.modellink.storage] shutdown")
        self._subscription = None
        self._shared_storage.clear()

    def _on_modellink_event(self, event: carb.events.IEvent):
        if event.type != int(ml.MODELLINK_ADDED):
            return

        payload = dict(event.payload) if event.payload else {}
        prim_path = payload.get("prim_path")
        class_name = payload.get("class_name")
        if not prim_path or not class_name:
            return

        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsValid():
            return

        manager = ml.ModelLinkManager()
        for candidate in manager.get_activators():
            if candidate.enabled and candidate.clazz.__name__ == class_name and _matches_activator(prim, candidate):
                self._service.scope_for(prim, candidate.reference)
