from pxr import Usd
from injector import inject
from sick.modellink.core.modellink_manager import linked, usd_attr


@linked(cluster="VAC")
class Quantizer:
    """
    Quantizes input values to discrete steps.
    Maps continuous input values to discrete output values based on step size.
    """

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self._set_params()

    def _set_params(self):
        # Load invariant attributes
        step_size_attr = self.prim.GetAttribute("vac:step_size")
        offset_attr = self.prim.GetAttribute("vac:offset")
        self.step_size = step_size_attr.Get() if step_size_attr else 1.0
        self.offset = offset_attr.Get() if offset_attr else 0.0
        self.value = self.prim.GetAttribute("vac:value").Get() if self.prim.GetAttribute("vac:value") else 0.0

    @usd_attr("vac:step_size;vac:offset")
    def _update_params(self):
        self._set_params()
        self._quantize(self.value)

    def _quantize(self, value: float) -> None:
        """Quantize input value to discrete steps and send to targets"""
        if self.step_size <= 0.0:
            quantized_value = value
        else:
            # Quantize: round to nearest multiple of step_size, then apply offset
            quantized_value = round((value - self.offset) / self.step_size) * self.step_size + self.offset

        # Send via stateReceiver
        rel = self.prim.GetRelationship("stateReceiver")
        for target in rel.GetForwardedTargets():
            target_prim = self.stage.GetPrimAtPath(target)
            attr = target_prim.GetAttribute("vac:value")
            if attr:
                attr.Set(quantized_value, Usd.TimeCode.Default())

    @usd_attr("vac:value", param_name="value")
    def quantize(self, value: float) -> None:
        self._quantize(value)
