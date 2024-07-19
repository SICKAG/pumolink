from pxr import Usd, Gf, UsdGeom
import omni.kit.raycast.query as rq
from injector import inject
from sick.modellink.core.modellink_manager import linked, on_pause, on_play, on_stop, on_update, usd_attr

import carb


@linked
class Switchable:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self.enable_light(False)


    @usd_attr("vac:on", param_name="enabled")
    def enable_light(self, enabled: bool):
        rel = self.prim.GetRelationship("vac:switch")
        for target in rel.GetForwardedTargets():
            attr = self.stage.GetAttributeAtPath(target)
            attr.Set(UsdGeom.Tokens.inherited if enabled else UsdGeom.Tokens.invisible)


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

        transform = Gf.Transform()
        transform.SetMatrix(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))

        origin = transform.GetTranslation()
        direction = transform.GetMatrix().TransformDir(Gf.Vec3d(1, 0, 0))

        ray = rq.Ray(origin, direction, 0, 100)
        self.rqi.submit_raycast_query(ray, self.on_ray)
