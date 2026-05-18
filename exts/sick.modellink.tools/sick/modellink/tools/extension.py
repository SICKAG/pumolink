import asyncio
import threading
import carb
import omni.ext
import omni.ui as ui
import sick.modellink.core as ml


def _sort_text(value) -> str:
    if value is None:
        return ""
    try:
        return str(value).lower()
    except Exception:
        return ""

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
    def __init__(self, activator, parent=None):
        super().__init__()
        self.activator = activator
        self.parent = parent


class ClusterItem(ui.AbstractItem):
    def __init__(self, name: str, children=None, cluster_key=None):
        super().__init__()
        self.name = name
        self.cluster_key = cluster_key
        self.children = children or []
        self.parent = None
        self.expanded = True

    @property
    def enabled_count(self) -> int:
        return sum(1 for child in self.children if child.activator.enabled)

    @property
    def all_enabled(self) -> bool:
        return bool(self.children) and self.enabled_count == len(self.children)

    @property
    def all_disabled(self) -> bool:
        return self.enabled_count == 0


class LinkItem(ui.AbstractItem):
    def __init__(self, link):
        super().__init__()
        self.link = link


class ActivatorDelegate(ui.AbstractItemDelegate):

    def build_widget(self, model, item, column_id, level, expanded):
        is_cluster = hasattr(item, "children") and not hasattr(item, "activator")
        color = "white"
        if is_cluster and item.all_disabled:
            color = "grey"
        if not is_cluster and not item.activator.enabled:
            color = "grey"

        def _toggle(_x, _y, _b, _m):
            manager = ml.ModelLinkManager()
            if is_cluster:
                manager.set_cluster_enabled(item.cluster_key, not item.all_enabled)
            else:
                manager.set_class_enabled(item.activator.clazz, not item.activator.enabled)

        if is_cluster and column_id == 0:
            icon = "-" if item.expanded else "+"

            button_ref = {"widget": None}

            def _toggle_expand():
                model.toggle_cluster_expanded(item)
                widget = button_ref["widget"]
                if widget is not None:
                    try:
                        widget.text = "-" if item.expanded else "+"
                    except Exception:
                        pass

            with ui.HStack(spacing=4):
                button_ref["widget"] = ui.Button(icon, width=18, clicked_fn=_toggle_expand)
                ui.Label(
                    model.get_item_value_model(item, column_id),
                    style={"color": color},
                    mouse_double_clicked_fn=_toggle,
                )
            return

        ui.Label(
            model.get_item_value_model(item, column_id),
            style={"color": color},
            mouse_double_clicked_fn=_toggle,
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
        self._children = []
        self.set_list(activator_list)

    def set_list(self, activator_list):
        previous_expanded = {
            getattr(c, "cluster_key", c.name): c.expanded
            for c in self._children
            if hasattr(c, "children")
        }
        grouped = {}
        for activator in activator_list:
            cluster = getattr(activator, "cluster", None)
            if isinstance(cluster, str):
                cluster = cluster.strip() or None
            else:
                cluster = None
            if cluster not in grouped:
                grouped[cluster] = []
            grouped[cluster].append(activator)

        children = []
        for cluster_name in sorted(grouped.keys(), key=_sort_text):
            activators = sorted(
                grouped[cluster_name],
                key=lambda a: _sort_text(f"{getattr(a.clazz, '__module__', '')}.{getattr(a.clazz, '__qualname__', '')}"),
            )
            activator_children = [ActivatorItem(a) for a in activators]
            display_name = "(not clustered)" if cluster_name is None else str(cluster_name)
            cluster_item = ClusterItem(display_name, activator_children, cluster_name)
            cluster_item.expanded = previous_expanded.get(cluster_name, True)
            for child in activator_children:
                child.parent = cluster_item
            children.append(cluster_item)

        self._children = children
        self._rows = self._build_rows(children)
        self._item_changed(None)

    def _build_rows(self, clusters):
        rows = []
        for cluster in clusters:
            rows.append(cluster)
            if cluster.expanded:
                rows.extend(cluster.children)
        return rows

    def toggle_cluster_expanded(self, cluster_item):
        cluster_item.expanded = not cluster_item.expanded
        self._rows = self._build_rows(self._children)
        self._item_changed(None)
        

    def _is_cluster_item(self, item) -> bool:
        return isinstance(item, ClusterItem)

    def _is_activator_item(self, item) -> bool:
        return isinstance(item, ActivatorItem)

    def _is_tree_root_proxy(self, item) -> bool:
        return item is not None and not self._is_cluster_item(item) and not self._is_activator_item(item)

    def get_item_children(self, item):
        if item is None or self._is_tree_root_proxy(item):
            return self._rows
        return []

    def get_item_parent(self, item):
        if item is None:
            return None
        return getattr(item, "parent", None)

    def can_item_have_children(self, item):
        return item is None or self._is_tree_root_proxy(item)

    def get_item_value_model_count(self, item):
        return 3

    def get_item_value_model(self, item, column_id):
        if self._is_tree_root_proxy(item):
            return ""

        if self._is_cluster_item(item):
            switcher = {
                0: str(item.name),
                1: "",
                2: "",
            }
            return switcher.get(column_id, "")

        switcher = {
            0: f"{'    ' if getattr(item, 'parent', None) is not None else ''}{str(item.activator.clazz.__qualname__)}",
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
