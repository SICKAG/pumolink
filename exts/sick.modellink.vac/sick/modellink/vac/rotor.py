import carb
from pxr import Usd, Gf, UsdGeom
from injector import inject
from sick.modellink.core.modellink_manager import linked, usd_attr
from .utils import set_rotation_on_xform


@linked
class Rotor:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self._set_params()

    def _set_params(self):
        # Load invariant attributes
        axis_attr = self.prim.GetAttribute("vac:axis")
        offset_attr = self.prim.GetAttribute("vac:offset")
        range_attr = self.prim.GetAttribute("vac:range")
        factor_attr = self.prim.GetAttribute("vac:factor")
        clamp_attr = self.prim.GetAttribute("vac:clamp")
        self.axis = axis_attr.Get() if axis_attr else Gf.Vec3d(0, 0, 1)
        self.offset = offset_attr.Get() if offset_attr else 0.0
        self.range_min, self.range_max = range_attr.Get() if range_attr else (0.0, 360.0)
        self.factor = factor_attr.Get() if factor_attr else 1.0
        self.clamp = clamp_attr.Get() if clamp_attr else True
        #safe last value
        self.value = self.prim.GetAttribute("vac:value").Get() if self.prim.GetAttribute("vac:value") else 0.0


    @usd_attr("vac:axis;vac:offset;vac:range;vac:factor;vac:clamp")
    def _update_params(self):
        self._set_params()
        self._rotate(self.value)

    def _rotate(self, value: float):
        #carb.log_info(f"Rotor received value: {value}")
        # Calculate rotation
        scaled_value = value * self.factor + self.offset
        if self.clamp:
            scaled_value = max(self.range_min, min(self.range_max, scaled_value))
        rotation = Gf.Rotation(self.axis, scaled_value)
        #carb.log_info(f"Rotor calculated rotation: {rotation}")
        # Apply to targets
        rel = self.prim.GetRelationship("vac:target")
        for target in rel.GetForwardedTargets():
            target_prim = self.stage.GetPrimAtPath(target)
            xform = UsdGeom.Xformable(target_prim)
            if xform:
                set_rotation_on_xform(xform, rotation)

    @usd_attr("vac:value", param_name="value")
    def rotate(self, value: float):
        self._rotate(value)
        