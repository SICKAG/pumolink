from injector import Module, provider
import carb.events
import carb.settings
import carb.input
import omni.timeline
from omni.timeline._timeline import ITimeline
from omni.kit.app._app import IApp
from omni.appwindow._appwindow import IAppWindow
import omni.usd
from omni.usd._usd import Selection, UsdContext
from pxr import Usd, UsdUtils


class OmniverseDIModule(Module):

    @provider
    def provide_settings(self) -> carb.settings.ISettings:
        return carb.settings.get_settings()

    @provider
    def provide_timeline(self) -> ITimeline:
        return omni.timeline.get_timeline_interface()

    @provider
    def provide_input(self) -> carb.input.IInput:
        return carb.input.acquire_input_interface()

    @provider
    def provide_app(self) -> IApp:
        return omni.kit.app.get_app()

    @provider
    def provide_app_window(self) -> IAppWindow:
        return omni.kit.app.get_app().get_app_window()

    @provider
    def provide_usd_context(self) -> UsdContext:
        return omni.usd.get_context()

    @provider
    def provide_selection(self) -> Selection:
        return omni.usd.get_context().get_selection()

    @provider
    def provide_stage(self) -> Usd.Stage:
        ctx = omni.usd.get_context()
        return UsdUtils.StageCache.Get().Find(Usd.StageCache.Id.FromLongInt(ctx.get_stage_id()))
