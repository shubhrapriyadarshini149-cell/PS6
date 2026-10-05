def get_iou(box1, box2):
    """Calculate Intersection over Union (IoU) of two bounding boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    if inter_area == 0:
        return 0

    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    return inter_area / float(box1_area + box2_area - inter_area)

def is_inside(inner_box, outer_box):
    """Check if inner_box is significantly inside outer_box.
    Returns the percentage of inner_box area that is inside outer_box."""
    x1 = max(inner_box[0], outer_box[0])
    y1 = max(inner_box[1], outer_box[1])
    x2 = min(inner_box[2], outer_box[2])
    y2 = min(inner_box[3], outer_box[3])
    
    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    inner_area = (inner_box[2] - inner_box[0]) * (inner_box[3] - inner_box[1])
    
    if inner_area == 0:
        return 0
    return inter_area / float(inner_area)

def associate_ppe(detections):
    """
    Groups PPE detections with Person detections based on bounding box geometry.
    Returns a list of persons, where each person is a dict with their box, conf, track_id (if any) and a list of 'equipment'.
    Also returns a list of standalone hazards (e.g. fire/smoke).
    """
    persons = []
    ppe_items = []
    hazards = []
    
    for det in detections:
        cls = det["class"]
        if cls == "person":
            det["equipment"] = []
            persons.append(det)
        elif cls in ["hardhat", "vest", "no-hardhat", "no-vest"]:
            ppe_items.append(det)
        elif cls in ["fire", "smoke"]:
            hazards.append(det)
            
    # Naive association: if a PPE box is mostly inside a Person box, assign it.
    # In a crowded scene, assign to the person with highest overlap.
    for ppe in ppe_items:
        best_person = None
        best_overlap = 0
        for p in persons:
            overlap = is_inside(ppe["box"], p["box"])
            if overlap > best_overlap:
                best_overlap = overlap
                best_person = p
                
        # If at least 50% of the PPE box is inside the person box
        if best_person is not None and best_overlap > 0.5:
            best_person["equipment"].append(ppe["class"])
            
    return persons, hazards

def check_compliance(person, required_ppe, use_negative_classes="corroborate"):
    """
    Checks if a person has the required PPE.
    Returns True if compliant, False otherwise.
    """
    equipment = person["equipment"]
    
    for req in required_ppe:
        if req not in equipment:
            # If the model explicitly detected the lack of it, use that as strong corroboration
            if use_negative_classes == "corroborate":
                neg_class = f"no-{req}"
                if neg_class in equipment:
                    return False
            # Otherwise just strictly failing because it's not detected
            return False
            
    return True
