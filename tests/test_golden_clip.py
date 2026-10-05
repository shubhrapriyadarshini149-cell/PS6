import cv2
import sys
import os
import yaml

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.inference.adapter import ModelAdapter
from src.rules.ppe_rules import associate_ppe, check_compliance
from src.rules.temporal import TemporalSmoother
from src.alerts.engine import AlertEngine
from src.rules.zone_rules import ZoneRules

def test_golden_clip():
    # 1. Load config
    with open("config/models.yaml", "r") as f:
        models_config = yaml.safe_load(f)["models"]
    
    # 2. Initialize Adapter for PPE primary
    ppe_model_config = models_config["ppe_primary"]
    adapter = ModelAdapter("ppe_primary", ppe_model_config)
    print("Loading model...")
    adapter.load()
    
    # 3. Setup Rules & Engines
    rules = ZoneRules()
    required_ppe = rules.get_required_ppe("loading_dock") # Default to loading dock
    # Fallback if empty in yaml
    if not required_ppe:
        required_ppe = ["hardhat", "vest"]
        
    smoother = TemporalSmoother(smoothing_window_seconds=1.0) # short window for test
    alert_engine = AlertEngine(db_path="eval/test_alerts.db", snapshot_dir="eval/snapshots")
    
    # 4. Open sample video
    cap = cv2.VideoCapture("eval/data/clips/sample_workers.mp4")
    if not cap.isOpened():
        print("Could not open sample_workers.mp4. Did you run download script?")
        return
        
    print("Running baseline pipeline on golden clip...")
    frame_count = 0
    alerts_fired = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        
        # We only run inference every 5th frame to simulate our budget
        if frame_count % 5 != 0:
            continue
            
        detections = adapter.predict(frame)
        persons, hazards = associate_ppe(detections)
        
        for person in persons:
            is_compliant = check_compliance(person, required_ppe)
            track_id = person.get("track_id")
            
            if track_id is not None:
                state = smoother.update(track_id, is_compliant)
                
                if state == "non-compliant":
                    fired = alert_engine.trigger_alert("test_cam", "loading_dock", "ppe_violation", track_id, frame)
                    if fired:
                        alerts_fired += 1
                        print(f"Frame {frame_count}: Fired PPE alert for track {track_id}. Missing: {required_ppe}, Had: {person['equipment']}")
                        
    cap.release()
    print(f"Finished processing {frame_count} frames. Total unique alerts fired: {alerts_fired}")

if __name__ == "__main__":
    test_golden_clip()
