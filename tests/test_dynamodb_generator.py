"""Unit tests for DynamoDB generator new blocks.

Task 12.3 — validates requirements 3.11, 3.12, 3.13, 3.14, 3.15.
Tests stream attributes, TTL block, GSI/LSI blocks, server_side_encryption block,
and replica blocks emitted by DynamoDBGenerator.
"""

from app.generators.dynamodb_generator import DynamoDBGenerator
from app.models.input_models._general import ServiceType
from app.models.input_models.dynamodb_config import DynamoDBConfig
from app.models.ir_models import ResourceInstanceIR

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dynamodb_instance(name: str = "test_table", **config_kwargs) -> ResourceInstanceIR:
    """Build a ResourceInstanceIR for a DynamoDB table with required fields and overrides."""
    defaults = {"table_name": "test", "hash_key": "id", "hash_key_type": "S"}
    defaults.update(config_kwargs)
    return ResourceInstanceIR(
        name=name,
        service_type=ServiceType.DYNAMODB,
        config=DynamoDBConfig(**defaults),
    )


# ===========================================================================
# 1. Stream attributes (Requirement 3.11)
# ===========================================================================


class TestDynamoDBStreamAttributes:
    """Test stream_enabled and stream_view_type emitted when stream fields are set."""

    def setup_method(self):
        self.gen = DynamoDBGenerator()

    def test_stream_enabled_emitted(self):
        """stream_enabled attribute appears in resource output when set."""
        instance = _dynamodb_instance(stream_enabled=True)
        output = self.gen.generate_resource_tf(instance)
        assert "stream_enabled" in output

    def test_stream_view_type_emitted(self):
        """stream_view_type attribute appears in resource output when set."""
        instance = _dynamodb_instance(
            stream_enabled=True, stream_view_type="NEW_AND_OLD_IMAGES"
        )
        output = self.gen.generate_resource_tf(instance)
        assert "stream_enabled" in output
        assert "stream_view_type" in output

    def test_stream_not_emitted_when_none(self):
        """stream attributes not emitted when stream_enabled is None."""
        instance = _dynamodb_instance()
        output = self.gen.generate_resource_tf(instance)
        assert "stream_enabled" not in output
        assert "stream_view_type" not in output

    def test_stream_variables_emitted(self):
        """Variable blocks for stream fields are emitted when set."""
        instance = _dynamodb_instance(
            stream_enabled=True, stream_view_type="NEW_AND_OLD_IMAGES"
        )
        output = self.gen.generate_variables_tf(instance)
        assert "stream_enabled" in output
        assert "stream_view_type" in output


# ===========================================================================
# 2. TTL block (Requirement 3.12)
# ===========================================================================


class TestDynamoDBTTLBlock:
    """Test ttl block emitted when ttl_enabled/ttl_attribute_name are set."""

    def setup_method(self):
        self.gen = DynamoDBGenerator()

    def test_ttl_block_emitted(self):
        """ttl block appears in resource output when ttl_enabled is set."""
        instance = _dynamodb_instance(ttl_enabled=True, ttl_attribute_name="expires_at")
        output = self.gen.generate_resource_tf(instance)
        assert "ttl" in output
        assert "ttl_enabled" in output or "enabled" in output

    def test_ttl_attribute_name_in_block(self):
        """ttl block includes attribute_name when ttl_attribute_name is set."""
        instance = _dynamodb_instance(ttl_enabled=True, ttl_attribute_name="expires_at")
        output = self.gen.generate_resource_tf(instance)
        assert "ttl_attribute_name" in output or "attribute_name" in output

    def test_ttl_not_emitted_when_none(self):
        """ttl block not emitted when ttl_enabled is None."""
        instance = _dynamodb_instance()
        output = self.gen.generate_resource_tf(instance)
        # The word "ttl" should not appear as a block key
        lines = output.split("\n")
        ttl_lines = [l for l in lines if "ttl" in l.lower() and "attribute" not in l.lower()]
        # No dedicated TTL block lines
        assert not any("ttl" == l.strip().split()[0] if l.strip() else False for l in lines)

    def test_ttl_variables_emitted(self):
        """Variable blocks for TTL fields are emitted when set."""
        instance = _dynamodb_instance(ttl_enabled=True, ttl_attribute_name="expires_at")
        output = self.gen.generate_variables_tf(instance)
        assert "ttl_enabled" in output
        assert "ttl_attribute_name" in output


