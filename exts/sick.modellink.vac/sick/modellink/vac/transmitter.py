import carb
import cv2
import numpy as np
import threading
import time
from typing import Optional
from pxr import Usd, UsdShade, Sdf
from injector import inject
from sick.modellink.core.modellink_manager import linked, usd_attr

import omni.ui as ui
import omni.replicator.core as rep
import omni.usd


# ──────────────────────────────────────────────────────────────
# Capture base classes
# ──────────────────────────────────────────────────────────────
class RenderCapture:
    """Base class for render capture implementations"""
    def __init__(self, provider: ui.DynamicTextureProvider, camera_path: str = None):
        self.provider = provider
        self.camera_path = camera_path
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _capture_loop(self):
        raise NotImplementedError("Subclasses must implement _capture_loop")

    def _push_frame(self, frame: np.ndarray):
        """Push frame data to DynamicTextureProvider"""
        rgb = frame[:, :, :3]
        rgb = rgb / (rgb + 1.0) if frame.dtype == np.float32 else rgb / 255.0
        uint8 = (rgb * 255).clip(0, 255).astype(np.uint8)
        alpha = np.full(uint8.shape[:2] + (1,), 255, dtype=np.uint8)
        rgba = np.concatenate([uint8, alpha], axis=2)
        self.provider.set_data_array(rgba, list(rgba.shape[:2]) + [4])


class ReplicatorCapture(RenderCapture):
    """Captures frames from USD camera using Replicator"""
    def __init__(self, provider, camera_path):
        super().__init__(provider, camera_path)
        self._render_product = None
        self._writer = None
        self._setup_replicator()

    def _setup_replicator(self):
        """Set up Replicator render product and custom writer"""
        try:
            # Create RenderProduct
            self._render_product = rep.create.render_product(
                self.camera_path,
                (512, 512)
            )

            # Custom Writer class
            capture_instance = self
            
            class LiveFeedWriter(rep.Writer):
                def __init__(self, capture):
                    super().__init__()
                    self._capture = capture
                    self.annotators = []
                    self.annotators.append(rep.AnnotatorRegistry.get_annotator("rgb"))

                def write(self, data):
                    if not self._capture._running:
                        return
                    rgb_data = data.get("rgb")
                    if rgb_data is not None:
                        self._capture._push_frame(rgb_data)

            # Register and attach writer
            rep.WriterRegistry.register(LiveFeedWriter)
            self._writer = rep.WriterRegistry.get("LiveFeedWriter")
            self._writer.initialize(capture=capture_instance)
            self._writer.attach([self._render_product])

            carb.log_info(f"ReplicatorCapture initialized for camera: {camera_path}")
        except Exception as e:
            carb.log_error(f"ReplicatorCapture setup failed: {e}")

    def start(self):
        self._running = True
        carb.log_info("ReplicatorCapture started")

    def stop(self):
        self._running = False
        carb.log_info("ReplicatorCapture stopped")

    def _capture_loop(self):
        """Not used for Replicator (event-driven)"""
        pass


class MovieCapture(RenderCapture):
    """Captures frames from a video file"""
    def __init__(self, provider, video_path):
        super().__init__(provider, video_path)
        self._cap = None
        self._fps = 30
        self._frame_delay = 1.0 / self._fps

    def _capture_loop(self):
        try:
            self._cap = cv2.VideoCapture(self._video_path)
            if not self._cap.isOpened():
                carb.log_error(f"Failed to open video: {self._video_path}")
                return

            self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30
            self._frame_delay = 1.0 / self._fps

            while self._running:
                ret, frame = self._cap.read()
                if not ret:
                    # Loop video
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Resize to 512x512
                frame = cv2.resize(frame, (512, 512))
                self._push_frame(frame)
                time.sleep(self._frame_delay)

        except Exception as e:
            carb.log_error(f"MovieCapture error: {e}")
        finally:
            if self._cap:
                self._cap.release()

    def start(self):
        if self._running:
            return
        self._video_path = self.camera_path
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        carb.log_info(f"MovieCapture started: {self._video_path}")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
        carb.log_info("MovieCapture stopped")


