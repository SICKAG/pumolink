import inspect
from typing import Callable, Iterator
from carb import events
from omni import timeline, usd
from pxr import Usd, Sdf
from injector import Injector, get_bindings, inject, noninjectable
import sick.modellink.core
from sick.modellink.core.event_providers import type_for
from .omniverse_di_module import OmniverseDIModule


def on_update(*args, editmode: bool = False):
    """ Decorator to link a method to the update event.
        The method is called every frame.
        e.g.

        1)  @on_update
            def your_method():
                pass

        2)  @on_update(editmode=True)
            def your_method():
                pass

        Your method may also have a parameter of an injected type, e.g.:
        3)  @on_update
            def your_method(prim: Usd.Prim):
                pass    

    Args:
        editmode (bool, optional): If True, the method is called even if the timeline is paused. Defaults to False.
    """
    no_args = len(args) == 1 and inspect.isfunction(args[0])
    _editmode = not no_args and editmode

    def inner(f):
        manager = ModelLinkManager()
        manager.register_event(f, "update", _editmode)
        return f
    return inner(args[0]) if no_args else inner


def on_pre_update(*args, editmode: bool = False):
    """ Decorator to link a method to the preupdate event.
        The method is called every frame before the update event.
        e.g.

        1)  @on_pre_update
            def your_method():
                pass

        2)  @on_pre_update(editmode=True)
            def your_method():
                pass

        Your method may also have a parameter of an injected type, e.g.:
        3)  @on_pre_update
            def your_method(prim: Usd.Prim):
                pass

    Args:
        editmode (bool, optional): If True, the method is called even if the timeline is paused. Defaults to False.
    """
    no_args = len(args) == 1 and inspect.isfunction(args[0])
    _editmode = not no_args and editmode

    def inner(f):
        manager = ModelLinkManager()
        manager.register_event(f, "pre_update", _editmode)
        return f
    return inner(args[0]) if no_args else inner


def on_destroy(f):
    """ Decorator to link a method to the destroy event.
    """
    manager = ModelLinkManager()
    manager.register_event(f, "destroy")
    return f


def on_play(f):
    """ Decorator to link a method to the play event.
    """
    manager = ModelLinkManager()
    manager.register_event(f, "play", True)
    return f


def on_pause(f):
    """ Decorator to link a method to the pause event.
    """
    manager = ModelLinkManager()
    manager.register_event(f, "pause", True)
    return f


def on_stop(f):
    """ Decorator to link a method to the stop event.
    """
    manager = ModelLinkManager()
    manager.register_event(f, "stop", True)
    return f


def on_step(f):
    """ Decorator to link a method to the 'Physics' step event.
        To use this decorator, the modellink.extras extension must be enabled.        
    """
    manager = ModelLinkManager()
    manager.register_event(f, "step")
    return f


def on_event(_id: str | int):
    """ Decorator to link a method to a custom event.
        instead of using 'on_play' etc. you can also use this decorator by using the event id 'play'.

    Args:
        _id (str | int): any string or integer to identify the event, any string is converted to an integer using modellink.core.type_for
    """
    def inner(f):
        manager = ModelLinkManager()
        manager.register_event(f, _id)
        return f
    return inner


# decorator to link a method to a prim attribute
def usd_attr(path: str, param_name: str | None = None):
    """ Decorator to link a method to a prim attribute. The method is called when the attribute changes.
        The changed value is passed to the method as argument with the name of the attribute
        or the name specified in param_name.
    Args:
        path (str): the name of the attribute of the prim to be observed
        param_name (str | None, optional): the name of the parameter to be passed to the function. Defaults to the path.
    """
    def inner(f):
        manager = ModelLinkManager()
        manager.add_usd_attr(f, path, param_name)
        return f
    return inner


