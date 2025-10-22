from pxr import Usd
from injector import inject
from sick.modellink.core.modellink_manager import linked, usd_attr


@linked
class Coupler:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self._set_params()

    def _set_params(self):
        # Load invariant attributes
        format_attr = self.prim.GetAttribute("vac:format")
        bool_values_attr = self.prim.GetAttribute("vac:bool_values")
        factor_attr = self.prim.GetAttribute("vac:factor")
        threshold_attr = self.prim.GetAttribute("vac:threshold")
        self.output_format = format_attr.Get() if format_attr else "real"
        bool_values = bool_values_attr.Get() if bool_values_attr else (0.0, 1.0)
        self.bool_false_value, self.bool_true_value = bool_values
        self.factor = factor_attr.Get() if factor_attr else 1.0
        self.threshold = threshold_attr.Get() if threshold_attr else 0.0

    @usd_attr("vac:format;vac:bool_values;vac:factor;vac:threshold")
    def _update_params(self):
        self._set_params()

    def _set_output(self, output_value):
        if isinstance(output_value, bool):
            attr_name = "vac:on"
        elif isinstance(output_value, int):
            attr_name = "vac:select"
        else:  # float
            attr_name = "vac:value"
        rel = self.prim.GetRelationship("stateReceiver")
        for target in rel.GetForwardedTargets():
            prim = self.stage.GetPrimAtPath(target)
            attr = prim.GetAttribute(attr_name)
            if attr:
                attr.Set(output_value, Usd.TimeCode.Default())

    @usd_attr("vac:on", param_name="input_bool")
    def convert_bool(self, input_bool: bool):
        if self.output_format == "bool":
            output_value = input_bool
        elif self.output_format == "int":
            output_value = 1 if input_bool else 0
        else:  # real
            output_value = self.bool_true_value if input_bool else self.bool_false_value
        self._set_output(output_value)

    @usd_attr("vac:select", param_name="input_int")
    def convert_int(self, input_int: int):
        if self.output_format == "bool":
            output_value = input_int != 0
        elif self.output_format == "int":
            output_value = input_int
        else:  # real
            output_value = float(input_int) * self.factor
        self._set_output(output_value)

    @usd_attr("vac:value", param_name="input_real")
    def convert_real(self, input_real: float):
        if self.output_format == "bool":
            output_value = input_real > self.threshold
        elif self.output_format == "int":
            output_value = int(input_real * self.factor)
        else:  # real
            output_value = input_real
        self._set_output(output_value)