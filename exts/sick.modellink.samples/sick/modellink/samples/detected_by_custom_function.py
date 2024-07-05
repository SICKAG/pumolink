from pxr import Usd
from carb import log_info
from sick.modellink.core.modellink_manager import linked

""" This sample demonstrates how to create a ModelLink using a custom function to detect the prim.
    The function 'my_custom_function' is used to detect the prim to be linked.
    The function should return True if the prim should be linked, otherwise False.
    In this example, the prim is linked if it has an attribute 'id' with value 42.

    To see it in action:
    - Drag and drop an .usda file contained in '/data/testfiles/' into the stage
"""


def my_custom_function(prim: Usd.Prim):
    return prim.HasAttribute('id') and prim.GetAttribute('id').Get() == 42


@linked(my_custom_function)
class MyCustomHandler:

    def __init__(self) -> None:
        log_info("Detected by Function sample Initialized!")
