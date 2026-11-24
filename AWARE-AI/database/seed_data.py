"""
AWARE-AI — Database Seeding Script.
Populates realistic baseline enterprise supply chain data:
- Global maritime ports (coordinates, codes, countries)
- Strategic suppliers with category, reliability, and lead time profiles
- Critical inventory components (SKUs, safety stock, reorder point, unit costs)
- Active & historical shipments with route geolocations, cargo details, and initial status
- Weather evidence records
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from database.connection import DatabaseManager
from database.crud import (
    InventoryCRUD,
    PortCRUD,
    ShipmentCRUD,
    SupplierCRUD,
    WeatherCRUD,
)
from database.models import (
    Inventory,
    Port,
    PriorityLevel,
    Shipment,
    ShipmentStatus,
    Supplier,
    WeatherEvidence,
    WeatherSeverity,
)


def seed_database(db: DatabaseManager | None = None) -> None:
    if db is None:
        db = DatabaseManager()
    db.init()

    with db.session() as session:
        # Check if already seeded
        from database.models import Port
        existing_ports = session.query(Port).count()
        if existing_ports >= 10:
            print(f"Database already contains {existing_ports} port records. Verifying other tables...")
        else:
            ports_data = [
                {"name": "Port of Shanghai", "code": "CNSHA", "country": "China", "latitude": 31.2304, "longitude": 121.4737},
                {"name": "Port of Singapore", "code": "SGSIN", "country": "Singapore", "latitude": 1.2902, "longitude": 103.8519},
                {"name": "Port of Rotterdam", "code": "NLRTM", "country": "Netherlands", "latitude": 51.9244, "longitude": 4.4777},
                {"name": "Port of Los Angeles", "code": "USLAX", "country": "United States", "latitude": 33.7432, "longitude": -118.2673},
                {"name": "Port of Hamburg", "code": "DEHAM", "country": "Germany", "latitude": 53.5488, "longitude": 9.9872},
                {"name": "Port of Tokyo", "code": "JPTYO", "country": "Japan", "latitude": 35.6197, "longitude": 139.7788},
                {"name": "Port of Busan", "code": "KRPUS", "country": "South Korea", "latitude": 35.1028, "longitude": 129.0403},
                {"name": "Port of Jebel Ali", "code": "AEJEA", "country": "United Arab Emirates", "latitude": 25.0113, "longitude": 55.0617},
                {"name": "Port of Antwerp", "code": "BEANR", "country": "Belgium", "latitude": 51.2612, "longitude": 4.3986},
                {"name": "Port of Santos", "code": "BRSSZ", "country": "Brazil", "latitude": -23.9535, "longitude": -46.3339},
            ]
            for p in ports_data:
                existing = PortCRUD.get_by_code(session, p["code"])
                if not existing:
                    PortCRUD.create(session, **p)
            print("  ✓ Ensured 10 global maritime ports exist.")

    # Build port mapping
    port_map = {}
    with db.session() as session:
        for p in PortCRUD.list_all(session):
            port_map[p.code] = p.id

    # 2. Strategic Suppliers
    suppliers_data = [
        {"name": "Apex Semiconductor Ltd", "country": "Taiwan", "reliability_score": 0.88, "lead_time_days": 18, "category": "Semiconductors", "risk_tier": "low"},
        {"name": "Nordic Precision Motors", "country": "Germany", "reliability_score": 0.94, "lead_time_days": 14, "category": "Motors & Actuators", "risk_tier": "low"},
        {"name": "Pacific Battery Systems", "country": "South Korea", "reliability_score": 0.76, "lead_time_days": 25, "category": "Energy Storage", "risk_tier": "medium"},
        {"name": "Shenzhen Microelectronics", "country": "China", "reliability_score": 0.72, "lead_time_days": 21, "category": "Electronics", "risk_tier": "high"},
        {"name": "Rhine Valley Chemical Co", "country": "Netherlands", "reliability_score": 0.96, "lead_time_days": 10, "category": "Raw Materials", "risk_tier": "low"},
        {"name": "Kyoto Advanced Sensors", "country": "Japan", "reliability_score": 0.91, "lead_time_days": 15, "category": "Optics & Sensors", "risk_tier": "low"},
        {"name": "Global Poly-Resins Corp", "country": "United States", "reliability_score": 0.82, "lead_time_days": 16, "category": "Polymers", "risk_tier": "medium"},
    ]

    supplier_map = {}
    with db.session() as session:
        for s in suppliers_data:
            existing = session.query(Supplier).filter_by(name=s["name"]).first()
            if not existing:
                sup = SupplierCRUD.create(session, **s)
                supplier_map[s["name"]] = sup.id
            else:
                supplier_map[s["name"]] = existing.id
    print(f"  ✓ Ensured {len(supplier_map)} strategic suppliers.")

    # 3. Critical Inventory Items
    inventory_data = [
        {
            "sku": "SKU-MCU-8840",
            "product_name": "High-Efficiency Automotive MCU 32-Bit",
            "quantity_on_hand": 1850,
            "safety_stock": 2500,
            "reorder_point": 3000,
            "unit_cost": 48.50,
            "supplier_id": supplier_map["Apex Semiconductor Ltd"],
            "warehouse_location": "WH-US-WEST-A1",
        },
        {
            "sku": "SKU-BATT-950",
            "product_name": "Lithium-Ion Cell Pack 95kWh Modular",
            "quantity_on_hand": 420,
            "safety_stock": 600,
            "reorder_point": 800,
            "unit_cost": 1250.00,
            "supplier_id": supplier_map["Pacific Battery Systems"],
            "warehouse_location": "WH-EU-CENTRAL-B3",
        },
        {
            "sku": "SKU-SENS-410",
            "product_name": "LiDAR Array Optical Transceiver Module",
            "quantity_on_hand": 3100,
            "safety_stock": 2000,
            "reorder_point": 2400,
            "unit_cost": 115.00,
            "supplier_id": supplier_map["Kyoto Advanced Sensors"],
            "warehouse_location": "WH-ASIA-EAST-C2",
        },
        {
            "sku": "SKU-CHEM-204",
            "product_name": "High-Purity Fluoropolymer Resin 50kg Drum",
            "quantity_on_hand": 280,
            "safety_stock": 300,
            "reorder_point": 350,
            "unit_cost": 340.00,
            "supplier_id": supplier_map["Rhine Valley Chemical Co"],
            "warehouse_location": "WH-EU-NORTH-D1",
        },
        {
            "sku": "SKU-MOT-102",
            "product_name": "Brushless Servo Drive Actuator 48V",
            "quantity_on_hand": 1200,
            "safety_stock": 1000,
            "reorder_point": 1200,
            "unit_cost": 280.00,
            "supplier_id": supplier_map["Nordic Precision Motors"],
            "warehouse_location": "WH-US-EAST-E4",
        },
    ]

    with db.session() as session:
        for inv in inventory_data:
            existing = InventoryCRUD.get_by_sku(session, inv["sku"])
            if not existing:
                InventoryCRUD.create(session, **inv)
    print(f"  ✓ Ensured critical inventory SKUs exist.")

    # 4. Realistic Shipments
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    shipments_data = [
        {
            "tracking_id": "SHP-PAC-2026-001",
            "origin_port_id": port_map["CNSHA"],       # Shanghai
            "destination_port_id": port_map["USLAX"],  # Los Angeles
            "supplier_id": supplier_map["Apex Semiconductor Ltd"],
            "cargo_description": "Container 40ft: High-Efficiency Automotive MCUs (45,000 units)",
            "weight_kg": 18500.0,
            "status": ShipmentStatus.IN_TRANSIT,
            "priority": PriorityLevel.CRITICAL,
            "current_latitude": 28.50,
            "current_longitude": 175.20,
            "departure_date": now - timedelta(days=6),
            "estimated_arrival": now + timedelta(days=8),
        },
        {
            "tracking_id": "SHP-EUR-2026-002",
            "origin_port_id": port_map["SGSIN"],       # Singapore
            "destination_port_id": port_map["NLRTM"],  # Rotterdam
            "supplier_id": supplier_map["Pacific Battery Systems"],
            "cargo_description": "Hazmat Class 9: Lithium EV Battery Sub-modules",
            "weight_kg": 24000.0,
            "status": ShipmentStatus.IN_TRANSIT,
            "priority": PriorityLevel.HIGH,
            "current_latitude": 12.45,
            "current_longitude": 48.10,  # Gulf of Aden / Arabian Sea
            "departure_date": now - timedelta(days=10),
            "estimated_arrival": now + timedelta(days=12),
        },
        {
            "tracking_id": "SHP-ATL-2026-003",
            "origin_port_id": port_map["BEANR"],       # Antwerp
            "destination_port_id": port_map["USLAX"],  # Los Angeles
            "supplier_id": supplier_map["Nordic Precision Motors"],
            "cargo_description": "Precision Servo Actuators & Robotic Motors",
            "weight_kg": 14200.0,
            "status": ShipmentStatus.IN_TRANSIT,
            "priority": PriorityLevel.MEDIUM,
            "current_latitude": 38.20,
            "current_longitude": -45.60,
            "departure_date": now - timedelta(days=4),
            "estimated_arrival": now + timedelta(days=10),
        },
        {
            "tracking_id": "SHP-ASI-2026-004",
            "origin_port_id": port_map["JPTYO"],       # Tokyo
            "destination_port_id": port_map["CNSHA"],  # Shanghai
            "supplier_id": supplier_map["Kyoto Advanced Sensors"],
            "cargo_description": "Precision Optical Transceivers for Autonomous Vehicles",
            "weight_kg": 6800.0,
            "status": ShipmentStatus.PENDING,
            "priority": PriorityLevel.HIGH,
            "current_latitude": 35.6197,
            "current_longitude": 139.7788,
            "departure_date": now + timedelta(days=1),
            "estimated_arrival": now + timedelta(days=4),
        },
        {
            "tracking_id": "SHP-ME-2026-005",
            "origin_port_id": port_map["AEJEA"],       # Jebel Ali
            "destination_port_id": port_map["DEHAM"],  # Hamburg
            "supplier_id": supplier_map["Rhine Valley Chemical Co"],
            "cargo_description": "Specialty Chemical Catalysts & Resins",
            "weight_kg": 21500.0,
            "status": ShipmentStatus.DELIVERED,
            "priority": PriorityLevel.LOW,
            "current_latitude": 53.5488,
            "current_longitude": 9.9872,
            "departure_date": now - timedelta(days=22),
            "estimated_arrival": now - timedelta(days=2),
            "actual_arrival": now - timedelta(days=1),
        },
    ]

    with db.session() as session:
        for s in shipments_data:
            existing = ShipmentCRUD.get_by_tracking_id(session, s["tracking_id"])
            if not existing:
                ShipmentCRUD.create(
                    session,
                    **s,
                    changed_by="seed_system",
                    change_reason="Initial seed dataset",
                )
    print("  ✓ Ensured realistic enterprise maritime shipments exist.")

    # 5. Baseline Weather Evidence for key ports
    weather_data = [
        {
            "port_id": port_map["CNSHA"],
            "event_type": "Typhoon Warning - Strong Gale",
            "severity": WeatherSeverity.SEVERE,
            "description": "Tropical storm convergence outer bands causing 48 knot gusts and 4.2m swell waves.",
            "temperature_celsius": 24.5,
            "wind_speed_kmh": 68.0,
            "precipitation_mm": 42.0,
            "visibility_km": 4.5,
            "start_time": now - timedelta(hours=8),
            "end_time": now + timedelta(hours=36),
            "source": "Open-Meteo Global Marine",
        },
        {
            "port_id": port_map["NLRTM"],
            "event_type": "Dense Coastal Fog",
            "severity": WeatherSeverity.MODERATE,
            "description": "Vessel Traffic Service low visibility procedures in effect across Maasvlakte.",
            "temperature_celsius": 11.2,
            "wind_speed_kmh": 14.0,
            "precipitation_mm": 0.2,
            "visibility_km": 0.8,
            "start_time": now - timedelta(hours=4),
            "end_time": now + timedelta(hours=12),
            "source": "Open-Meteo Global Marine",
        },
    ]

    with db.session() as session:
        for w in weather_data:
            WeatherCRUD.create(session, **w)
    print("  ✓ Ensured baseline maritime weather evidence records.")

    print("\nDatabase seeding completed successfully.")


if __name__ == "__main__":
    seed_database()
