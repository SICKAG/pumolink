import asyncio
import threading
import carb
import omni.ext
import omni.ui as ui
import sick.modellink.core as ml

class ModelLinkToolsExtension(omni.ext.IExt):

    def wait_docking(self, window, neighbor_name: str):
        window.deferred_dock_in(neighbor_name)

        async def __waiter():
            property_win = None

            frames = 3
            while frames > 0:
                if not property_win:
                    property_win = ui.Workspace.get_window(neighbor_name)
                if property_win:
                    break   # early out

                frames = frames - 1
                await omni.kit.app.get_app().next_update_async()

            # Dock to Property window after 5 frames. It's enough for window to appear.
            for _ in range(5):
                await omni.kit.app.get_app().next_update_async()

            if property_win:
                window.deferred_dock_in(neighbor_name)

        asyncio.ensure_future(__waiter())


    def on_startup(self, ext_id):
        print("[sick.modellink.tool] sick  modellink_tool startup")

        self.timer = None
        self._links_model = LinkModel()
        self._link_delegate = LinkDelegate()

        self._activators_model = ActivatorModel()
        self._activator_delegate = ActivatorDelegate()

        self.build_ui()

        manager = ml.ModelLinkManager()

        self._subscription = ml.ModelLinkManager().get_event_stream().create_subscription_to_push(self.on_changes)


        def refresh():  # refresh every 5 seconds in case somethink changes besides the events
            links_list = manager.get_modellinks()
            self._links_model.set_list(links_list)
            activator_list = manager.get_activators()
            self._activators_model.set_list(activator_list)
            self.timer = threading.Timer(5, refresh)
            self.timer.start()

        refresh()


    def on_changes(self, e: carb.events.IEvent):
        manager = ml.ModelLinkManager()
        if e.type == int(ml.MODELLINK_ACTIVATOR_ADDED) \
                or e.type == int(ml.MODELLINK_ACTIVATOR_REMOVED) \
                or e.type == int(ml.MODELLINK_ACTIVATOR_ENABLED) \
                or e.type == int(ml.MODELLINK_ACTIVATOR_DISABLED):
            self._activators_model.set_list(manager.get_activators())

        if e.type == int(ml.MODELLINK_ADDED) or e.type == int(ml.MODELLINK_REMOVED):
            self._links_model.set_list(manager.get_modellinks())


    def on_shutdown(self):
        print("[sick.modellink.tool] sick  modellink_tool shutdown")
        if self.timer:
            self.timer.cancel()
        self._subscription = None

    def build_ui(self):
        self._window = ui.Window("ModelLink Monitor", width=300, height=300)
        with self._window.frame:
            with ui.ScrollingFrame(horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF, vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED):
                with ui.VStack(height=0):
                    # with ui.CollapsableFrame("Tools"):
                    #    with ui.VStack(height=0):
                    #        ui.Button("Copy Python Template from Selection to Clipboard")
                    with ui.CollapsableFrame("ModelLinks"):
                        with ui.ScrollingFrame(
                            height=200,
                            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                            style_type_name_override="TreeView",
                        ):
                            ui.TreeView(self._links_model, delegate=self._link_delegate, columns_resizable=True, column_widths=[ui.Fraction(0.4), ui.Fraction(0.3), ui.Fraction(0.3)], header_visible=True, root_visible=False)
                    with ui.CollapsableFrame("ModelLink Activators \n(Double click to disable/enable Activator)"):
                        with ui.ScrollingFrame(
                            height=200,
                            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                            style_type_name_override="TreeView",
                        ):
                            ui.TreeView(self._activators_model, delegate=self._activator_delegate, columns_resizable=True, column_widths=[ui.Fraction(0.2), ui.Fraction(0.5), ui.Fraction(0.3)], header_visible=True, root_visible=False)
        self.wait_docking(self._window, "Stage")


class ActivatorItem(ui.AbstractItem):
    def __init__(self, activator):
        super().__init__()
        self.activator = activator


class LinkItem(ui.AbstractItem):
    def __init__(self, link):
        super().__init__()
        self.link = link


class ActivatorDelegate(ui.AbstractItemDelegate):

    def build_widget(self, model, item, column_id, level, expanded):
        ui.Label(
            model.get_item_value_model(item, column_id),
            style={"color": "white" if item.activator.enabled else "grey"},
            mouse_double_clicked_fn=lambda _x, _y, _b, _m: ml.ModelLinkManager().set_class_enabled(item.activator.clazz, not item.activator.enabled)
        )

    def build_header(self, column_id):
        """Build the header"""
        if column_id == 0:
            ui.Label("Class")
        elif column_id == 1:
            ui.Label("Module")
        else:
            ui.Label("Detector")


class LinkDelegate(ui.AbstractItemDelegate):

    def build_widget(self, model, item, column_id, level, expanded):
        ui.Label(
            model.get_item_value_model(item, column_id),
        )

    def build_header(self, column_id):
        if column_id == 0:
            ui.Label("Prim Path")
        elif column_id == 1:
            ui.Label("Class")
        else:
            ui.Label("Instance")


class ActivatorModel(ui.AbstractItemModel):
    def __init__(self, activator_list=[]):
        super().__init__()
        self._children = [ActivatorItem(t) for t in activator_list]

    def set_list(self, activator_list):
        self._children = [ActivatorItem(t) for t in activator_list]
        self._item_changed(None)

    def get_item_children(self, item):
        if item is not None:
            return []
        return self._children

    def get_item_value_model_count(self, item):
        return 3

    def get_item_value_model(self, item, column_id):
        switcher = {
            0: str(item.activator.clazz.__qualname__),
            1: str(item.activator.clazz.__module__),
            2: f"{item.activator.detectType} ({item.activator.reference})"
        }
        return switcher.get(column_id, "---")


class LinkModel(ui.AbstractItemModel):
    def __init__(self, links_list=[]):
        super().__init__()
        self._children = [LinkItem(t) for t in links_list]

    def set_list(self, links_list):
        self._children = [LinkItem(t) for t in links_list]
        self._item_changed(None)

    def get_item_children(self, item):
        if item is not None:
            return []
        return self._children

    def get_item_value_model_count(self, item):
        return 3

    def get_item_value_model(self, item, column_id):
        switcher = {
            0: str(item.link._prim.GetPrimPath()),
            1: str(item.link._instance.__class__.__qualname__),
            2: f"{hex(id(item.link._instance))}"
        }
        return switcher.get(column_id, "---")
