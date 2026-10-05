import sqlite3
import os
import time
import logging
import cv2

class AlertEngine:
    def __init__(self, db_path="alerts.db", snapshot_dir="snapshots", cooldown_seconds=60):
        self.db_path = db_path
        self.snapshot_dir = snapshot_dir
        self.cooldown_seconds = cooldown_seconds
        
        # camera_name -> {track_id (or 'fire') -> last_alert_time}
        self.cooldowns = {}
        
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
                      snapshot_path TEXT)''')
        conn.commit()
        conn.close()

    def _is_on_cooldown(self, camera, entity_id, now):
        if camera not in self.cooldowns:
            self.cooldowns[camera] = {}
            
        last_alert = self.cooldowns[camera].get(entity_id, 0)
        if now - last_alert < self.cooldown_seconds:
            return True
        return False

    def trigger_alert(self, camera, zone, alert_type, entity_id, frame):
        now = time.time()
        
        if self._is_on_cooldown(camera, entity_id, now):
            return False # Ignored due to cooldown
            
        # Save snapshot
        snapshot_filename = f"{camera}_{alert_type}_{entity_id}_{int(now)}.jpg"
        snapshot_path = os.path.join(self.snapshot_dir, snapshot_filename)
        cv2.imwrite(snapshot_path, frame)
        
        # Log to DB
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO alerts (camera, zone, alert_type, track_id, snapshot_path) VALUES (?, ?, ?, ?, ?)",
                  (camera, zone, alert_type, str(entity_id), snapshot_path))
        conn.commit()
        conn.close()
        
        # Update cooldown
        self.cooldowns[camera][entity_id] = now
        
        logging.warning(f"ALERT [{camera}]: {alert_type} for {entity_id}. Saved to {snapshot_path}")
        return True
