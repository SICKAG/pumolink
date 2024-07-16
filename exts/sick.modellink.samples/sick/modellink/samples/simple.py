from carb import log_info
from sick.modellink.core.modellink_manager import linked, on_update, usd_attr

""" This sample demonstrates how to create a simple ModelLink.
    To see it in action:
    - create a new 'Cube' prim (not 'Mesh') in the stage
    - press the 'play' button to see the omniverse update event is calling the 'update' function
    - change the value of the 'size' attribute of the 'Cube' prim (in the Property Window)
      to see the 'attr_size_change' function being called
"""


@linked('Cube', enabled=False)
class CubeHandler:

    def __init__(self) -> None:
        log_info("Simple Sample Initialized!")

    @on_update
    def update(self):
        log_info("update called")

    @usd_attr('size')
    def attr_size_change(self, size: float):
        log_info(f"attribute '.size' changed, new value is: {str(size)}")
