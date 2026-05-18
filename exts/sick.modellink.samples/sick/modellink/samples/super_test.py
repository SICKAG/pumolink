from carb import log_info
from pxr import Usd
from sick.modellink.core.modellink_manager import linked

"""Super sample that combines all detector types in one place.

Detectors covered:
- Schema detector via @linked("Cube")
- Class detector via @linked and metadata key `linkedClass`
- Classes detector via @linked and metadata key `linkedClasses`
- Custom detector via @linked(custom_function)

Quick stage setup examples:
- Schema detector: create a `Cube` prim.
- Class detector: set `customData.linkedClass = "SuperClassHandler"`.
- Classes detector: set
  `customData.linkedClasses = ["SuperClassesAHandler", "SuperClassesBHandler"]`
  or
  `customData.linkedClasses = "SuperClassesAHandler;SuperClassesBHandler"`.
- Custom detector: create any prim with attribute `id = 42`.
"""


def super_custom_detector(prim: Usd.Prim) -> bool:
    return prim.HasAttribute("id") and prim.GetAttribute("id").Get() == 42


@linked("Cube", cluster="super_test")
class SuperSchemaHandler:
    def __init__(self) -> None:
        log_info("[super_test] Schema detector linked (Cube)")


@linked(cluster="super_test")
class SuperClassHandler:
    def __init__(self) -> None:
        log_info("[super_test] Class detector linked (linkedClass)")


@linked(cluster="super_test")
class SuperClassesAHandler:
    def __init__(self) -> None:
        log_info("[super_test] Classes detector linked (A)")


@linked(cluster="super_test")
class SuperClassesBHandler:
    def __init__(self) -> None:
        log_info("[super_test] Classes detector linked (B)")


@linked(super_custom_detector, cluster="super_test")
class SuperCustomHandler:
    def __init__(self) -> None:
        log_info("[super_test] Custom detector linked (id == 42)")
