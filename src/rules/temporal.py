import time

class TemporalSmoother:
    def __init__(self, smoothing_window_seconds=1.0, min_hits=2):
        self.smoothing_window_seconds = smoothing_window_seconds
        self.min_hits = min_hits
        # track_id -> list of (timestamp, is_compliant)
        self.history = {}
        
    def update(self, track_id, is_compliant, timestamp=None):
        """
        Records the compliance state of a tracked person and determines if they are 
        non-compliant.
        Returns: 
          - "compliant" if currently compliant
          - "non-compliant" if non-compliant for at least min_hits observations
          - "pending" if non-compliant but still within grace period
        """
        if timestamp is None:
            timestamp = time.time()
            
        if track_id not in self.history:
            self.history[track_id] = []
            
        self.history[track_id].append((timestamp, is_compliant))
        
        # Cleanup history older than 5.0 seconds
        cutoff = timestamp - 5.0
        self.history[track_id] = [h for h in self.history[track_id] if h[0] > cutoff]
        
        if is_compliant:
            return "compliant"
            
        # Recent observations within the last 2.5 seconds
        window_start = timestamp - 2.5
        recent_history = [h for h in self.history[track_id] if h[0] >= window_start]
        
        if not recent_history:
            return "pending"
            
        # Count non-compliant observations
        non_compliant_count = sum(1 for h in recent_history if not h[1])
        
        if non_compliant_count >= self.min_hits:
            return "non-compliant"
            
        return "pending"

    def remove_track(self, track_id):
        if track_id in self.history:
            del self.history[track_id]
