import time

def calculate_iou(boxA, boxB):
    """Calculates Intersection over Union (IoU) of two bounding boxes."""
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

def calculate_center_distance(boxA, boxB):
    """Euclidean distance between bounding box centers."""
    cA_x = (boxA[0] + boxA[2]) / 2.0
    cA_y = (boxA[1] + boxA[3]) / 2.0
    cB_x = (boxB[0] + boxB[2]) / 2.0
    cB_y = (boxB[1] + boxB[3]) / 2.0
    return ((cA_x - cB_x) ** 2 + (cA_y - cB_y) ** 2) ** 0.5

class SingleCameraTracker:
    """Maintains persistent object tracks isolated to a single camera stream."""
    def __init__(self, max_age_seconds=4.0, iou_threshold=0.25, max_center_dist=90.0):
        self.max_age_seconds = max_age_seconds
        self.iou_threshold = iou_threshold
        self.max_center_dist = max_center_dist
        self.next_track_id = 1
        # track_id -> dict: {box, class, conf, last_seen, first_seen, hits}
        self.tracks = {}

    def update(self, detections, timestamp=None):
        if timestamp is None:
            timestamp = time.time()

        # Cleanup expired tracks
        expired = [tid for tid, t in self.tracks.items() if (timestamp - t["last_seen"]) > self.max_age_seconds]
        for tid in expired:
            del self.tracks[tid]

        if not detections:
            return []

        matched_tracks = set()
        matched_dets = set()
        matches = []

        # Find best candidate matches between detections and existing camera tracks
        for d_idx, det in enumerate(detections):
            det_box = det["box"]
            for tid, track in self.tracks.items():
                if tid in matched_tracks:
                    continue

                iou = calculate_iou(det_box, track["box"])
                if iou >= self.iou_threshold:
                    matches.append((iou, d_idx, tid))
                else:
                    dist = calculate_center_distance(det_box, track["box"])
                    if dist <= self.max_center_dist:
                        pseudo_iou = 0.2 + (1.0 - dist / self.max_center_dist) * 0.1
                        matches.append((pseudo_iou, d_idx, tid))

        # Greedily assign matches with highest score
        matches.sort(key=lambda x: x[0], reverse=True)
        for score, d_idx, tid in matches:
            if d_idx in matched_dets or tid in matched_tracks:
                continue
            matched_dets.add(d_idx)
            matched_tracks.add(tid)

            track = self.tracks[tid]
            det = detections[d_idx]
            track["box"] = det["box"]
            track["conf"] = det["conf"]
            track["class"] = det["class"]
            track["last_seen"] = timestamp
            track["hits"] += 1
            det["track_id"] = tid

        # Assign new persistent IDs to unmatched detections
        for d_idx, det in enumerate(detections):
            if d_idx not in matched_dets:
                tid = self.next_track_id
                self.next_track_id += 1

                self.tracks[tid] = {
                    "box": det["box"],
                    "class": det["class"],
                    "conf": det["conf"],
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "hits": 1
                }
                det["track_id"] = tid

        return detections

class MultiCameraTracker:
    """Manages independent trackers for each camera to eliminate cross-camera track ID resets."""
    def __init__(self):
        self.camera_trackers = {}

    def update(self, camera_name, detections, timestamp=None):
        if camera_name not in self.camera_trackers:
            self.camera_trackers[camera_name] = SingleCameraTracker()
        return self.camera_trackers[camera_name].update(detections, timestamp=timestamp)
