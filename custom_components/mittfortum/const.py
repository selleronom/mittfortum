"""Constants for the MittFortum integration."""

DOMAIN = "mittfortum"
ENERGY_BASE_URL = "https://retail-lisa-eu-prd-energyflux.herokuapp.com/api"
CUSTOMER_BASE_URL = "https://retail-lisa-eu-prd-customersrv.herokuapp.com/api"

CONSUMPTION_URL = f"{ENERGY_BASE_URL}/consumption/customer/{{customer_id}}/meteringPoint/{{metering_point}}"
CUSTOMER_URL = f"{CUSTOMER_BASE_URL}/customer/{{customer_id}}"
DELIVERYSITES_URL = f"{CUSTOMER_BASE_URL}/deliverysites/{{customer_id}}"
