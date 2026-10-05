import sqlite3
import os
import time
import logging
import cv2

def _calculate_box_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0

    boxAArea = max(1.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(1.0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    return interArea / float(boxAArea + boxBArea - interArea)

def _calculate_box_center_dist(boxA, boxB):
    cA_x = (boxA[0] + boxA[2]) / 2.0
    cA_y = (boxA[1] + boxA[3]) / 2.0
    cB_x = (boxB[0] + boxB[2]) / 2.0
    cB_y = (boxB[1] + boxB[3]) / 2.0
    return ((cA_x - cB_x) ** 2 + (cA_y - cB_y) ** 2) ** 0.5

class AlertEngine:
    def __init__(self, db_path="alerts.db", snapshot_dir="snapshots", cooldown_seconds=60):
        self.db_path = db_path
        self.snapshot_dir = snapshot_dir
        self.cooldown_seconds = cooldown_seconds
        
        # camera_name -> {track_id -> last_alert_time}
        self.cooldowns = {}
        # camera_name -> list of {"box": [x1, y1, x2, y2], "timestamp": float, "alert_type": str}
        self.recent_alerts = {}
        
        os.makedirs(self.snapshot_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS alerts
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                      camera TEXT,
                      zone TEXT,
                      alert_type TEXT,
                      track_id TEXT,
                      snapshot_path TEXT,
                      details TEXT)''')
        # Check if details column exists (for upgrade)
        try:
            c.execute("ALTER TABLE alerts ADD COLUMN details TEXT")
        except Exception:
            pass
        conn.commit()
        conn.close()

    def _is_on_cooldown(self, camera, entity_id, box, alert_type, now):
        if camera not in self.cooldowns:
            self.cooldowns[camera] = {}
            self.recent_alerts[camera] = []
            
        entity_key = str(entity_id)
        
        # 1. Track ID cooldown
        last_alert = self.cooldowns[camera].get(entity_key, 0)
        if now - last_alert < self.cooldown_seconds:
            return True
            
        # 2. Spatial / Positional Cooldown (Blocks duplicate alerts for same location)
        if box is not None:
            self.recent_alerts[camera] = [
                a for a in self.recent_alerts[camera] 
                if (now - a["timestamp"]) < self.cooldown_seconds
            ]
            
            for past in self.recent_alerts[camera]:
                if past.get("alert_type") == alert_type:
                    past_box = past.get("box")
                    if past_box is not None:
                        iou = _calculate_box_iou(box, past_box)
                        dist = _calculate_box_center_dist(box, past_box)
                        if iou > 0.25 or dist < 80.0:
                            return True
                            
        return False

    def trigger_alert(self, camera, zone, alert_type, entity_id, frame, details="PPE Violation", box=None):
        now = time.time()
        entity_key = str(entity_id)
        
        if self._is_on_cooldown(camera, entity_key, box, alert_type, now):
            return False # Suppressed due to cooldown or spatial duplication
            
        # Clean snapshot filename
        raw_name = f"{camera}_{alert_type}_{entity_id}_{int(now)}.jpg"
        clean_name = "".join(c for c in raw_name if c.isalnum() or c in "._-")
        snapshot_path = os.path.join(self.snapshot_dir, clean_name)
        
        if frame is not None:
            cv2.imwrite(snapshot_path, frame)
        
        # Log to DB
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO alerts (camera, zone, alert_type, track_id, snapshot_path, details) VALUES (?, ?, ?, ?, ?, ?)",
                  (camera, zone, alert_type, str(entity_id), snapshot_path, details))
        conn.commit()
        conn.close()
        
        # Update cooldown
        self.cooldowns[camera][entity_key] = now
        if box is not None:
            self.recent_alerts[camera].append({
                "box": box,
                "timestamp": now,
                "alert_type": alert_type
            })
        
        logging.warning(f"ALERT [{camera}]: {alert_type} ({details}) for {entity_id}. Saved to {snapshot_path}")
        return True

    def get_recent_alerts(self, limit=30):
        """Fetches the latest alerts from SQLite for display in the frontend."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT id, timestamp, camera, zone, alert_type, track_id, snapshot_path, details
                     FROM alerts ORDER BY id DESC LIMIT ?''', (limit,))
        rows = c.fetchall()
        conn.close()
        
        alerts = []
        for r in rows:
            snap_path = r[6]
            snap_url = ""
            if snap_path:
                normalized = snap_path.replace("\\", "/")
                if "static/" in normalized:
                    snap_url = "/static/" + normalized.split("static/")[1]
                else:
                    snap_url = f"/static/snapshots/{os.path.basename(snap_path)}"
            
            alerts.append({
                "id": r[0],
                "timestamp": r[1],
                "camera": r[2],
                "zone": r[3],
                "alert_type": r[4],
                "track_id": r[5],
                "snapshot_path": snap_path,
                "snapshot_url": snap_url,
                "details": r[7] or ("PPE Violation" if r[4] == "ppe_violation" else f"{r[4].capitalize()} Hazard")
            })
        return alerts
