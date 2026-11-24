"""
AWARE-AI — Autonomous Base Agent Framework

Implements the fundamental perceive → decide → act cycle for all specialized agents.
Provides:
- Strict structured input and output typing.
- Transparent execution timing (milliseconds).
- Integrated SQLite agent execution audit trail logging (AgentExecution).
- Resilient exception catching and diagnostic reporting.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from database.connection import DatabaseManager
from database.crud import AgentExecutionCRUD
from database.models import AgentExecution, AgentTaskStatus
from utils.logger import get_logger


class BaseAgent(ABC):
    """
    Abstract foundation for all AWARE-AI autonomous agents.
    Enforces perceive → decide → act lifecycle with database tracking.
    """

    def __init__(self, name: str, db_manager: Optional[DatabaseManager] = None):
        self.name = name
        self.db = db_manager
        self.logger = get_logger(f"agent.{self.name}")

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full agent execution pipeline with timing, exception handling, and database audit logging.
        """
        task_type = context.get("task_type", "default_task")
        start_ts = time.time()
        start_dt = datetime.now(timezone.utc).replace(tzinfo=None)

        execution_record_id = None
        if self.db:
            try:
                with self.db.session() as session:
                    rec = AgentExecutionCRUD.create(
                        session,
                        agent_name=self.name,
                        task_type=task_type,
                        input_summary=json.dumps(context, default=str),
                        status=AgentTaskStatus.RUNNING,
                        started_at=start_dt,
                    )
                    execution_record_id = rec.id
            except Exception as e:
                self.logger.warning("Failed to initialize execution record: %s", e)

        try:
            self.logger.info("[%s] Beginning perceive cycle with context keys: %s", self.name, list(context.keys()))
            perception = self.perceive(context)

            self.logger.info("[%s] Beginning decide cycle", self.name)
            decision = self.decide(perception)

            self.logger.info("[%s] Beginning act cycle", self.name)
            action_result = self.act(decision)

            duration_ms = int((time.time() - start_ts) * 1000)

            final_output = {
                "agent_name": self.name,
                "task_type": task_type,
                "status": "completed",
                "duration_ms": duration_ms,
                "perception": perception,
                "decision": decision,
                "action_result": action_result,
                "executed_at": start_dt.isoformat(),
            }

            if self.db and execution_record_id:
                try:
                    with self.db.session() as session:
                        AgentExecutionCRUD.complete(
                            session,
                            execution_id=execution_record_id,
                            output_summary=json.dumps(action_result, default=str),
                        )
                except Exception as e:
                    self.logger.warning("Failed to finalize execution record: %s", e)

            return final_output

        except Exception as exc:
            duration_ms = int((time.time() - start_ts) * 1000)
            self.logger.error("[%s] Agent failed during execution: %s", self.name, exc, exc_info=True)

            error_summary = {
                "agent_name": self.name,
                "task_type": task_type,
                "status": "failed",
                "duration_ms": duration_ms,
                "error": str(exc),
                "executed_at": start_dt.isoformat(),
            }

            if self.db and execution_record_id:
                try:
                    with self.db.session() as session:
                        AgentExecutionCRUD.complete(
                            session,
                            execution_id=execution_record_id,
                            error_message=str(exc),
                        )
                except Exception as e:
                    self.logger.warning("Failed to record execution error: %s", e)

            return error_summary

    @abstractmethod
    def perceive(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Gather, parse, and structure empirical domain data and evidence."""

    @abstractmethod
    def decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Reason, classify, evaluate risk/causality, or formulate strategy."""

    @abstractmethod
    def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Persist state, dispatch alerts, generate reports, or execute actions."""
