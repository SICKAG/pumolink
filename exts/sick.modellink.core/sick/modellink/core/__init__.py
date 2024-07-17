from .extension import *
from .modellink_manager import *
from .model_event_registry import *
import injector
import carb.events


PREFIX = "sick.modellink.core"

MODELLINK_ADDED = carb.events.type_from_string(f"{PREFIX}.MODELLINK_ADDED")
MODELLINK_REMOVED = carb.events.type_from_string(f"{PREFIX}.MODELLINK_REMOVED")
MODELLINK_ACTIVATOR_ADDED = carb.events.type_from_string(f"{PREFIX}.MODELLINK_ACTIVATOR_ADDED")
MODELLINK_ACTIVATOR_REMOVED = carb.events.type_from_string(f"{PREFIX}.MODELLINK_ACTIVATOR_REMOVED")
MODELLINK_ACTIVATOR_ENABLED = carb.events.type_from_string(f"{PREFIX}.MODELLINK_ACTIVATOR_ENABLED")
MODELLINK_ACTIVATOR_DISABLED = carb.events.type_from_string(f"{PREFIX}.MODELLINK_ACTIVATOR_DISABLED")


def get_event_stream() -> carb.events.IEventStream:
    return ModelLinkManager().get_event_stream()


def get_model_event_registry() -> ModelEventRegistry:
    return ModelEventRegistry.instance