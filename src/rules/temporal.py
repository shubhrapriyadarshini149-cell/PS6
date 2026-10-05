import time

class TemporalSmoother:
    def __init__(self, smoothing_window_seconds=5.0):
        self.smoothing_window_seconds = smoothing_window_seconds
        # track_id -> list of (timestamp, is_compliant)
        self.history = {}
        
    def update(self, track_id, is_compliant, timestamp=None):
        """
        Records the compliance state of a tracked person and determines if they are 
        SUSTAINABLY non-compliant.
        Returns: 
          - "compliant" if currently compliant
          - "non-compliant" if non-compliant for longer than the smoothing window
          - "pending" if non-compliant but within the grace window
        """
        if timestamp is None:
            timestamp = time.time()
            
        if track_id not in self.history:
            self.history[track_id] = []
            
        self.history[track_id].append((timestamp, is_compliant))
        
        # Cleanup history older than window + a small buffer (e.g. 2s)
        cutoff = timestamp - self.smoothing_window_seconds - 2.0
        self.history[track_id] = [h for h in self.history[track_id] if h[0] > cutoff]
        
        # If currently compliant, they are safe
        if is_compliant:
            return "compliant"
            
        # Check how long they have been non-compliant
        # Are there ANY compliant frames in the smoothing window?
        window_start = timestamp - self.smoothing_window_seconds
        recent_history = [h for h in self.history[track_id] if h[0] >= window_start]
        
        if not recent_history:
            return "pending"
            
        # If the earliest record in the window is older than the window, 
        # and ALL records in the window are non-compliant, trigger alert.
        time_non_compliant = timestamp - recent_history[0][0]
        
        all_non_compliant = all(not h[1] for h in recent_history)
        
        if all_non_compliant and time_non_compliant >= self.smoothing_window_seconds:
            return "non-compliant"
            
        return "pending"

    def remove_track(self, track_id):
        if track_id in self.history:
            del self.history[track_id]
