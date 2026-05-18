from carb import log_info
from injector import inject
from pxr import Usd

from sick.modellink.core.modellink_manager import linked, on_destroy, on_update
from sick.modellink.storage import ModelLinkStorageService, storage_owner

""" This sample demonstrates how to use sick.modellink.storage.

    It keeps shared state per (primID + detector reference). The state remains stable
    when a prim is renamed or moved, as long as primID remains stable.

    To see it in action:
    - create a new 'Cube' prim (not 'Mesh') in the stage
    - press play: update() increments a shared counter
    - duplicate or move/rename the prim and check logs
"""


@storage_owner()
@linked("Sphere")
class CubeStorageHandler:

    @inject
    def __init__(self, prim: Usd.Prim, storage_service: ModelLinkStorageService) -> None:
        self._storage = storage_service.storage_for_instance_link(prim, self)
        self._storage.setdefault("updates", 0)
        log_info(f"Storage sample initialized, updates={self._storage['updates']}")

    @on_update
    def update(self):
        self._storage["updates"] += 1
        if self._storage["updates"] % 30 == 0:
            log_info(f"Storage sample updates={self._storage['updates']}")

    @on_destroy
    def destroy(self):
        log_info(f"Storage sample destroyed, final updates={self._storage['updates']}")
