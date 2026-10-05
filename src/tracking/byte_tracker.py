# ByteTrack wrapper using ultralytics built-in tracker
from ultralytics.trackers import BOTSORT, BYTETracker
import yaml

class TrackerWrapper:
    def __init__(self, tracker_type="bytetrack"):
        self.tracker_type = tracker_type
        # Ultralytics handles ByteTrack internally if we pass tracker="bytetrack.yaml"
        # We can just expose a clean wrapper around it if we were doing custom bounding boxes,
        # but since we are using YOLOv8 natively, we can just call model.track().
        # This file serves as a placeholder to configure tracker thresholds if needed.
        pass
        
    def get_tracker_config(self):
        # We'll rely on the default bytetrack.yaml provided by Ultralytics
        return "bytetrack.yaml"
