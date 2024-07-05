from abc import ABC
from typing import Callable
import omni
import carb.events
import omni.physx as physx
from sick.modellink.core import EventProvider, type_for


class PhysXEventProvider(EventProvider):
    """ Provides events from the PhysX simulation.
    """
    def __init__(self) -> None:
        self._physx = physx.acquire_physx_interface()
        self._type = type_for('step')
        self._subscription = None

    def get_types(self):
        return [self._type]

    def activate(self, func: Callable):

        def _event(e: carb.events.IEvent):
            func(self._type)

        self._subscription = self._physx.subscribe_physics_step_events(_event)

    def deactivate(self):
        if self._subscription:
            self._subscription = None
