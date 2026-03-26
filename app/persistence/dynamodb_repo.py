"""DynamoDB implementation of the AbstractRepository interface."""

import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

from app.persistence.base import AbstractRepository
from app.persistence.models import DiagramRecord, DiagramSummary, UserRecord


class DynamoDBRepository(AbstractRepository):
    """Repository backed by AWS DynamoDB.

    Uses two tables:
    - ``Users`` (partition key: ``session_id``)
    - ``Diagrams`` (partition key: ``diagram_id``, GSI ``session_id-index`` on ``session_id``)

    Table names are configurable via constructor params.
    """

    def __init__(
        self,
        *,
        users_table_name: str = "Users",
        diagrams_table_name: str = "Diagrams",
        session_index_name: str = "session_id-index",
        endpoint_url: str | None = None,
        region_name: str | None = None,
    ) -> None:
        kwargs: dict = {}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        if region_name:
            kwargs["region_name"] = region_name

        dynamodb = boto3.resource("dynamodb", **kwargs)
        self._users_table = dynamodb.Table(users_table_name)
        self._diagrams_table = dynamodb.Table(diagrams_table_name)
        self._session_index_name = session_index_name

    # ------------------------------------------------------------------
    # User operations
    # ------------------------------------------------------------------

    def create_user(self, session_id: str) -> UserRecord:
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "session_id": session_id,
            "created_at": now,
            "last_active": now,
        }
        self._users_table.put_item(Item=item)
        return UserRecord(**item)

    def get_user(self, session_id: str) -> UserRecord | None:
        response = self._users_table.get_item(Key={"session_id": session_id})
        item = response.get("Item")
        if not item:
            return None
        return UserRecord(**item)

    def update_user_last_active(self, session_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._users_table.update_item(
            Key={"session_id": session_id},
            UpdateExpression="SET last_active = :ts",
            ExpressionAttributeValues={":ts": now},
        )

    # ------------------------------------------------------------------
    # Diagram operations
    # ------------------------------------------------------------------

    def save_diagram(self, session_id: str, diagram: dict) -> str:
        diagram_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "diagram_id": diagram_id,
            "session_id": session_id,
            "project_name": diagram.get("projectName", ""),
            "diagram_state": diagram,
            "created_at": now,
            "updated_at": now,
        }
        self._diagrams_table.put_item(Item=item)
        return diagram_id

    def get_diagram(self, diagram_id: str) -> DiagramRecord | None:
        response = self._diagrams_table.get_item(Key={"diagram_id": diagram_id})
        item = response.get("Item")
        if not item:
            return None
        return DiagramRecord(**item)

    def list_diagrams(self, session_id: str) -> list[DiagramSummary]:
        response = self._diagrams_table.query(
            IndexName=self._session_index_name,
            KeyConditionExpression=Key("session_id").eq(session_id),
        )
        return [
            DiagramSummary(
                diagram_id=item["diagram_id"],
                project_name=item["project_name"],
                updated_at=item["updated_at"],
            )
            for item in response.get("Items", [])
        ]

    def update_diagram(self, diagram_id: str, diagram: dict) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        response = self._diagrams_table.update_item(
            Key={"diagram_id": diagram_id},
            UpdateExpression="SET diagram_state = :ds, project_name = :pn, updated_at = :ts",
            ConditionExpression="attribute_exists(diagram_id)",
            ExpressionAttributeValues={
                ":ds": diagram,
                ":pn": diagram.get("projectName", ""),
                ":ts": now,
            },
            ReturnValues="ALL_NEW",
        )
        return "Attributes" in response

    def delete_diagram(self, diagram_id: str) -> bool:
        try:
            self._diagrams_table.delete_item(
                Key={"diagram_id": diagram_id},
                ConditionExpression="attribute_exists(diagram_id)",
            )
            return True
        except self._diagrams_table.meta.client.exceptions.ConditionalCheckFailedException:
            return False
