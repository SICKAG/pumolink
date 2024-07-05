from abc import ABC
from typing import Callable
import carb.events


def type_for(typename: str) -> int:
    return carb.events.type_from_string(typename)


class EventProvider(ABC):
    """ Base class for event providers.
    """

    def remap_types(self, type_mapping: dict[int, str]) -> dict[int, int]:
        """Use this method to remap the types of events that this provider can provide. The keys of the dictionary should be the original event types, and the values should be the new event types.

        Args:
            type_mapping (dict[int, str]): A dictionary mapping the original event types to the new event types.

        Returns:
            dict[int, int]: A dictionary mapping the original event types to the new event types.
        """
        new_map = {}
        for k, v in type_mapping.items():
            new_map[int(k)] = type_for(v)
        return new_map

    def get_types(self):
        """ Returns the types of events that this provider can provide.
        """
        pass

    def activate(self, func: Callable):
        """ Activates the provider. When an event is received, the function will be called with the event type as argument.

        Args:
            func (Callable): The function to call when an event is received. The function shoulds look like "def func(event_type: int):"
        """
        pass

    def deactivate(self):
        """ Deactivates the provider. No more events should be received after this is called.
        """
        pass


class EventStreamProvider(EventProvider):
    """ Provides events from omniverse kit event streams. 
        The event types are remapped to the types specified in the type_mapping dictionary.
    """
    def __init__(self, event_stream, type_mapping: dict[int, str] = {}, use_push: bool = False) -> None:
        self._event_stream = event_stream
        self._type_mapping: dict[int, int] = self.remap_types(type_mapping)
        self._use_push = use_push
        self._subscription = None

    def get_types(self):
        return self._type_mapping.values()

    def activate(self, func: Callable):
        def _event(e: carb.events.IEvent):
            event_type = e.type
            if event_type in self._type_mapping:
                func(self._type_mapping[event_type])

        if self._use_push:
            self._subscription = self._event_stream.create_subscription_to_push(_event)
        else:
            self._subscription = self._event_stream.create_subscription_to_pop(_event)

    def deactivate(self):
        if self._subscription:
            self._subscription.unsubscribe()
            self._subscription = None
