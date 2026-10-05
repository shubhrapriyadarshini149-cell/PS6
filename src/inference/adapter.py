import logging
from ultralytics import YOLO

class ModelAdapter:
    def __init__(self, config_key, model_config):
        self.config_key = config_key
        self.model_config = model_config
        self.role = model_config.get("role")
        self.weights = model_config.get("weights")
        self.alias_map = model_config.get("alias", {})
        self.required_classes = model_config.get("required_classes", [])
        self.conf_thresholds = model_config.get("conf", {})
        self.imgsz = model_config.get("imgsz", 640)
        
        self.model = None
        self.names = {}
        self.normalized_to_raw_indices = {}

    def load(self):
        logging.info(f"Loading model {self.config_key} from {self.weights}")
        try:
            self.model = YOLO(self.weights)
            self.names = self.model.names # dict mapping class index to raw name
            self._build_normalized_map()
            self._validate_required_classes()
            return True
        except Exception as e:
            logging.error(f"Failed to load model {self.config_key}: {e}")
            raise
            
    def _build_normalized_map(self):
        """Builds a mapping from our normalized classes (e.g. 'person') to the model's specific class indices."""
        self.normalized_to_raw_indices = {}
        for idx, raw_name in self.names.items():
            # If the raw name (or string representation of idx like '0') is in the alias map, use the normalized name
            normalized_name = self.alias_map.get(raw_name, self.alias_map.get(str(idx), raw_name.lower()))
            if normalized_name not in self.normalized_to_raw_indices:
                self.normalized_to_raw_indices[normalized_name] = []
            self.normalized_to_raw_indices[normalized_name].append(idx)
            
    def _validate_required_classes(self):
        """Fails fast if the loaded model doesn't support the required classes."""
        missing = []
        for req_cls in self.required_classes:
            if req_cls not in self.normalized_to_raw_indices:
                missing.append(req_cls)
        
        if missing:
            err = f"Model {self.config_key} is missing required classes after alias mapping: {missing}"
            logging.error(err)
            raise ValueError(err)

    def predict(self, frame):
        """Runs inference and yields normalized results with track IDs."""
        if self.model is None:
            raise RuntimeError(f"Model {self.config_key} not loaded.")
            
        results = self.model.track(frame, imgsz=self.imgsz, persist=True, tracker="bytetrack.yaml", verbose=False)
        
        normalized_detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_idx = int(box.cls[0].item())
                raw_name = self.names[cls_idx]
                conf = float(box.conf[0].item())
                
                track_id = int(box.id[0].item()) if box.id is not None else None
                
                normalized_name = self.alias_map.get(raw_name, self.alias_map.get(str(cls_idx), raw_name.lower()))
                
                # Filter by per-class confidence
                req_conf = self.conf_thresholds.get(normalized_name, 0.25)
                if conf >= req_conf:
                    xyxy = box.xyxy[0].cpu().numpy().tolist()
                    normalized_detections.append({
                        "class": normalized_name,
                        "conf": conf,
                        "box": xyxy, # [x1, y1, x2, y2]
                        "track_id": track_id
                    })
                    
        return normalized_detections
