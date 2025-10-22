from pxr import Usd, UsdGeom
from injector import inject
from sick.modellink.core.modellink_manager import linked, usd_attr


@linked
class Enabler:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self.enable_light(False)

    @usd_attr("vac:on", param_name="enabled")
    def enable_light(self, enabled: bool):
        rel = self.prim.GetRelationship("vac:target")
        for target in rel.GetForwardedTargets():
            attr = self.stage.GetAttributeAtPath(target)
            attr.Set(UsdGeom.Tokens.inherited if enabled else UsdGeom.Tokens.invisible)