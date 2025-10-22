import omni.ext
from sick.modellink.core import ModelLinkManager


class ModelLinkVACExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("[sick.modellink.vac] sick  modellink_vac startup")
        ModelLinkManager().update_links()

    def on_shutdown(self):
        print("[sick.modellink.vac] sick  modellink_vac shutdown")
        ModelLinkManager().discard_namespace('sick.modellink.vac')
