"""Example configuration for MittFortum integration."""

# Example Home Assistant configuration.yaml entry
"""
# Add this to your configuration.yaml if manual configuration is needed
# (normally the integration is configured through the UI)

mittfortum:
  username: "your_mittfortum_username"
  password: "your_mittfortum_password"
  scan_interval: 15  # minutes (optional, default: 15)
  timeout: 30  # seconds (optional, default: 30)
"""

# Example secrets.yaml entries
"""
# Add these to your secrets.yaml file
mittfortum_username: "your_username_here"
mittfortum_password: "your_password_here"

# OAuth2 credentials (if using custom OAuth2 app)
mittfortum_client_id: "your_client_id_here"
mittfortum_client_secret: "your_client_secret_here"
"""

# Example automation using MittFortum sensors
"""
# Example automation in automations.yaml
- alias: "High Energy Consumption Alert"
  trigger:
    - platform: numeric_state
      entity_id: sensor.main_meter_energy_consumption
      above: 500  # kWh
  action:
    - service: notify.pushover
      data:
        message: "High energy consumption detected: {{ states('sensor.main_meter_energy_consumption') }} kWh"
        title: "Energy Alert"

- alias: "Daily Energy Cost Report"
  trigger:
    - platform: time
      at: "23:00:00"
  action:
    - service: notify.email
      data:
        title: "Daily Energy Report"
        message: |
          Energy consumed today: {{ states('sensor.main_meter_energy_consumption') }} kWh
          Cost today: {{ states('sensor.main_meter_total_cost') }} SEK
"""

# Example Lovelace dashboard configuration
"""
# Example dashboard card configuration
type: entities
title: Energy Monitoring
entities:
  - entity: sensor.main_meter_energy_consumption
    name: Energy Consumption
    icon: mdi:lightning-bolt
  - entity: sensor.main_meter_total_cost
    name: Total Cost
    icon: mdi:currency-usd
  - type: divider
  - entity: sensor.main_meter_current_power
    name: Current Power
    icon: mdi:flash

# Example energy dashboard integration
type: energy-grid-neutrality-gauge
energy_sources:
  - entity: sensor.main_meter_energy_consumption
    name: Grid Consumption
"""

# Example Node-RED flow configuration
"""
[
    {
        "id": "energy_monitor",
        "type": "server-state-changed",
        "name": "Energy Consumption Changed",
        "server": "home_assistant",
        "version": 1,
        "entityidfilter": "sensor.main_meter_energy_consumption",
        "entityidfiltertype": "exact",
        "outputinitially": false,
        "state_type": "str",
        "haltifstate": "",
        "halt_if_type": "str",
        "halt_if_compare": "is",
        "outputs": 1,
        "output_only_on_state_change": true,
        "x": 200,
        "y": 100,
        "wires": [["process_energy_data"]]
    }
]
"""
