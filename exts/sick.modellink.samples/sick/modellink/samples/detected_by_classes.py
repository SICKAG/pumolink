from carb import log_info
from sick.modellink.core.modellink_manager import linked

""" This sample demonstrates how to create multiple ModelLinks from a list in metadata.
    The key used to store the list is 'linkedClasses' and can be used in customData or assetInfo.

    Supported examples:
        customData = {
            string[] linkedClasses = ["MyClassesAHandler", "MyClassesBHandler"]
        }

        customData = {
            string linkedClasses = "MyClassesAHandler;MyClassesBHandler"
        }

    To see it in action:
    - Drag and drop an .usda file contained in '/data/testfiles/' into the stage
"""


@linked
class MyClassesAHandler:

    def __init__(self) -> None:
        log_info("Detected by Classes sample A initialized!")


@linked
class MyClassesBHandler:

    def __init__(self) -> None:
        log_info("Detected by Classes sample B initialized!")
