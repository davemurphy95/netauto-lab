from jinja2 import Environment, FileSystemLoader

# Data: later this can come from YAML (your devices.yaml) instead
data = {
    "hostname": "SW1",
    "vlans": [
        {"id": 10, "name": "USERS"},
        {"id": 20, "name": "SERVERS"},
        {"id": 30, "name": "VOICE"},
    ],
    "interfaces": [
        {"name": "GigabitEthernet0/1", "description": "Uplink to core"},
        {"name": "GigabitEthernet0/2", "description": "User access port"},
    ],
}

# Load templates from the current folder
env = Environment(loader=FileSystemLoader("."), trim_blocks=True, lstrip_blocks=True)
template = env.get_template("vlans.j2")

config = template.render(data)
print(config)
