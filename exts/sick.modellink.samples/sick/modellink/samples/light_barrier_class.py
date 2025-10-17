from pxr import Usd, Gf, UsdGeom
import omni.kit.raycast.query as rq
from injector import inject
from sick.modellink.core.modellink_manager import linked, on_pause, on_play, on_stop, on_update, usd_attr

import carb
import paho.mqtt.client as mqtt

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


@linked
class Mover:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
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

    @usd_attr("vac:value", param_name="value")
    def move(self, value: float):
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
                ops = xform.GetOrderedXformOps()
                if ops:
                    translate_op = ops[0]
                    translate_op.Set(position, Usd.TimeCode.Default())


@linked
class Rotor:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
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

    @usd_attr("vac:value", param_name="value")
    def rotate(self, value: float):
        #carb.log_info(f"Rotor received value: {value}")
        # Calculate rotation
        scaled_value = value * self.factor + self.offset
        if self.clamp:
            scaled_value = max(self.range_min, min(self.range_max, scaled_value))
        rotation = Gf.Rotation(self.axis, scaled_value)

        # Apply to targets
        rel = self.prim.GetRelationship("vac:target")
        for target in rel.GetForwardedTargets():
            target_prim = self.stage.GetPrimAtPath(target)
            xform = UsdGeom.Xformable(target_prim)
            if xform:
                ops = xform.GetOrderedXformOps()
                if len(ops) > 1:
                    rotate_op = ops[1]
                    rotate_op.Set(Gf.Quatf(rotation.GetQuat()), Usd.TimeCode.Default())


@linked
class Coupler:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
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


@linked
class MqttCoupler:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        # Load MQTT configuration attributes
        broker_attr = self.prim.GetAttribute("vac:broker")
        port_attr = self.prim.GetAttribute("vac:port")
        topic_attr = self.prim.GetAttribute("vac:topic")
        self.broker = broker_attr.Get() if broker_attr else "localhost"
        self.port = port_attr.Get() if port_attr else 1883
        self.topic = topic_attr.Get() if topic_attr else "vac/default"
        self.pending_value = None  # For thread-safe updates
        # Initialize MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(self.broker, self.port, 60)
        self.mqtt_client.subscribe(self.topic)
        self.mqtt_client.loop_start()

    def on_message(self, client, userdata, message):
        try:
            payload_str = message.payload.decode().strip('[]')
            value = float(payload_str)
            self.pending_value = value  # Store for main thread
        except ValueError:
            carb.log_warn(f"Invalid MQTT message payload: {message.payload}")

    @on_update()
    def update(self, prim: Usd.Prim):
        if self.pending_value is not None:
            self._set_output(self.pending_value)
            self.pending_value = None

    def _set_output(self, output_value):
        rel = self.prim.GetRelationship("stateReceiver")
        for target in rel.GetForwardedTargets():
            prim = self.stage.GetPrimAtPath(target)
            attr = prim.GetAttribute("vac:value")
            if attr:
                attr.Set(output_value, Usd.TimeCode.Default())

    @usd_attr("vac:value", param_name="value")
    def publish_value(self, value: float):
        if self.mqtt_client:
            self.mqtt_client.publish(self.topic, str(value))

    @usd_attr("vac:topic", param_name="new_topic")
    def set_topic(self, new_topic: str):
        old_topic = self.topic
        self.topic = new_topic
        if self.mqtt_client:
            self.mqtt_client.unsubscribe(old_topic)
            self.mqtt_client.subscribe(new_topic)


@linked
class WaveGenerator:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
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

    @on_update()
    def update(self, prim: Usd.Prim):
        import math
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
