from pxr import Usd
from injector import inject
from sick.modellink.core.modellink_manager import linked, on_update, usd_attr

import math


@linked
class WaveGenerator:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self._set_params()

    def _set_params(self):
        # Load invariant attributes
        amplitude_attr = self.prim.GetAttribute("vac:amplitude")
        frequency_attr = self.prim.GetAttribute("vac:frequency")
        phase_attr = self.prim.GetAttribute("vac:phase")
        type_attr = self.prim.GetAttribute("vac:type")
        self.amplitude = amplitude_attr.Get() if amplitude_attr else 1.0
        self.frequency = frequency_attr.Get() if frequency_attr else 1.0
        self.phase = phase_attr.Get() if phase_attr else 0.0
        self.wave_type = type_attr.Get() if type_attr else "sin"
        self.time = 0.0

    @usd_attr("vac:amplitude;vac:frequency;vac:phase;vac:type")
    def _update_params(self):
        self._set_params()

    @on_update()
    def update(self, prim: Usd.Prim):
        self.time += 0.016  # Assume ~60 FPS, dt=1/60
        t = self.time * self.frequency + self.phase
        if self.wave_type == "sin":
            value = self.amplitude * math.sin(t)
        elif self.wave_type == "square":
            value = self.amplitude * (1 if math.sin(t) > 0 else -1)
        elif self.wave_type == "triangle":
            value = self.amplitude * (2 / math.pi) * math.asin(math.sin(t))
        elif self.wave_type == "sawtooth":
            value = self.amplitude * (2 * (t / (2 * math.pi) - math.floor(0.5 + t / (2 * math.pi))))
        else:
            value = 0.0

        # Send via stateReceiver
        rel = self.prim.GetRelationship("stateReceiver")
        for target in rel.GetForwardedTargets():
            target_prim = self.stage.GetPrimAtPath(target)
            attr = target_prim.GetAttribute("vac:value")
            if attr:
                attr.Set(value, Usd.TimeCode.Default())