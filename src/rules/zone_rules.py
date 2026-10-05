import yaml
import logging

class ZoneRules:
    def __init__(self, yaml_path="config/rules.yaml"):
        self.rules = {}
        try:
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)
                self.rules = config.get("zones", {})
        except Exception as e:
            logging.error(f"Failed to load zone rules from {yaml_path}: {e}")
            
    def get_required_ppe(self, zone_name):
        zone_config = self.rules.get(zone_name, {})
        return zone_config.get("required_ppe", [])
        
    def get_smoothing_window(self, zone_name):
        zone_config = self.rules.get(zone_name, {})
        return zone_config.get("temporal_smoothing_seconds", 5.0)
