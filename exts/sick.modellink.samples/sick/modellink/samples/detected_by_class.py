from carb import log_info
from sick.modellink.core.modellink_manager import linked

""" This sample demonstrates how to create a ModelLink using an information inside the prim
    This information can be stored in the prim's metadata either in 'assetInfo' or in 'customData'.
    The key used to store the information is 'linkedClass', the value is the name of the class to be linked.
    e.g.
        assetInfo = { 
            string linkedClass = "SensorClass"
        }

    To see it in action:
    - Drag and drop an .usda file contained in '/data/testfiles/' into the stage
"""

@linked
class MyClassHandler:

    def __init__(self) -> None:
        log_info("Detected by Class sample Initialized!")
