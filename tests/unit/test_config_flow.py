"""Test config flow."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant import data_entry_flow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from custom_components.mittfortum.config_flow import (
    CannotConnect,
    ConfigFlow,
    InvalidAuth,
    validate_input,
)
from custom_components.mittfortum.exceptions import AuthenticationError, MittFortumError


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return Mock(spec=HomeAssistant)


@pytest.fixture
def config_flow(mock_hass):
    """Create a config flow instance."""
    flow = ConfigFlow()
    flow.hass = mock_hass
    return flow


class TestMittFortumConfigFlow:
    """Test MittFortum config flow."""

    async def test_form_step_user(self, config_flow):
        """Test user step shows form."""
        result = await config_flow.async_step_user()

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    @patch("custom_components.mittfortum.config_flow.validate_input")
    async def test_form_step_user_valid_credentials(self, mock_validate, config_flow):
        """Test user step with valid credentials."""
        mock_validate.return_value = {"title": "MittFortum (test_user)"}

        user_input = {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
        }

        with (
            patch.object(config_flow, "async_set_unique_id") as mock_set_id,
            patch.object(config_flow, "_abort_if_unique_id_configured"),
        ):
            result = await config_flow.async_step_user(user_input)

            assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert result["title"] == "MittFortum (test_user)"
            assert result["data"] == user_input
            mock_set_id.assert_called_once_with("test_user")

    @patch("custom_components.mittfortum.config_flow.validate_input")
    async def test_form_step_user_invalid_credentials(self, mock_validate, config_flow):
        """Test user step with invalid credentials."""
        mock_validate.side_effect = InvalidAuth()

        user_input = {
            CONF_USERNAME: "invalid_user",
            CONF_PASSWORD: "invalid_password",
        }

        result = await config_flow.async_step_user(user_input)

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "invalid_auth"}

    @patch("custom_components.mittfortum.config_flow.validate_input")
    async def test_form_step_user_connection_error(self, mock_validate, config_flow):
        """Test user step with connection error."""
        mock_validate.side_effect = CannotConnect()

        user_input = {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
        }

        result = await config_flow.async_step_user(user_input)

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "cannot_connect"}

    @patch("custom_components.mittfortum.config_flow.validate_input")
    async def test_form_step_user_unexpected_error(self, mock_validate, config_flow):
        """Test user step with unexpected error."""
        mock_validate.side_effect = Exception("Unexpected error")

        user_input = {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
        }

        result = await config_flow.async_step_user(user_input)

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        assert result["errors"] == {"base": "unknown"}


class TestValidateInput:
    """Test validate_input function."""

    @patch("custom_components.mittfortum.config_flow.OAuth2AuthClient")
    @patch("custom_components.mittfortum.config_flow.FortumAPIClient")
    async def test_validate_input_success(
        self, mock_api_client_class, mock_auth_client_class, mock_hass
    ):
        """Test successful validation."""
        mock_auth_client = AsyncMock()
        mock_auth_client_class.return_value = mock_auth_client

        mock_api_client = AsyncMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client.get_customer_id.return_value = "12345"

        data = {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
        }

        result = await validate_input(mock_hass, data)
        assert result["title"] == "MittFortum (test_user)"

    @patch("custom_components.mittfortum.config_flow.OAuth2AuthClient")
    @patch("custom_components.mittfortum.config_flow.FortumAPIClient")
    async def test_validate_input_auth_error(
        self, mock_api_client_class, mock_auth_client_class, mock_hass
    ):
        """Test validation with authentication error."""
        mock_auth_client = AsyncMock()
        mock_auth_client_class.return_value = mock_auth_client

        mock_api_client = AsyncMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client.get_customer_id.side_effect = AuthenticationError(
            "Invalid credentials"
        )

        data = {
            CONF_USERNAME: "invalid_user",
            CONF_PASSWORD: "invalid_password",
        }

        with pytest.raises(InvalidAuth):
            await validate_input(mock_hass, data)

    @patch("custom_components.mittfortum.config_flow.OAuth2AuthClient")
    @patch("custom_components.mittfortum.config_flow.FortumAPIClient")
    async def test_validate_input_api_error(
        self, mock_api_client_class, mock_auth_client_class, mock_hass
    ):
        """Test validation with API error."""
        mock_auth_client = AsyncMock()
        mock_auth_client_class.return_value = mock_auth_client

        mock_api_client = AsyncMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client.get_customer_id.side_effect = MittFortumError("API error")

        data = {
            CONF_USERNAME: "test_user",
            CONF_PASSWORD: "test_password",
        }

        with pytest.raises(CannotConnect):
            await validate_input(mock_hass, data)
