from pxr import Usd
from injector import inject
from sick.modellink.core.modellink_manager import linked, on_update, usd_attr


@linked(cluster="VAC")
class Timer:
    """
    Countdown timer controlled by a start signal.
    Starts counting down when vac:start becomes True.
    When duration expires, automatically resets vac:start to False.
    Supports optional retriggering (allowing restart during countdown).
    """

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self.last_time = 0.0
        self.remaining_time = 0.0
        self.is_running = False
        self.last_start_state = False
        self._set_params()

    def _set_params(self):
        # Load configuration attributes
        duration_attr = self.prim.GetAttribute("vac:duration")
        allow_retrigger_attr = self.prim.GetAttribute("vac:allow_retrigger")
        self.duration = duration_attr.Get() if duration_attr else 1.0
        self.allow_retrigger = allow_retrigger_attr.Get() if allow_retrigger_attr else True
        if self.duration <= 0.0:
            self.duration = 1.0

    @usd_attr("vac:duration;vac:allow_retrigger")
    def _update_params(self):
        self._set_params()

    def _send_value(self, value: float) -> None:
        """Send remaining time to stateReceiver targets"""
        rel = self.prim.GetRelationship("stateReceiver")
        for target in rel.GetForwardedTargets():
            target_prim = self.stage.GetPrimAtPath(target)
            attr = target_prim.GetAttribute("vac:value")
            if attr:
                attr.Set(value, Usd.TimeCode.Default())

    def _stop_timer(self):
        """Stop timer and reset start flag"""
        self.is_running = False
        self.remaining_time = 0.0
        self._send_value(0.0)
        # Reset start flag
        start_attr = self.prim.GetAttribute("vac:start")
        if start_attr:
            start_attr.Set(False, Usd.TimeCode.Default())

    @on_update()
    def update(self, prim: Usd.Prim) -> None:
        """Called on each frame to manage timer countdown"""
        # Get current time from stage
        current_time = self.stage.GetTimeCodesPerSecond()
        
        # Get start flag
        start_attr = self.prim.GetAttribute("vac:start")
        is_started = start_attr.Get() if start_attr else False

        # Check for start flag edge
        if is_started and not self.last_start_state:
            # Rising edge - start the timer
            self.is_running = True
            self.remaining_time = self.duration
            self.last_time = current_time
        elif is_started and self.last_start_state and self.allow_retrigger and self.is_running:
            # Retrigger: restart timer if allowed and already running
            self.remaining_time = self.duration
            self.last_time = current_time
        elif not is_started and self.last_start_state:
            # Falling edge - stop the timer
            self.is_running = False

        self.last_start_state = is_started

        # Update timer if running
        if self.is_running:
            dt = current_time - self.last_time
            self.last_time = current_time
            self.remaining_time -= dt

            # Check if time expired
            if self.remaining_time <= 0.0:
                self._stop_timer()
            else:
                # Send remaining time
                self._send_value(self.remaining_time)


