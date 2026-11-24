"""
Unit tests for Supplier Reliability Analysis and Scoring Engine.
"""

import pytest

from database.crud import PortCRUD, ShipmentCRUD, SupplierCRUD
from modules.supplier.intelligence import SupplierIntelligence
from modules.supplier.scoring import SupplierScorer


@pytest.fixture
def supplier_with_shipment_history(db):
    with db.session() as s:
        p1 = PortCRUD.create(s, name="Origin", code="ORG01", country="A", latitude=0, longitude=0)
        p2 = PortCRUD.create(s, name="Dest", code="DST01", country="B", latitude=1, longitude=1)
        supplier = SupplierCRUD.create(
            s, name="Pacific Parts Ltd", country="Japan",
            contact_email="parts@pacific.jp", reliability_score=0.90,
            lead_time_days=15,
        )
        sup_id = supplier.id

        # Create 2 delivered shipments and 1 delayed shipment
        s1 = ShipmentCRUD.create(s, tracking_id="TR-DELIV-1", origin_port_id=p1.id, destination_port_id=p2.id, supplier_id=sup_id)
        ShipmentCRUD.update_status(s, s1.id, "delivered")

        s2 = ShipmentCRUD.create(s, tracking_id="TR-DELIV-2", origin_port_id=p1.id, destination_port_id=p2.id, supplier_id=sup_id)
        ShipmentCRUD.update_status(s, s2.id, "delivered")

        s3 = ShipmentCRUD.create(s, tracking_id="TR-DELAY-1", origin_port_id=p1.id, destination_port_id=p2.id, supplier_id=sup_id)
        ShipmentCRUD.update_status(s, s3.id, "delayed")

        return sup_id


class TestSupplierScoringAndIntelligence:
    def test_new_supplier_returns_baseline_provenance(self, db):
        with db.session() as s:
            supplier = SupplierCRUD.create(
                s, name="New Supplier Corp", country="Vietnam",
                reliability_score=0.88, lead_time_days=20,
            )
            sid = supplier.id

        scorer = SupplierScorer(db)
        eval_data = scorer.compute_score(sid)

        assert eval_data["supplier_id"] == sid
        assert eval_data["data_provenance"]["source"] == "SUPPLIER_INITIAL_PROFILE"
        assert eval_data["data_provenance"]["evidence_shipment_count"] == 0
        assert eval_data["metrics"]["completed_shipments"] == 0

    def test_empirical_scoring_with_shipment_history(self, db, supplier_with_shipment_history):
        sup_id = supplier_with_shipment_history
        scorer = SupplierScorer(db)

        eval_data = scorer.compute_score(sup_id)

        assert eval_data["data_provenance"]["source"] == "EMPIRICAL_SHIPMENT_HISTORY"
        assert eval_data["data_provenance"]["evidence_shipment_count"] == 3
        assert eval_data["metrics"]["completed_shipments"] == 2
        assert eval_data["metrics"]["delayed_shipments"] == 1
        assert eval_data["metrics"]["on_time_delivery_rate"] == pytest.approx(0.667, abs=0.01)

        # Ensure database is updated with calculated score
        with db.session() as s:
            sup = SupplierCRUD.get(s, sup_id)
            assert sup.reliability_score == eval_data["reliability_score"]

    def test_find_alternative_suppliers(self, db):
        with db.session() as s:
            s1 = SupplierCRUD.create(s, name="Main S1", country="Korea", category="Electronics", reliability_score=0.50)
            s2 = SupplierCRUD.create(s, name="Alt S2", country="Korea", category="Electronics", reliability_score=0.95, lead_time_days=10)
            s3 = SupplierCRUD.create(s, name="Alt S3", country="Germany", category="Automotive", reliability_score=0.80, lead_time_days=25)
            s1_id = s1.id

        intel = SupplierIntelligence(db)
        alternatives = intel.find_alternatives(s1_id)

        assert len(alternatives) >= 2
        # Highest ranked alternative should be Alt S2 due to category match and high score
        assert alternatives[0]["name"] == "Alt S2"
        assert alternatives[0]["category_match"] is True
