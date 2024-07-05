import omni.ext
from sick.modellink.core import ModelLinkManager


class ModelLinkSamplesExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("[sick.modellink.samples] sick  modellink_samples startup")
        ModelLinkManager().update_links()

    def on_shutdown(self):
        print("[sick.modellink.samples] sick  modellink_samples shutdown")
        ModelLinkManager().discard_namespace('sick.modellink.samples')
