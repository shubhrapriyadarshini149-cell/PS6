import yaml
import logging

def load_models_config(yaml_path="config/models.yaml"):
    try:
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('models', {})
    except Exception as e:
        logging.error(f"Failed to load models config from {yaml_path}: {e}")
        return {}
