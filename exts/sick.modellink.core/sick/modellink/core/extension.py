import omni.ext
from sick.modellink.core.model_event_registry import ModelEventRegistry
from sick.modellink.core.modellink_manager import ModelLinkManager


class ModelLinkCoreExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("[sick.modellink.core] sick  modellink startup")
        manager = ModelLinkManager()
        self.controller = ModelEventRegistry(manager)


    def on_shutdown(self):
        print("[sick.modellink.core] sick  modellink shutdown")
        self.controller.clear()
        ModelLinkManager().clear()
