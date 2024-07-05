from carb import log_info
from pxr import Usd, Gf
from injector import inject
from sick.modellink.core.modellink_manager import linked, on_pause, on_play, on_stop, on_update
from .geo_tools import setRotate


""" This sample demonstrates how to use events
    The prim will rotate when the 'play' button is pressed

    To see it in action:
    - create a new 'Cone' prim (not 'Mesh') in the stage
    - press the 'play' button to see the events being called
"""


@linked('Cone')
class MyEventsHandler:

    def __init__(self) -> None:
        log_info("Handle Events sample initialized!")
        self.rot = 0.0

    @on_update
    def update(self, prim: Usd.Prim):
        self.rot += 0.5
        setRotate(prim, Gf.Vec3f(0.0, self.rot, 0.0))

    @on_play
    def play(self):
        log_info("Rotation started!")

    @on_pause
    def pause(self):
        log_info("Rotation paused!")

    @on_stop
    def stop(self, prim: Usd.Prim):
        log_info("Rotation stopped!")
        self.rot = 0.0
        setRotate(prim, Gf.Vec3f(0.0, self.rot, 0.0))
