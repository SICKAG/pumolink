from pxr import Usd
from injector import inject
from sick.modellink.core.modellink_manager import linked, on_update, usd_attr

import carb
import paho.mqtt.client as mqtt


@linked
class MqttCoupler:

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self._set_params()
        self.pending_value = None  # For thread-safe updates
        # Initialize MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(self.broker, self.port, 60)
        self.mqtt_client.subscribe(self.topic)
        self.mqtt_client.loop_start()

    def _set_params(self):
        # Load MQTT configuration attributes
        broker_attr = self.prim.GetAttribute("vac:broker")
        port_attr = self.prim.GetAttribute("vac:port")
        topic_attr = self.prim.GetAttribute("vac:topic")
        self.broker = broker_attr.Get() if broker_attr else "localhost"
        self.port = port_attr.Get() if port_attr else 1883
        self.topic = topic_attr.Get() if topic_attr else "vac/default"

    @usd_attr("vac:broker;vac:port")
    def _update_params(self):
        self._set_params()
        #if self.mqtt_client:
        #    self.mqtt_client.disconnect()
        #    self.mqtt_client.connect(self.broker, self.port, 60)
        #    self.mqtt_client.subscribe(self.topic)

    def on_message(self, client, userdata, message):
        try:
            payload_str = message.payload.decode().strip('[]')
            value = float(payload_str)
            self.pending_value = value  # Store for main thread
        except ValueError:
            carb.log_warn(f"Invalid MQTT message payload: {message.payload}")

    @on_update(editmode=True)
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