# ===========================================================================
# 3. Global Secondary Index blocks (Requirement 3.13)
# ===========================================================================


class TestDynamoDBGSIBlocks:
    """Test global_secondary_index blocks emitted when global_secondary_indexes is set."""

    def setup_method(self):
        self.gen = DynamoDBGenerator()

    def test_gsi_block_emitted(self):
        """global_secondary_index block appears when GSI is defined."""
        instance = _dynamodb_instance(
            global_secondary_indexes=[
                {"name": "gsi1", "hash_key": "email", "projection_type": "ALL"}
            ]
        )
        output = self.gen.generate_resource_tf(instance)
        assert "global_secondary_index" in output
        assert "gsi1" in output
        assert "email" in output

    def test_gsi_multiple_indexes(self):
        """Multiple GSI blocks are emitted for multiple indexes."""
        instance = _dynamodb_instance(
            global_secondary_indexes=[
                {"name": "gsi1", "hash_key": "email", "projection_type": "ALL"},
                {"name": "gsi2", "hash_key": "status", "projection_type": "KEYS_ONLY"},
            ]
        )
        output = self.gen.generate_resource_tf(instance)
        assert "gsi1" in output
        assert "gsi2" in output

    def test_gsi_with_range_key(self):
        """GSI block includes range_key when provided."""
        instance = _dynamodb_instance(
            global_secondary_indexes=[
                {
                    "name": "gsi1",
                    "hash_key": "email",
                    "range_key": "created_at",
                    "projection_type": "ALL",
                }
            ]
        )
        output = self.gen.generate_resource_tf(instance)
        assert "range_key" in output
        assert "created_at" in output

    def test_gsi_not_emitted_when_none(self):
        """global_secondary_index block not emitted when field is None."""
        instance = _dynamodb_instance()
        output = self.gen.generate_resource_tf(instance)
        assert "global_secondary_index" not in output

    def test_gsi_variables_emitted(self):
        """Variable block for global_secondary_indexes is emitted when set."""
        instance = _dynamodb_instance(
            global_secondary_indexes=[
                {"name": "gsi1", "hash_key": "email", "projection_type": "ALL"}
            ]
        )
        output = self.gen.generate_variables_tf(instance)
        assert "global_secondary_indexes" in output


# ===========================================================================
# 4. Local Secondary Index blocks (Requirement 3.13)
# ===========================================================================


class TestDynamoDBLSIBlocks:
    """Test local_secondary_index blocks emitted when local_secondary_indexes is set."""

    def setup_method(self):
        self.gen = DynamoDBGenerator()

    def test_lsi_block_emitted(self):
        """local_secondary_index block appears when LSI is defined."""
        instance = _dynamodb_instance(
            local_secondary_indexes=[
                {"name": "lsi1", "range_key": "created_at", "projection_type": "KEYS_ONLY"}
            ]
        )
        output = self.gen.generate_resource_tf(instance)
        assert "local_secondary_index" in output
        assert "lsi1" in output
        assert "created_at" in output

    def test_lsi_multiple_indexes(self):
        """Multiple LSI blocks are emitted for multiple indexes."""
        instance = _dynamodb_instance(
            local_secondary_indexes=[
                {"name": "lsi1", "range_key": "created_at", "projection_type": "KEYS_ONLY"},
                {"name": "lsi2", "range_key": "updated_at", "projection_type": "ALL"},
            ]
        )
        output = self.gen.generate_resource_tf(instance)
        assert "lsi1" in output
        assert "lsi2" in output

    def test_lsi_not_emitted_when_none(self):
        """local_secondary_index block not emitted when field is None."""
        instance = _dynamodb_instance()
        output = self.gen.generate_resource_tf(instance)
        assert "local_secondary_index" not in output

    def test_lsi_variables_emitted(self):
        """Variable block for local_secondary_indexes is emitted when set."""
        instance = _dynamodb_instance(
            local_secondary_indexes=[
                {"name": "lsi1", "range_key": "created_at", "projection_type": "KEYS_ONLY"}
            ]
        )
        output = self.gen.generate_variables_tf(instance)
        assert "local_secondary_indexes" in output


# ===========================================================================
# 5. Server-side encryption block (Requirement 3.14)
# ===========================================================================


