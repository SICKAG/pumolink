import math
from pxr import Usd
from injector import inject
from sick.modellink.core.modellink_manager import linked, on_update, usd_attr


@linked(cluster="VAC")
class Tweener:
    """
    Applies easing functions to trigger transitions with smooth animations.
    On trigger edge (rising or falling), starts an easing animation over a configured duration.
    If the trigger edge occurs during easing, reverses direction over the elapsed time.
    """

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self.last_trigger = False
        self.elapsed_time = 0.0
        self.easing_forward = True
        self.is_easing = False
        self._set_params()

    def _set_params(self):
        # Load invariant attributes
        easing_type_attr = self.prim.GetAttribute("vac:easing_type")
        duration_attr = self.prim.GetAttribute("vac:duration")
        self.easing_type = easing_type_attr.Get() if easing_type_attr else "linear"
        self.duration = duration_attr.Get() if duration_attr else 1.0
        if self.duration <= 0.0:
            self.duration = 1.0

    @usd_attr("vac:easing_type;vac:duration")
    def _update_params(self):
        self._set_params()

    def _ease_linear(self, t: float) -> float:
        """Linear interpolation"""
        return t

    def _ease_in_quad(self, t: float) -> float:
        """Quadratic ease-in"""
        return t * t

    def _ease_out_quad(self, t: float) -> float:
        """Quadratic ease-out"""
        return t * (2.0 - t)

    def _ease_in_out_quad(self, t: float) -> float:
        """Quadratic ease-in-out"""
        if t < 0.5:
            return 2.0 * t * t
        else:
            return -1.0 + (4.0 - 2.0 * t) * t

    def _ease_in_cubic(self, t: float) -> float:
        """Cubic ease-in"""
        return t * t * t

    def _ease_out_cubic(self, t: float) -> float:
        """Cubic ease-out"""
        t = t - 1.0
        return t * t * t + 1.0

    def _ease_in_out_cubic(self, t: float) -> float:
        """Cubic ease-in-out"""
        if t < 0.5:
            return 4.0 * t * t * t
        else:
            t = 2.0 * t - 2.0
            return 0.5 * t * t * t + 1.0

    def _ease_in_sine(self, t: float) -> float:
        """Sine ease-in"""
        return 1.0 - math.cos((t * math.pi) / 2.0)

    def _ease_out_sine(self, t: float) -> float:
        """Sine ease-out"""
        return math.sin((t * math.pi) / 2.0)

    def _ease_in_out_sine(self, t: float) -> float:
        """Sine ease-in-out"""
        return -(math.cos(math.pi * t) - 1.0) / 2.0

    def _get_eased_value(self, t: float) -> float:
        """Apply easing function to normalized time value [0, 1]"""
        # Clamp to [0, 1]
        t = max(0.0, min(1.0, t))

        # Apply easing function
        if self.easing_type == "linear":
            return self._ease_linear(t)
        elif self.easing_type == "ease_in_quad":
            return self._ease_in_quad(t)
        elif self.easing_type == "ease_out_quad":
            return self._ease_out_quad(t)
        elif self.easing_type == "ease_in_out_quad":
            return self._ease_in_out_quad(t)
        elif self.easing_type == "ease_in_cubic":
            return self._ease_in_cubic(t)
        elif self.easing_type == "ease_out_cubic":
            return self._ease_out_cubic(t)
        elif self.easing_type == "ease_in_out_cubic":
            return self._ease_in_out_cubic(t)
        elif self.easing_type == "ease_in_sine":
            return self._ease_in_sine(t)
        elif self.easing_type == "ease_out_sine":
            return self._ease_out_sine(t)
        elif self.easing_type == "ease_in_out_sine":
            return self._ease_in_out_sine(t)
        else:
            return t

    def _send_value(self, value: float) -> None:
        """Send eased value to stateReceiver targets"""
        rel = self.prim.GetRelationship("stateReceiver")
        for target in rel.GetForwardedTargets():
            target_prim = self.stage.GetPrimAtPath(target)
            attr = target_prim.GetAttribute("vac:value")
            if attr:
                attr.Set(value, Usd.TimeCode.Default())

    @on_update()
    def update(self, prim: Usd.Prim) -> None:
        """Update easing state and check for trigger edges"""
        # Get current trigger state
        trigger_attr = self.prim.GetAttribute("vac:trigger")
        current_trigger = trigger_attr.Get() if trigger_attr else False

        # Check for trigger edge (rising or falling)
        if current_trigger != self.last_trigger:
            # Trigger edge detected
            if self.is_easing:
                # If we're already easing, reverse direction with remaining time
                self.easing_forward = not self.easing_forward
                # Swap direction but keep elapsed_time to use it as new duration
                self.elapsed_time = self.duration - self.elapsed_time
            else:
                # Start new easing
                self.is_easing = True
                self.elapsed_time = 0.0
                self.easing_forward = current_trigger  # True if rising edge, False if falling edge

            self.last_trigger = current_trigger

        # Update easing progress
        if self.is_easing:
            self.elapsed_time += 0.016  # Assume ~60 FPS

            # Calculate progress (0.0 to 1.0)
            progress = min(1.0, self.elapsed_time / self.duration)

            # Get eased value
            eased = self._get_eased_value(progress)

            # Map to 0.0 -> 1.0 if forward, 1.0 -> 0.0 if backward
            if self.easing_forward:
                output_value = eased
            else:
                output_value = 1.0 - eased

            self._send_value(output_value)

            # Check if easing is complete
            if progress >= 1.0:
                self.is_easing = False
                # Ensure we're at the target value
                target_value = 1.0 if self.easing_forward else 0.0
                self._send_value(target_value)
