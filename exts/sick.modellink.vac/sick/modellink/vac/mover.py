from pxr import Usd, Gf, UsdGeom
from injector import inject
from sick.modellink.core.modellink_manager import linked, usd_attr
from .utils import set_translation_on_xform


@linked
class Mover:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self._set_params()

    def _set_params(self):
        # Load invariant attributes
        direction_attr = self.prim.GetAttribute("vac:direction")
        offset_attr = self.prim.GetAttribute("vac:offset")
        range_attr = self.prim.GetAttribute("vac:range")
        factor_attr = self.prim.GetAttribute("vac:factor")
        clamp_attr = self.prim.GetAttribute("vac:clamp")
        self.direction = direction_attr.Get() if direction_attr else Gf.Vec3d(1, 0, 0)
        self.offset = offset_attr.Get() if offset_attr else 0.0
        self.range_min, self.range_max = range_attr.Get() if range_attr else (0.0, 1.0)
        self.factor = factor_attr.Get() if factor_attr else 1.0
        self.clamp = clamp_attr.Get() if clamp_attr else True
        self.value = self.prim.GetAttribute("vac:value").Get() if self.prim.GetAttribute("vac:value") else 0.0

    @usd_attr("vac:direction;vac:offset;vac:range;vac:factor;vac:clamp")
    def _update_params(self):
        self._set_params()
        self._move(self.value)

    def _move(self, value: float):
        # Calculate position
        scaled_value = value * self.factor + self.offset
        if self.clamp:
            scaled_value = max(self.range_min, min(self.range_max, scaled_value))
        position = self.direction * scaled_value

        # Apply to targets
        rel = self.prim.GetRelationship("vac:target")
        for target in rel.GetForwardedTargets():
            target_prim = self.stage.GetPrimAtPath(target)
            xform = UsdGeom.Xformable(target_prim)
            if xform:
                set_translation_on_xform(xform, position)


    @usd_attr("vac:value", param_name="value")
    def move(self, value: float):
        self._move(value)