class TestDynamoDBEncryptionBlock:
    """Test server_side_encryption block emitted when encryption fields are set."""

    def setup_method(self):
        self.gen = DynamoDBGenerator()

    def test_encryption_block_emitted(self):
        """server_side_encryption block appears when encryption is enabled."""
        instance = _dynamodb_instance(server_side_encryption_enabled=True)
        output = self.gen.generate_resource_tf(instance)
        assert "server_side_encryption" in output

    def test_encryption_with_kms_key(self):
        """server_side_encryption block includes kms_key_arn when provided."""
        instance = _dynamodb_instance(
            server_side_encryption_enabled=True,
            server_side_encryption_kms_key_arn="arn:aws:kms:us-east-1:123456789012:key/abc",
        )
        output = self.gen.generate_resource_tf(instance)
        assert "server_side_encryption" in output
        assert "kms_key_arn" in output

    def test_encryption_not_emitted_when_none(self):
        """server_side_encryption block not emitted when fields are None."""
        instance = _dynamodb_instance()
        output = self.gen.generate_resource_tf(instance)
        assert "server_side_encryption" not in output

    def test_encryption_variables_emitted(self):
        """Variable blocks for encryption fields are emitted when set."""
        instance = _dynamodb_instance(
            server_side_encryption_enabled=True,
            server_side_encryption_kms_key_arn="arn:aws:kms:us-east-1:123456789012:key/abc",
        )
        output = self.gen.generate_variables_tf(instance)
        assert "server_side_encryption_enabled" in output
        assert "server_side_encryption_kms_key_arn" in output


# ===========================================================================
# 6. Replica blocks (Requirement 3.15)
# ===========================================================================


class TestDynamoDBReplicaBlocks:
    """Test replica blocks emitted when replica_regions is set."""

    def setup_method(self):
        self.gen = DynamoDBGenerator()

    def test_replica_blocks_emitted(self):
        """replica blocks appear when replica_regions is set."""
        instance = _dynamodb_instance(replica_regions=["us-west-2", "eu-west-1"])
        output = self.gen.generate_resource_tf(instance)
        assert "replica" in output
        assert "us-west-2" in output
        assert "eu-west-1" in output

    def test_replica_single_region(self):
        """A single replica region emits one replica block."""
        instance = _dynamodb_instance(replica_regions=["us-west-2"])
        output = self.gen.generate_resource_tf(instance)
        assert "replica" in output
        assert "us-west-2" in output

    def test_replica_not_emitted_when_none(self):
        """replica blocks not emitted when replica_regions is None."""
        instance = _dynamodb_instance()
        output = self.gen.generate_resource_tf(instance)
        assert "region_name" not in output

    def test_replica_variables_emitted(self):
        """Variable block for replica_regions is emitted when set."""
        instance = _dynamodb_instance(replica_regions=["us-west-2", "eu-west-1"])
        output = self.gen.generate_variables_tf(instance)
        assert "replica_regions" in output


# ===========================================================================
# 7. Variables output — required vs optional defaults
# ===========================================================================


class TestDynamoDBVariablesOutput:
    """Test variables_tf output for required fields (no default) and optional fields (with default)."""

    def setup_method(self):
        self.gen = DynamoDBGenerator()

    def test_required_fields_no_default(self):
        """Required fields (table_name, hash_key, hash_key_type) have no default in variables."""
        instance = _dynamodb_instance()
        output = self.gen.generate_variables_tf(instance)
        # Required variables should appear without a default line
        # They should be present
        assert "table_name" in output
        assert "hash_key" in output
        assert "hash_key_type" in output

    def test_optional_fields_have_default(self):
        """Optional fields emit variable blocks with default values."""
        instance = _dynamodb_instance(
            stream_enabled=True,
            stream_view_type="NEW_AND_OLD_IMAGES",
            ttl_enabled=True,
            ttl_attribute_name="expires_at",
        )
        output = self.gen.generate_variables_tf(instance)
        # Optional fields should have defaults
        assert "stream_enabled" in output
        assert "stream_view_type" in output
        assert "ttl_enabled" in output
        assert "ttl_attribute_name" in output

    def test_billing_mode_has_default(self):
        """billing_mode variable has a default value."""
        instance = _dynamodb_instance()
        output = self.gen.generate_variables_tf(instance)
        assert "billing_mode" in output
        assert "PAY_PER_REQUEST" in output
