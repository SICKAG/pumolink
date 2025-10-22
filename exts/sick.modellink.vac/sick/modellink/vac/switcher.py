from pxr import Usd
from injector import inject
from sick.modellink.core.modellink_manager import linked, usd_attr


@linked
class Switcher:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self.current_state = 0

    @usd_attr("vac:select", param_name="select_index")
    def select_target(self, select_index: int):
        rel = self.prim.GetRelationship("vac:target")
        targets = rel.GetForwardedTargets()
        if 0 <= select_index < len(targets):
            target = targets[select_index]
            attr = self.stage.GetAttributeAtPath(target)
            self.current_state = (self.current_state + 1) % 2  # Toggle state
            attr.Set(self.current_state, Usd.TimeCode.Default())