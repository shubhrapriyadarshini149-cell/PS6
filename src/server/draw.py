import cv2

COLOR_MAP = {
    "person": (255, 0, 0),      # Blue
    "hardhat": (0, 255, 0),     # Green
    "vest": (0, 255, 255),      # Yellow
    "no-hardhat": (0, 0, 255),  # Red
    "no-vest": (0, 0, 255),     # Red
    "fire": (0, 165, 255),      # Orange
    "smoke": (128, 128, 128)    # Gray
}

def draw_annotations(frame, detections):
    """Draws bounding boxes and labels on the frame based on detections."""
    # Create a copy so we don't mutate the original frame being used elsewhere
    annotated = frame.copy()
    
    for det in detections:
        cls = det["class"]
        conf = det["conf"]
        box = det["box"]
        track_id = det.get("track_id")
        
        x1, y1, x2, y2 = map(int, box)
        color = COLOR_MAP.get(cls, (255, 255, 255))
        
        # Draw box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        
        # Prepare label
        label = f"{cls} {conf:.2f}"
        if track_id is not None:
            label = f"ID:{track_id} " + label
            
        # Draw label background
        (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated, (x1, y1 - text_height - 4), (x1 + text_width, y1), color, -1)
        
        # Draw text
        cv2.putText(annotated, label, (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
    return annotated