# ──────────────────────────────────────────────────────────────
# Transmitter LinkedClass
# ──────────────────────────────────────────────────────────────
@linked(cluster="VAC")
class Transmitter:
    """
    Transmits video/camera feeds as dynamic textures to receiver materials.
    
    Attributes:
        vac:type - "camera" or "movie"
        vac:path - USD camera path (for camera) or file path (for movie)
        vac:image_receiver - Relationship to prims that receive the texture
    """

    @inject
    def __init__(self, prim: Usd.Prim, stage: Usd.Stage) -> None:
        self.prim = prim
        self.stage = stage
        self._current_capture: Optional[RenderCapture] = None
        self._provider: Optional[ui.DynamicTextureProvider] = None
        self._initialized = False
        self._set_params()
        self._initialize_capture()

    def _set_params(self):
        """Load configuration attributes"""
        type_attr = self.prim.GetAttribute("vac:type")
        path_attr = self.prim.GetAttribute("vac:path")
        
        self.capture_type = type_attr.Get() if type_attr else "camera"
        self.capture_path = path_attr.Get() if path_attr else None
        
        carb.log_info(f"Transmitter initialized - Type: {self.capture_type}, Path: {self.capture_path}")

    def _initialize_capture(self):
        """Set up capture based on type"""
        if self._initialized:
            return
        
        try:
            # Create dynamic texture provider
            texture_name = f"transmitter_{id(self)}"
            self._provider = ui.DynamicTextureProvider(texture_name)
            
            # Initialize empty texture
            initial = np.zeros((512, 512, 4), dtype=np.uint8)
            self._provider.set_data_array(initial, [512, 512, 4])
            
            # Create appropriate capture based on type
            if self.capture_type == "camera" and self.capture_path:
                self._current_capture = ReplicatorCapture(self._provider, self.capture_path)
                self._current_capture.start()
            elif self.capture_type == "movie" and self.capture_path:
                self._current_capture = MovieCapture(self._provider, self.capture_path)
                self._current_capture.start()
            else:
                carb.log_warn(f"Invalid transmitter config - Type: {self.capture_type}, Path: {self.capture_path}")
                return
            
            # Bind material to receiver prims
            self._bind_receivers(texture_name)
            self._initialized = True
            carb.log_info(f"Transmitter capture started with provider: {texture_name}")
            
        except Exception as e:
            carb.log_error(f"Transmitter initialization failed: {e}")

    def _bind_receivers(self, texture_name: str):
        """Set vac:inputname on all receiver prims with the texture name"""
        rel = self.prim.GetRelationship("vac:image_receivers")
        if not rel:
            carb.log_warn("No vac:image_receiver relationship found")
            return
        
        for target_path in rel.GetForwardedTargets():
            target_prim = self.stage.GetPrimAtPath(target_path)
            if not target_prim or not target_prim.IsValid():
                carb.log_warn(f"Invalid receiver prim: {target_path}")
                continue

            # Set the texture name as source_name on receiver
            input_name_attr = target_prim.GetAttribute("vac:source_name")
            if input_name_attr:
                input_name_attr.Set(texture_name, Usd.TimeCode.Default())
                carb.log_info(f"Set vac:source_name='{texture_name}' on receiver: {target_path}")

    @usd_attr("vac:image_receiver")
    def _update_receivers(self):
        """Update receivers when relationship changes"""
        if not self._initialized:
            return
        texture_name = f"transmitter_{id(self)}"
        self._bind_receivers(texture_name)


    @usd_attr("vac:type;vac:path")
    def _update_config(self):
        """Update capture configuration when attributes change"""
        self._set_params()
        # Restart capture with new configuration
        if self._current_capture:
            self._current_capture.stop()
            self._current_capture = None
        self._initialized = False
        self._initialize_capture()

    def __del__(self):
        """Clean up capture on destruction"""
        if self._current_capture:
            self._current_capture.stop()