def linked(*args, enabled: bool = True):
    """ Decorator to link a class to a prim. The correct prim is recognized using 'detection'. 
    The detection can be specified as an argument to the decorator.

    1)  @linked or @linked()
        If no argument is provided, the class name is used as reference.
        In this case, the prim must contain the entry linkedClass='yourClass' in customData or assetInfo (Metadata of the prim)

        e.g.
            def Xform "Sensor"
            (
                customData = {
                    string linkedClass = "SensorClass"
                }
            )
            {
            }

    2)  @linked('YourSchema')
        If a string is provided, the schema name is used as reference.
        The prim must have the schema 'YourSchema' to be linked to the class.

    3)  @linked(yourFunction)
        If a function is provided, the function is called with the prim as argument. 
        If the function returns True, the class is linked to the prim.

        e.g.
            def yourFunction(prim):
                return prim.HasAttribute('yourAttribute')
    """
    no_args = len(args) == 1 and inspect.isclass(args[0])
    rule = None if no_args or len(args) == 0 else args[0]

    def inner(c):
        if inspect.isclass(c):
            activator = ModelLinkActivator(c, rule, enabled)
            manager = ModelLinkManager()
            manager.add_activator(activator)
        return c

    if no_args:
        return inner(args[0])  # type: ignore
    else:
        return inner


class ModelLinkActivator():
    """ Represents the class and its members that are linked to any Usd Prim.
        ModelLinkActivator behaves like a class, while the ModelLink behaves like an instance of the class.

    Args:
        clazz (class): the class to be linked
        rule (str | Callable, optional): the detection rule.
            If a string is provided, the schema name is used as reference.
            If a function is provided, the function is called with the prim as argument.
            If nothing is provided, the class name is used as reference. 
            In this case, the prim must contain the entry linkedClass='yourClass' in customData or assetInfo (Metadata of the prim)
    """

    type_class = 'class'
    type_schema = 'schema'
    type_custom = 'custom'

    def __init__(self, clazz, rule, enabled=True) -> None:
        self.enabled = enabled
        self.members = Members()
        self.clazz = clazz
        self.detectFunc = self._default_detect
        if not rule:
            self.detectType = ModelLinkActivator.type_class
            self.reference = str(clazz.__name__)
        elif type(rule) is str:
            self.detectType = ModelLinkActivator.type_schema
            self.reference = rule
        else:
            self.detectType = ModelLinkActivator.type_custom
            self.detectFunc = rule
            self.reference = f"{rule.__name__};{clazz.__name__}"

    #############################
    # Public methods
    #############################
    def set_members(self, members):
        self.members = members

    def call_attr_changed(self, changed_path: Sdf.Path, instance, prim):
        attr = changed_path.name

        value = prim.GetAttribute(attr).Get()
        if attr in self.members.attr:
            self._call(self.members.attr[attr], instance, prim, value)

    def call_event(self, event_type: int, instance, prim):
        if event_type in self.members.event:
            playing = timeline.get_timeline_interface().is_playing()
            for event in self.members.event[event_type]:
                if playing or bool(event.__meta_editmode__):
                    self._call(event, instance, prim, None)

    #############################
    # Private methods
    #############################
    def _call(self, func, instance, prim, value):
        if not bool(func.__bindings__):
            func(instance)
            return
        if hasattr(func, '__meta_prim_params__'):
            kargs = {k: prim for k in func.__meta_prim_params__}
        else:
            kargs = {}
        if value is not None and hasattr(func, '__meta_value_param__'):
            kargs[func.__meta_value_param__] = value

        injector = ModelLinkManager()._injector
        injector.call_with_injection(func, instance, kwargs=kargs)

    def _default_detect(self, *args) -> bool:
        return True


class ModelLink:
    """ Represents a link between a specific prim and an instance of a specific class.

    Args:
        instance (object): the instance of the class
        prim (Usd.Prim): the prim to be linked
        activator (ModelLinkActivator): the activator that detected the link
    """
    def __init__(self, instance, prim, activator):
        self._instance = instance
        self._prim = prim
        self._activator: ModelLinkActivator = activator

    def destroy(self):
        pass

    def property_changed(self, changed_path):
        self._activator.call_attr_changed(changed_path, self._instance, self._prim)

    def dispatch_event(self, event_type: int):
        self._activator.call_event(event_type, self._instance, self._prim)


class Members:
    # Helper for moving members to activator
    def __init__(self) -> None:
        self.attr = {}
        self.event = {}


