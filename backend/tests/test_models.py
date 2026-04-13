import uuid
from datetime import UTC, datetime


class TestDeviceStatus:
    def test_device_status_values(self):
        from app.config import DeviceStatus

        assert DeviceStatus.AVAILABLE.value == "available"
        assert DeviceStatus.MAINTENANCE.value == "maintenance"
        assert DeviceStatus.UNAVAILABLE.value == "unavailable"


class TestUserRole:
    def test_user_role_values(self):
        from app.config import UserRole

        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"


class TestReservationStatus:
    def test_reservation_status_values(self):
        from app.config import ReservationStatus

        assert ReservationStatus.CONFIRMED.value == "confirmed"
        assert ReservationStatus.CANCELLED.value == "cancelled"
        assert ReservationStatus.COMPLETED.value == "completed"


class TestDeviceSchemaValidation:
    def test_device_create_valid(self):
        from app.schemas import DeviceCreate

        device = DeviceCreate(name="test", location="lab")
        assert device.name == "test"
        assert device.location == "lab"

    def test_device_update_partial(self):
        from app.schemas import DeviceUpdate

        device = DeviceUpdate(name="new name")
        assert device.name == "new name"
        assert device.description is None

    def test_device_schema_has_expected_fields(self):
        from app.schemas import DeviceCreate

        fields = DeviceCreate.model_fields.keys()
        assert "name" in fields
        assert "description" in fields
        assert "location" in fields
        assert "category" in fields


class TestUserSchemaValidation:
    def test_user_create_valid(self):
        from app.schemas import UserCreate

        user = UserCreate(keycloak_id="kc-123", email="test@test.com")
        assert user.keycloak_id == "kc-123"
        assert user.email == "test@test.com"

    def test_user_update_partial(self):
        from app.schemas import UserUpdate

        user = UserUpdate(name="new name")
        assert user.name == "new name"
        assert user.role is None

    def test_user_schema_has_expected_fields(self):
        from app.schemas import UserCreate

        fields = UserCreate.model_fields.keys()
        assert "keycloak_id" in fields
        assert "email" in fields
        assert "name" in fields
        assert "role" in fields


class TestReservationSchemaValidation:
    def test_reservation_create_valid(self):
        from app.schemas import ReservationCreate

        res = ReservationCreate(
            device_id=uuid.uuid4(),
            start_time=datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
            end_time=datetime(2026, 4, 15, 12, 0, tzinfo=UTC),
        )
        assert res.device_id is not None

    def test_reservation_update_partial(self):
        from app.schemas import ReservationUpdate

        res = ReservationUpdate(purpose="new purpose")
        assert res.purpose == "new purpose"

    def test_reservation_schema_has_expected_fields(self):
        from app.schemas import ReservationCreate

        fields = ReservationCreate.model_fields.keys()
        assert "device_id" in fields
        assert "start_time" in fields
        assert "end_time" in fields
        assert "purpose" in fields
        assert "user_id" not in fields


class TestResponseSchemas:
    def test_device_response_has_id(self):
        from app.schemas import DeviceResponse

        fields = DeviceResponse.model_fields.keys()
        assert "id" in fields
        assert "status" in fields
        assert "created_at" in fields

    def test_user_response_has_id(self):
        from app.schemas import UserResponse

        fields = UserResponse.model_fields.keys()
        assert "id" in fields
        assert "keycloak_id" in fields
        assert "created_at" in fields

    def test_reservation_response_has_id(self):
        from app.schemas import ReservationResponse

        fields = ReservationResponse.model_fields.keys()
        assert "id" in fields
        assert "status" in fields
        assert "created_at" in fields
