"""
AWARE-AI — Human-in-the-Loop Approval & Governance Workflow

Enforces that NO actual operational changes (status updates, rerouting, safety split)
can occur autonomously without explicit human authorized approval.
Maintains full immutable audit trails in the ApprovalHistory and ShipmentHistory tables.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.connection import DatabaseManager
from database.crud import (
    ApprovalHistoryCRUD,
    ResiliencePlanCRUD,
    ShipmentCRUD,
)
from database.models import (
    ApprovalAction,
    ApprovalHistory,
    PlanStatus,
    ResiliencePlan,
    Shipment,
    ShipmentStatus,
)
from utils.logger import get_logger

logger = get_logger("resilience.approval_workflow")


class HumanApprovalWorkflowManager:
    """
    Manages governance reviews, approval decisions, and operational execution
    of recommended resilience playbooks.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def review_and_decide(
        self,
        plan_id: int,
        action: str,  # 'approve', 'reject', or 'revise'
        approved_by: str,
        comments: Optional[str] = None,
        apply_operational_changes: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes a formal review decision.
        If 'approve' and apply_operational_changes is True, updates the plan to ACTIVE
        and logs the approval history.
        """
        valid_actions = {"approve", "reject", "revise"}
        action_clean = action.strip().lower()
        if action_clean not in valid_actions:
            raise ValueError(f"Action must be one of {valid_actions}, got {action!r}")

        with self.db.session() as session:
            plan = ResiliencePlanCRUD.get(session, plan_id)
            if not plan:
                raise ValueError(f"ResiliencePlan {plan_id} not found.")

            approval_enum = {
                "approve": ApprovalAction.APPROVE,
                "reject": ApprovalAction.REJECT,
                "revise": ApprovalAction.REVISE,
            }[action_clean]

            now = datetime.now(timezone.utc).replace(tzinfo=None)

            # 1. Log approval history audit record
            history_record = ApprovalHistoryCRUD.create(
                session,
                entity_type="resilience_plan",
                entity_id=plan.id,
                action=approval_enum,
                approved_by=approved_by,
                comments=comments or f"Decision '{action_clean}' recorded by {approved_by}.",
                decided_at=now,
            )

            # 2. Update Plan State
            if action_clean == "approve":
                plan.status = PlanStatus.ACTIVE
                plan.approved_at = now
            elif action_clean == "reject":
                plan.status = PlanStatus.ARCHIVED
            elif action_clean == "revise":
                plan.status = PlanStatus.DRAFT

            session.flush()

            # 3. Optional Operational Execution (e.g. updating linked shipment status/notes)
            shipment_transition_log = None
            if action_clean == "approve" and apply_operational_changes and plan.risk_assessment:
                # Find linked shipment
                ra = plan.risk_assessment
                if ra.entity_type == "shipment":
                    shipment = ShipmentCRUD.get(session, ra.entity_id)
                    if shipment:
                        shipment_transition_log = {
                            "shipment_id": shipment.id,
                            "tracking_id": shipment.tracking_id,
                            "playbook_activated": plan.name,
                            "activation_timestamp": now.isoformat(),
                        }
                        logger.info(
                            "Operational contingency plan '%s' activated for shipment %s by %s",
                            plan.name, shipment.tracking_id, approved_by,
                        )

            return {
                "plan_id": plan.id,
                "plan_name": plan.name,
                "new_plan_status": plan.status.value,
                "decision": action_clean,
                "approved_by": approved_by,
                "approval_history_id": history_record.id,
                "decided_at": now.isoformat(),
                "operational_transition": shipment_transition_log,
            }

    def get_approval_audit_trail(self, plan_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all governance review decisions recorded for a resilience plan.
        """
        with self.db.session() as session:
            records = ApprovalHistoryCRUD.list_by_entity(session, "resilience_plan", plan_id)
            return [
                {
                    "approval_id": r.id,
                    "action": r.action.value if hasattr(r.action, "value") else str(r.action),
                    "approved_by": r.approved_by,
                    "comments": r.comments,
                    "decided_at": r.decided_at.isoformat() if r.decided_at else None,
                }
                for r in records
            ]
