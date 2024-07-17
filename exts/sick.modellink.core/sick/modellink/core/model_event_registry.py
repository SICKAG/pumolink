import carb
import omni
from pxr import Usd, Tf
import sick.modellink.core
from .event_providers import EventProvider, EventStreamProvider
from .modellink_manager import ModelLinkManager


class ModelEventRegistry:
    """ This class is responsible for registering and dispatching events.
        It dispatches events to the ModelLinkManager from different sources like USD, PhysX, etc.
        For that it uses EventProviders. EventProviders are classes that provide events from different sources.
        EventProvider translates the events from the original source to a common event type.
    """

    instance = None

    def __init__(self, manager: ModelLinkManager):

        ModelEventRegistry.instance = self
        self._stage = None
        self._listener = None
        self._manager = manager
        self._context = omni.usd.get_context()
        self._stage_listener = self._context.get_stage_event_stream().create_subscription_to_pop(self._on_stage_event)
        self._event_providers = []
        self._register_event_providers()
        self._handle_stage_open()
        self._modellink_listener = ModelLinkManager().get_event_stream().create_subscription_to_pop(self._on_modellink_event)

    ############################
    # Public methods
    ############################
    def add_event_provider(self, provider: EventProvider):
        self._event_providers.append(provider)

    def clear(self):
        self._clear_usd_events()
        self._stage_listener = None

    ############################
    # Private methods
    ############################
    def _on_modellink_event(self, e: carb.events.IEvent):
        if e.type == int(sick.modellink.core.MODELLINK_ADDED):
            carb.log_info(f"MODELLINK_ADDED {e.payload}")
            self._activate_event_providers()
        elif e.type == int(sick.modellink.core.MODELLINK_REMOVED):
            carb.log_info(f"MODELLINK_REMOVED {e.payload}")
            self._activate_event_providers()
        elif e.type == int(sick.modellink.core.MODELLINK_ACTIVATOR_ADDED):
            carb.log_info(f"MODELLINK_ACTIVATOR_ADDED {e.payload}")
        elif e.type == int(sick.modellink.core.MODELLINK_ACTIVATOR_REMOVED):
            carb.log_info(f"MODELLINK_ACTIVATOR_REMOVED {e.payload}")
        elif e.type == int(sick.modellink.core.MODELLINK_ACTIVATOR_ENABLED):
            carb.log_info(f"MODELLINK_ACTIVATOR_ENABLED {e.payload}")
        elif e.type == int(sick.modellink.core.MODELLINK_ACTIVATOR_DISABLED):
            carb.log_info(f"MODELLINK_ACTIVATOR_DISABLED {e.payload}")


    def _is_event_type_used(self, provider):
        types_provider: set[int] = provider.get_types()
        types_registered: set[int] = self._manager.get_registered_events()
        return not types_registered.isdisjoint(types_provider)

    def _on_stage_event(self, e: carb.events.IEvent):
        if e.type == int(omni.usd.StageEventType.OPENED):
            self._handle_stage_open()
        elif e.type == int(omni.usd.StageEventType.CLOSED):
            self._handle_stage_close()


    def _handle_stage_open(self):
        self._context = omni.usd.get_context()
        stage = self._context.get_stage()   # TODO: check why usdrt is not working if scene reloaded
        self._stage = stage

        self._manager.link_entire_stage(self._stage)

        self._setup_usd_events(stage)


    def _handle_stage_close(self):
        self._clear_usd_events()
        self._manager.clear_links()
        self._stage = None


    def _setup_usd_events(self, stage):
        self._clear_usd_events()
        self._stage = stage
        self._listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._handle_usd_event, self._stage)
        # self._activate_event_providers()

    def _on_event(self, event):
        self._manager.dispatch_events(event)

    def _deactivate_event_providers(self):
        for provider in self._event_providers:
            provider.deactivate()

    def _activate_event_providers(self):
        for provider in self._event_providers:
            provider.deactivate()
            if self._is_event_type_used(provider):
                provider.activate(self._on_event)


    def _register_event_providers(self ):
        app = omni.kit.app.get_app()
        self.add_event_provider(EventStreamProvider(app.get_update_event_stream(), {0: "update"}))
        self.add_event_provider(EventStreamProvider(app.get_pre_update_event_stream(), {0: "pre_update"}))
        timeline_stream = omni.timeline.get_timeline_interface().get_timeline_event_stream()
        self.add_event_provider(EventStreamProvider(timeline_stream,
                                                    {omni.timeline.TimelineEventType.PLAY: "play",
                                                     omni.timeline.TimelineEventType.PAUSE: "pause",
                                                     omni.timeline.TimelineEventType.STOP: "stop"}))
        # self.add_event_provider(PhysXEventProvider())
        # get_pre_update_event_stream()
        # self.add_event_provider(EventStreamProvider(omni.kit.app.get_app().get_message_bus_event_stream(), {0: "message_bus"}))
        # self.add_event_provider(EventStreamProvider(omni.kit.app.get_app().get_selection_event_stream(), {0: "selection"}))
        # self.add_event_provider(EventStreamProvider(omni.kit.app.get_app().get_input_event_stream(), {0: "input"}))
        # self.add_event_provider(EventStreamProvider(omni.kit.app.get_app().get_app_event_stream(), {0: "app"}))
        # self.add_event_provider(EventStreamProvider(omni.kit.app.get_app().get_app_window_event_stream(), {0: "app_window"}))

    def _clear_usd_events(self):
        if self._listener:
            self._listener.Revoke()

        self._stage = None
        self._deactivate_event_providers()

    def _handle_usd_event(self, objects_changed, sender):

        if sender is None or sender != self._stage:
            return

        for resync_path in objects_changed.GetResyncedPaths():
            if resync_path.IsPrimPath():
                prim = self._stage.GetPrimAtPath(resync_path)
                if prim and prim.IsActive():
                    self._manager.create_new_link(prim)
                if not prim:
                    self._manager.remove_link(resync_path)

        for changed_path in objects_changed.GetChangedInfoOnlyPaths():
            if changed_path.IsPropertyPath():
                self._manager.property_changed(changed_path)

