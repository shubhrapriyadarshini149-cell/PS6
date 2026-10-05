import time
import logging
from src.rules.ppe_rules import associate_ppe, check_compliance
from src.rules.temporal import TemporalSmoother
from src.rules.zone_rules import ZoneRules
from src.tracking.multi_camera_tracker import MultiCameraTracker

class InferenceScheduler:
    def __init__(self, cameras, models, max_fps=15.0, alert_engine=None, zone_rules=None):
        """
        cameras: list of CameraThread objects
        models: list of loaded ModelAdapter objects
        max_fps: total global inference budget (frames per second across all cameras)
        alert_engine: optional AlertEngine instance to log alerts and save snapshots
        zone_rules: optional ZoneRules instance
        """
        self.cameras = [c for c in cameras if c.is_running]
        self.models = models
        self.max_fps = max_fps
        self.min_loop_time = 1.0 / max_fps if max_fps > 0 else 0
        self.is_running = False
        
        self.alert_engine = alert_engine
        self.zone_rules = zone_rules or ZoneRules()
        self.smoothers = {} # camera_name -> TemporalSmoother
        self.multi_tracker = MultiCameraTracker() # Camera-isolated persistent tracking
        
        # We store the latest detection results per camera here
        self.latest_results = {cam.name: [] for cam in self.cameras}

    def start(self):
        self.is_running = True
        logging.info(f"Starting Inference Scheduler with {len(self.cameras)} cameras and {len(self.models)} models.")
        
        camera_idx = 0
        while self.is_running:
            loop_start = time.time()
            
            if not self.cameras:
                time.sleep(0.5)
                continue
                
            cam = self.cameras[camera_idx]
            frame, timestamp = cam.get_latest_frame()
            
            if frame is not None:
                all_detections = []
                for model in self.models:
                    # Run each model on the frame
                    try:
                        dets = model.predict(frame)
                        all_detections.extend(dets)
                    except Exception as e:
                        logging.error(f"Inference error on model {model.config_key}: {e}")
                
                # Apply per-camera isolated tracking to guarantee stable IDs
                all_detections = self.multi_tracker.update(cam.name, all_detections, timestamp=loop_start)
                self.latest_results[cam.name] = all_detections
                
                # Evaluate rules and trigger alerts
                if self.alert_engine and all_detections:
                    try:
                        persons, hazards = associate_ppe(all_detections)
                        camera_name = cam.name
                        zone = cam.config.get("zone", "loading_dock")
                        required_ppe = self.zone_rules.get_required_ppe(zone)
                        if not required_ppe:
                            required_ppe = ["hardhat", "vest"]
                            
                        if camera_name not in self.smoothers:
                            self.smoothers[camera_name] = TemporalSmoother(smoothing_window_seconds=1.0, min_hits=2)
                            
                        smoother = self.smoothers[camera_name]
                        
                        # 1. Check PPE compliance per tracked person
                        for person in persons:
                            is_compliant = check_compliance(person, required_ppe)
                            track_id = person.get("track_id")
                            box = person.get("box")
                            if track_id is None:
                                b = box or [0, 0, 0, 0]
                                track_id = f"person_{int(b[0])//60}_{int(b[1])//60}"
                                
                            state = smoother.update(str(track_id), is_compliant, timestamp=loop_start)
                            if state == "non-compliant":
                                equipment = person.get("equipment", [])
                                if "no-hardhat" in equipment:
                                    missing_str = "No Hardhat Detected"
                                elif "no-vest" in equipment:
                                    missing_str = "No Safety Vest Detected"
                                else:
                                    missing = [req for req in required_ppe if req not in equipment]
                                    missing_labels = [m.replace("hardhat", "Hardhat").replace("vest", "Safety Vest") for m in missing]
                                    missing_str = f"Missing: {', '.join(missing_labels)}" if missing_labels else "PPE Violation"
                                    
                                self.alert_engine.trigger_alert(
                                    camera=camera_name,
                                    zone=zone,
                                    alert_type="ppe_violation",
                                    entity_id=str(track_id),
                                    frame=frame,
                                    details=missing_str,
                                    box=box
                                )
                                    
                        # 2. Check hazard detections (fire / smoke)
                        for hazard in hazards:
                            h_type = hazard.get("class", "fire")
                            conf = hazard.get("conf", 0.0)
                            details = f"{h_type.upper()} Detected ({int(conf * 100)}%)"
                            self.alert_engine.trigger_alert(
                                camera=camera_name,
                                zone=zone,
                                alert_type=h_type,
                                entity_id=f"{h_type}_hazard",
                                frame=frame,
                                details=details,
                                box=hazard.get("box")
                            )
                    except Exception as e:
                        logging.error(f"Alert evaluation error on {cam.name}: {e}")
            
            # Move to next camera (round robin)
            camera_idx = (camera_idx + 1) % len(self.cameras)
            
            # Enforce inference budget
            elapsed = time.time() - loop_start
            sleep_time = self.min_loop_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self):
        self.is_running = False
