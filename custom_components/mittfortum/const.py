"""Constants for the MittFortum integration."""

DOMAIN = "mittfortum"
BASE_URL = "https://retail-lisa-eu-prd-energyflux.herokuapp.com/api"
CONSUMPTION_URL = f"{BASE_URL}/consumption/customer/{{customer_id}}/meteringPoint/{{metering_point}}"
CUSTOMER_URL = f"{BASE_URL}/customer/{{customer_id}}"
DELIVERYSITES_URL = f"{BASE_URL}/deliverysites/{{customer_id}}"