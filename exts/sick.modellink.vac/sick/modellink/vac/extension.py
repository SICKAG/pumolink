import omni.ext
from sick.modellink.core import ModelLinkManager
from sick.modellink.vac.menu import VacCreateMenu


class ModelLinkVACExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("[sick.modellink.vac] sick  modellink_vac startup")
        self._create_menu = VacCreateMenu(ext_id)
        ModelLinkManager().update_links()

    def on_shutdown(self):
        print("[sick.modellink.vac] sick  modellink_vac shutdown")
        if hasattr(self, "_create_menu") and self._create_menu is not None:
            self._create_menu.shutdown()
            self._create_menu = None
        ModelLinkManager().discard_namespace('sick.modellink.vac')
