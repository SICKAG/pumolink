from pxr import Usd
import omni.kit.raycast.query as rq
from injector import inject
from sick.modellink.core.modellink_manager import linked, on_update

import carb


@linked
class LightBarrierClass:

    @inject
    def __init__(self, its_prim: Usd.Prim, stage: Usd.Stage):
        self.rqi = rq.acquire_raycast_query_interface()
        self._its_prim = its_prim
        self._stage = stage

    def send_signal(self, enabled: bool):
        rel = self._its_prim.GetRelationship("stateReceiver")
        for target in rel.GetForwardedTargets():
            prim = self._stage.GetPrimAtPath(target)
            attr = prim.GetAttribute("vac:on")
            attr.Set(enabled)

    def on_ray(self, ray: rq.Ray, hit: rq.RayQueryResult):
        self.send_signal(hit.valid)
        #if hit.valid:
        #    carb.log_info(f"Hit: {hit.get_target_usd_path()} from {self._its_prim.GetPath()} Distance: {hit.hit_t}")
        #else:
        #    carb.log_info("Miss")

    @on_update(editmode=True)
    def update(self, prim: Usd.Prim):
        from pxr import Gf, UsdGeom
        transform = Gf.Transform()
        transform.SetMatrix(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))

        origin = transform.GetTranslation()
        direction = transform.GetMatrix().TransformDir(Gf.Vec3d(1, 0, 0))

        ray = rq.Ray(origin, direction, 0, 100)
        self.rqi.submit_raycast_query(ray, self.on_ray)