class ModelLinkManager:
    """ Singleton to manage ModelLinks and ModelLinkActivators
        It can be accessed by: ModelLinkManager()
        It is also responsible for dispatching events to the ModelLinks and for injecting parameters
    """
    def __new__(cls):
        # singleton, only one instance of ModelLinkManager
        if not hasattr(cls, 'instance'):
            cls.instance = super(ModelLinkManager, cls).__new__(cls)
            cls.instance._init()
        return cls.instance

    def __init__(self) -> None:
        # do not initialize anything here, __new__ calls _init(self) instead
        pass

    #############################
    # Public methods
    #############################
    def get_event_stream(self) -> events.IEventStream:
        return self._modellink_event_stream

    def add_activator(self, activator: ModelLinkActivator):
        self._activators[activator.detectType][activator.reference] = activator
        self._move_members_to_activator(activator.clazz.__name__, activator)
        self._event_cache = None
        self._fire_modellink_event(sick.modellink.core.MODELLINK_ACTIVATOR_ADDED,
                                   payload={"detector": activator.detectType,
                                            "reference": activator.reference,
                                            "class_name": activator.clazz.__name__})


    def set_class_enabled(self, clazz, enabled: bool, keep_links: bool = False):
        activator = self._find_activator_by_class_name(clazz.__name__)
        if activator:
            activator.enabled = enabled

            if enabled:
                self.update_links()
            elif not keep_links:
                self._remove_links_for_activator(activator)

            self._fire_modellink_event(sick.modellink.core.MODELLINK_ACTIVATOR_ENABLED if enabled
                                       else sick.modellink.core.MODELLINK_ACTIVATOR_DISABLED,
                                       payload={"detector": activator.detectType,
                                                "reference": activator.reference,
                                                "class_name": activator.clazz.__name__})


    def add_usd_attr(self, func, path: str, param_name: str | None):
        if param_name is None:
            param_name = path.split('.')[-1]
        name = self._extract_class_name(func)
        if name not in self._members:
            self._members[name] = Members()

        self._prepare_injection(func, param_name)
        self._members[name].attr[path] = func

    def register_event(self, func, event_id: str | int, editmode: bool = False):
        if type(event_id) is str:
            event_type = type_for(event_id)
        else:
            event_type = event_id

        name = self._extract_class_name(func)
        if name not in self._members:
            self._members[name] = Members()

        if event_type not in self._members[name].event:
            self._members[name].event[event_type] = []

        self._prepare_injection(func)
        func.__meta_editmode__ = editmode
        self._members[name].event[event_type].append(func)

    def get_registered_events(self) -> set[int]:
        if not self._event_cache:
            self._event_cache = set()
            for activator in self.get_activators():
                for event_type in activator.members.event.keys():
                    self._event_cache.add(event_type)
        return self._event_cache


    def discard_namespace(self, namespace):
        for _map in self._activators.values():
            for key, value in list(_map.items()):
                if value.clazz.__module__.startswith(namespace):
                    self._discard_intern(value, _map, key)

    def discard_class(self, clazz):
        for _map in self._activators.values():
            for key, value in list(_map.items()):
                if value.clazz is clazz:
                    self._discard_intern(value, _map, key)

    def clear_links(self):
        for key in list(self._links.keys()):
            self.remove_link(key)

    def clear(self):
        self.clear_links()
        self._clear_activators()
        self._clear_members()

    def create_new_link(self, prim: Usd.Prim):
        activator = self._find_activator(prim)
        if activator and activator.enabled:
            instance = self._create(activator.clazz, prim)  # also handles injection
            self._links[prim.GetPrimPath()] = ModelLink(instance, prim, activator)
            self._fire_modellink_event(sick.modellink.core.MODELLINK_ADDED,
                                       payload={"prim_path": prim.GetPrimPath(),
                                                "class_name": activator.clazz.__name__})

    def remove_link(self, resync_path):
        link = self._links.pop(resync_path, None)
        if link:
            link.destroy()
            self._fire_modellink_event(sick.modellink.core.MODELLINK_REMOVED,
                                       payload={"prim_path": resync_path,
                                                "class_name": link._activator.clazz.__name__})

    def property_changed(self, changed_path):
        prim_path = changed_path.GetPrimPath()
        link = self._links.get(prim_path, None)
        if link:
            link.property_changed(changed_path)

    def dispatch_events(self, event_type: int):
        for link in self._links.values():
            if link:
                link.dispatch_event(event_type)

    def get_activators(self) -> Iterator[ModelLinkActivator]:
        for activator in self._activators.values():
            for _, value in activator.items():
                yield value

    def get_modellinks(self) -> Iterator[ModelLink]:
        for link in self._links.values():
            yield link

    def update_links(self, renew_all=False, stage: Usd.Stage | None = None):

        if not stage:
            stage = usd.get_context().get_stage()

        if stage:
            for prim in stage.Traverse():
                if renew_all or prim.GetPath() not in self._links:
                    self.create_new_link(prim)

    def link_entire_stage(self, stage):
        self.update_links(renew_all=True, stage=stage)

    #############################
    # Private methods
    #############################
    def _init(self) -> None:
        # initialize the ModelLinkManager, called by __new__
        # do all initialization here, do not call this method directly
        self._injector = Injector(OmniverseDIModule)
        self._activators = {
            'class': {},
            'schema': {},
            'custom': {}
        }
        self._members: dict[str, Members] = {}
        self._links: dict[str, ModelLink] = {}
        self._modellink_event_stream = events.acquire_events_interface().create_event_stream()
        self._event_cache = None

    def _fire_modellink_event(self, event_type: int, payload):
        self._modellink_event_stream.push(event_type, payload=payload)
        self._modellink_event_stream.pump()

    def _create(self, clazz, prim: Usd.Prim):
        func = clazz.__init__
        bindings = get_bindings(func)
        kargs = {}
        if bool(bindings): # special handling for Usd.Prim
            kargs = {k:prim for (k, v) in bindings.items() if v is Usd.Prim}

        return self._injector.create_object(clazz, kargs)

    def _extract_class_name(self, func: Callable) -> str:
        return func.__qualname__.split('.')[0]  # TODO: make it work for nested classes etc.

    def _prepare_injection(self, func, param_name: str | None = None):
        inject(func)
        bindings = get_bindings(func)
        if bool(bindings):
            prim_param_names = [k for (k, v) in bindings.items() if v is Usd.Prim]
            if param_name and param_name in bindings.keys():
                func.__meta_value_param__ = param_name
                names = prim_param_names + [param_name]
            else:
                names = prim_param_names

            noninjectable(*names)(func)
            func.__meta_prim_params__ = prim_param_names

    def _move_members_to_activator(self, class_name: str, activator: ModelLinkActivator | None = None):
        if class_name in self._members:
            members = self._members[class_name]
            activator = activator or self._find_activator_by_class_name(class_name)
            if activator:
                activator.set_members(members)
                del self._members[class_name]

    def _find_activator(self, prim: Usd.Prim):
        # first look for schema
        if bool(self._activators['schema']):
            schema = prim.GetTypeName()
            if schema in self._activators['schema']:
                return self._activators['schema'][schema]

        # second look for classlinks
        if bool(self._activators['class']):
            custom_data = prim.GetCustomDataByKey("linkedClass") or prim.GetAssetInfoByKey("linkedClass")
            if custom_data in self._activators['class']:
                return self._activators['class'][custom_data]

        # then look for custom
        if bool(self._activators['custom']):
            for activator in self._activators['custom'].values():
                if activator.detectFunc(prim):
                    return activator
        return None

    def _find_activator_by_class_name(self, name) -> ModelLinkActivator | None:
        for _map in self._activators.values():
            for key, value in _map.items():
                if value.clazz.__name__ == name:
                    return value
        return None

    def _remove_links_for_activator(self, activator: ModelLinkActivator):
        for key, link in list(self._links.items()):
            if link._activator is activator:
                self.remove_link(key)

    def _clear_activators(self):
        self._activators = {
            'class': {},
            'schema': {},
            'custom': {}
        }
        # TODO: event -> cleared all activators

    def _clear_members(self):
        self._members = {}

    def _discard_intern(self, value, _map, key):
        self._remove_links_for_activator(value)
        del _map[key]
        self._event_cache = None

        self._fire_modellink_event(sick.modellink.core.MODELLINK_ACTIVATOR_REMOVED,
                                   payload={"detector": value.detectType,
                                            "reference": value.reference,
                                            "class_name": value.clazz.__name__})
