import omni.ext
from sick.modellink.core import ModelLinkManager
from sick.modellink.extras.event_providers import PhysXEventProvider
from sick.modellink.core.model_event_registry import ModelEventRegistry


class ModelLinkExtrasExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("[sick.modellink.extras] sick  modellink_ext startup")
        ModelEventRegistry.instance.add_event_provider(PhysXEventProvider())


    def on_shutdown(self):
        print("[sick.modellink.extras] sick  modellink_ext shutdown")
