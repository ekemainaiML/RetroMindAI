"""Seed the OEM database tables with common conversion vehicle models.

Call `seed_oem_data(db)` from app startup or run standalone.
"""

import logging

from sqlalchemy.orm import Session

from core.models import (
    OEMManufacturer,
    OEMMountingPoint,
    OEMRoutingPath,
    OEMSpecification,
    OEMVehicleModel,
)

logger = logging.getLogger(__name__)

_UPSEEDED_KEY = "_oem_seeded"


def seed_oem_data(db: Session) -> None:
    """Insert seed OEM data if the manufacturers table is empty."""
    if db.query(OEMManufacturer).count() > 0:
        logger.info("OEM seed data already present, skipping")
        return

    manufacturers: dict[str, OEMManufacturer] = {}

    def mfr(name: str, country: str | None = None, founded_year: int | None = None) -> OEMManufacturer:
        if name not in manufacturers:
            m = OEMManufacturer(name=name, country=country, founded_year=founded_year)
            db.add(m)
            db.flush()
            manufacturers[name] = m
        return manufacturers[name]

    def model(
        mfr_name: str,
        model_name: str,
        vehicle_type: str,
        generation: str | None = None,
        year_start: int | None = None,
        year_end: int | None = None,
    ) -> OEMVehicleModel:
        m = mfr(mfr_name)
        vm = OEMVehicleModel(
            manufacturer_id=m.id,
            model_name=model_name,
            generation=generation,
            vehicle_type=vehicle_type,
            year_start=year_start,
            year_end=year_end,
        )
        db.add(vm)
        db.flush()
        return vm

    def spec(
        vm: OEMVehicleModel,
        wheelbase_mm: int | None = None,
        overall_length_mm: int | None = None,
        overall_width_mm: int | None = None,
        overall_height_mm: int | None = None,
        ground_clearance_mm: int | None = None,
        cargo_length_mm: int | None = None,
        cargo_width_mm: int | None = None,
        kerb_weight_kg: int | None = None,
        gross_weight_kg: int | None = None,
        payload_kg: int | None = None,
        seating_capacity: int | None = None,
        engine_cc: int | None = None,
        fuel_type: str | None = None,
        notes: str | None = None,
    ) -> OEMSpecification:
        s = OEMSpecification(
            model_id=vm.id,
            wheelbase_mm=wheelbase_mm,
            overall_length_mm=overall_length_mm,
            overall_width_mm=overall_width_mm,
            overall_height_mm=overall_height_mm,
            ground_clearance_mm=ground_clearance_mm,
            cargo_length_mm=cargo_length_mm,
            cargo_width_mm=cargo_width_mm,
            kerb_weight_kg=kerb_weight_kg,
            gross_weight_kg=gross_weight_kg,
            payload_kg=payload_kg,
            seating_capacity=seating_capacity,
            engine_cc=engine_cc,
            fuel_type=fuel_type,
            notes=notes,
        )
        db.add(s)
        db.flush()
        return s

    def mounting_point(
        vm: OEMVehicleModel,
        point_name: str,
        point_type: str,
        x: int | None = None,
        y: int | None = None,
        z: int | None = None,
        bolt_pattern: str | None = None,
        torque_nm: int | None = None,
        notes: str | None = None,
    ) -> OEMMountingPoint:
        mp = OEMMountingPoint(
            model_id=vm.id,
            point_name=point_name,
            point_type=point_type,
            position_x_mm=x,
            position_y_mm=y,
            position_z_mm=z,
            bolt_pattern=bolt_pattern,
            torque_spec_nm=torque_nm,
            notes=notes,
        )
        db.add(mp)
        db.flush()
        return mp

    def routing_path(
        vm: OEMVehicleModel,
        path_name: str,
        path_type: str,
        start_point: str | None = None,
        end_point: str | None = None,
        length_mm: int | None = None,
        constraints: dict | None = None,
        notes: str | None = None,
    ) -> OEMRoutingPath:
        rp = OEMRoutingPath(
            model_id=vm.id,
            path_name=path_name,
            path_type=path_type,
            start_point=start_point,
            end_point=end_point,
            length_estimate_mm=length_mm,
            constraints=constraints or {},
            notes=notes,
        )
        db.add(rp)
        db.flush()
        return rp

    # ═══════════════════════════════════════════════════════════════════
    # THREE-WHEELERS — Auto Rickshaws & Cargo Tuk-tuks
    # ═══════════════════════════════════════════════════════════════════

    vm = model("Bajaj Auto", "RE 4S", "three_wheeler", generation="RE 4S", year_start=2010)
    spec(vm, wheelbase_mm=2230, overall_length_mm=3170, overall_width_mm=1440,
         overall_height_mm=1770, ground_clearance_mm=170, cargo_length_mm=900,
         cargo_width_mm=1300, kerb_weight_kg=360, gross_weight_kg=940,
         payload_kg=580, seating_capacity=3, engine_cc=116, fuel_type="petrol",
         notes="Most popular auto rickshaw model in India. Common EV conversion candidate.")
    mounting_point(vm, "Engine Mount Front", "engine", x=0, y=500, z=300, bolt_pattern="4xM10", torque_nm=45)
    mounting_point(vm, "Engine Mount Rear", "engine", x=0, y=1500, z=300, bolt_pattern="4xM10", torque_nm=45)
    mounting_point(vm, "Battery Tray Main", "battery", x=0, y=800, z=200)
    mounting_point(vm, "Rear Axle Mount", "suspension", x=0, y=2000, z=100, bolt_pattern="4xM12", torque_nm=80)
    routing_path(vm, "Main Chassis Rail LH", "chassis_rail", "Front bulkhead", "Rear crossmember", 2200,
                 {"section": "box 60x40mm", "material": "steel"})
    routing_path(vm, "Main Chassis Rail RH", "chassis_rail", "Front bulkhead", "Rear crossmember", 2200,
                 {"section": "box 60x40mm", "material": "steel"})
    routing_path(vm, "Underfloor Tunnel", "underbody_tunnel", "Engine bay", "Rear axle", 1800,
                 {"max_width": 200, "max_height": 150})

    vm = model("Bajaj Auto", "RE CNG", "three_wheeler", generation="RE CNG", year_start=2015)
    spec(vm, wheelbase_mm=2230, overall_length_mm=3170, overall_width_mm=1440,
         overall_height_mm=1770, ground_clearance_mm=170, cargo_length_mm=900,
         cargo_width_mm=1300, kerb_weight_kg=375, gross_weight_kg=940,
         payload_kg=565, seating_capacity=3, engine_cc=116, fuel_type="cng",
         notes="CNG variant of the Bajaj RE. Similar conversion approach to 4S.")

    vm = model("Bajaj Auto", "Maxima XL", "three_wheeler", year_start=2018)
    spec(vm, wheelbase_mm=2630, overall_length_mm=3468, overall_width_mm=1520,
         overall_height_mm=1800, ground_clearance_mm=180, cargo_length_mm=1200,
         cargo_width_mm=1400, kerb_weight_kg=430, gross_weight_kg=1035,
         payload_kg=605, seating_capacity=3, engine_cc=200, fuel_type="petrol",
         notes="Larger cargo three-wheeler. Battery placement in extended rear floor area.")
    mounting_point(vm, "Battery Tray Extended", "battery", x=0, y=700, z=150)
    mounting_point(vm, "Motor Mount LH", "engine", x=-200, y=1200, z=250)
    mounting_point(vm, "Motor Mount RH", "engine", x=200, y=1200, z=250)

    vm = model("Piaggio", "Ape 501", "three_wheeler", year_start=2010)
    spec(vm, wheelbase_mm=2160, overall_length_mm=3100, overall_width_mm=1450,
         overall_height_mm=1720, ground_clearance_mm=165, cargo_length_mm=1000,
         cargo_width_mm=1300, kerb_weight_kg=340, gross_weight_kg=900,
         payload_kg=560, seating_capacity=3, engine_cc=150, fuel_type="petrol")
    mounting_point(vm, "Engine Carrier", "engine", x=0, y=1000, z=350)
    mounting_point(vm, "Battery Compartment", "battery", x=0, y=600, z=150)
    routing_path(vm, "Chassis Spine Frame", "frame_spine", "Front", "Rear axle carrier", 2000,
                 {"section": "tube 50mm OD", "material": "steel"})

    vm = model("Piaggio", "Ape E-City", "three_wheeler", year_start=2020, year_end=2024)
    spec(vm, wheelbase_mm=2160, overall_length_mm=3100, overall_width_mm=1450,
         overall_height_mm=1720, ground_clearance_mm=165, cargo_length_mm=1000,
         cargo_width_mm=1300, kerb_weight_kg=400, gross_weight_kg=900,
         payload_kg=500, seating_capacity=3, fuel_type="electric",
         notes="Factory electric variant. Reference for OLA-style conversion specs.")

    vm = model("Mahindra & Mahindra", "Treo", "three_wheeler", year_start=2019)
    spec(vm, wheelbase_mm=2285, overall_length_mm=3200, overall_width_mm=1480,
         overall_height_mm=1805, ground_clearance_mm=175, cargo_length_mm=1200,
         cargo_width_mm=1350, kerb_weight_kg=610, gross_weight_kg=1080,
         payload_kg=470, seating_capacity=3, fuel_type="electric",
         notes="Factory electric from Mahindra. Good aftermarket conversion platform.")

    vm = model("Atul Auto", "Gemini", "three_wheeler", year_start=2015)
    spec(vm, wheelbase_mm=2250, overall_length_mm=3230, overall_width_mm=1470,
         overall_height_mm=1790, ground_clearance_mm=170, cargo_length_mm=1050,
         cargo_width_mm=1320, kerb_weight_kg=370, gross_weight_kg=950,
         payload_kg=580, seating_capacity=3, engine_cc=130, fuel_type="diesel")

    vm = model("Mahindra & Mahindra", "Jeeto", "three_wheeler", year_start=2017)
    spec(vm, wheelbase_mm=2300, overall_length_mm=3360, overall_width_mm=1500,
         overall_height_mm=1830, ground_clearance_mm=175, cargo_length_mm=1350,
         cargo_width_mm=1440, kerb_weight_kg=490, gross_weight_kg=1050,
         payload_kg=560, seating_capacity=2, engine_cc=330, fuel_type="diesel",
         notes="Popular cargo three-wheeler with flat bed. Good EV conversion candidate for last-mile delivery.")
    mounting_point(vm, "Battery Tray Mid", "battery", x=0, y=900, z=150)
    mounting_point(vm, "Rear Axle Mount", "suspension", x=0, y=2000, z=120)

    vm = model("Bajaj Auto", "Compact RE", "three_wheeler", year_start=2020)
    spec(vm, wheelbase_mm=2000, overall_length_mm=2850, overall_width_mm=1350,
         overall_height_mm=1700, ground_clearance_mm=165, cargo_length_mm=700,
         cargo_width_mm=1200, kerb_weight_kg=310, gross_weight_kg=800,
         payload_kg=490, seating_capacity=3, engine_cc=116, fuel_type="petrol",
         notes="Compact auto rickshaw for narrow streets. Lightweight conversion platform.")

    # ═══════════════════════════════════════════════════════════════════
    # ELECTRIC TWO-WHEELERS — Modern EV Scooters (for reference)
    # ═══════════════════════════════════════════════════════════════════

    vm = model("Ola Electric", "S1 Pro", "scooter", year_start=2021)
    spec(vm, wheelbase_mm=1300, overall_length_mm=1860, overall_width_mm=710,
         overall_height_mm=1140, ground_clearance_mm=165, kerb_weight_kg=125,
         seating_capacity=2, fuel_type="electric",
         notes="Factory electric scooter. Reference for battery pack layout and motor specs.")

    vm = model("Ather Energy", "450X", "scooter", year_start=2020)
    spec(vm, wheelbase_mm=1275, overall_length_mm=1850, overall_width_mm=710,
         overall_height_mm=1140, ground_clearance_mm=155, kerb_weight_kg=118,
         seating_capacity=2, fuel_type="electric",
         notes="Premium electric scooter. Reference for lithium-ion battery packaging.")

    vm = model("Bajaj Auto", "Chetak", "scooter", year_start=2020)
    spec(vm, wheelbase_mm=1260, overall_length_mm=1850, overall_width_mm=710,
         overall_height_mm=1160, ground_clearance_mm=160, kerb_weight_kg=130,
         seating_capacity=2, fuel_type="electric",
         notes="Re-launched as electric. Good reference for vintage EV conversion.")

    # ═══════════════════════════════════════════════════════════════════
    # TWO-WHEELERS — Scooters & Motorcycles
    # ═══════════════════════════════════════════════════════════════════

    vm = model("Honda Motorcycle & Scooter India", "Activa 6G", "scooter", year_start=2021)
    spec(vm, wheelbase_mm=1260, overall_length_mm=1835, overall_width_mm=710,
         overall_height_mm=1170, ground_clearance_mm=170, kerb_weight_kg=108,
         seating_capacity=2, engine_cc=110, fuel_type="petrol",
         notes="India's best-selling scooter. Underseat battery pack conversion common.")
    mounting_point(vm, "Engine Swingarm", "engine", x=0, y=600, z=300)
    mounting_point(vm, "Underseat Tray", "battery", x=0, y=400, z=500)
    routing_path(vm, "Frame Spine", "frame_spine", "Steering head", "Swingarm pivot", 1200,
                 {"section": "tube 35mm OD", "material": "steel"})

    vm = model("Honda Motorcycle & Scooter India", "Activa 3G", "scooter", year_start=2013, year_end=2018)
    spec(vm, wheelbase_mm=1260, overall_length_mm=1828, overall_width_mm=702,
         overall_height_mm=1156, ground_clearance_mm=165, kerb_weight_kg=106,
         seating_capacity=2, engine_cc=109, fuel_type="petrol")

    vm = model("Hero MotoCorp", "Splendor Plus", "motorcycle", year_start=2015)
    spec(vm, wheelbase_mm=1240, overall_length_mm=2000, overall_width_mm=740,
         overall_height_mm=1060, ground_clearance_mm=165, kerb_weight_kg=112,
         seating_capacity=2, engine_cc=97, fuel_type="petrol",
         notes="World's best-selling motorcycle. Hub motor conversion fits rear wheel.")
    mounting_point(vm, "Engine Mount Front", "engine", x=0, y=600, z=250)
    mounting_point(vm, "Engine Mount Rear", "engine", x=0, y=1100, z=250)

    vm = model("Hero MotoCorp", "Splendor iSmart", "motorcycle", year_start=2019)
    spec(vm, wheelbase_mm=1240, overall_length_mm=2000, overall_width_mm=740,
         overall_height_mm=1060, ground_clearance_mm=165, kerb_weight_kg=113,
         seating_capacity=2, engine_cc=100, fuel_type="petrol")

    vm = model("TVS Motor Company", "Jupiter", "scooter", year_start=2015)
    spec(vm, wheelbase_mm=1275, overall_length_mm=1850, overall_width_mm=720,
         overall_height_mm=1180, ground_clearance_mm=170, kerb_weight_kg=109,
         seating_capacity=2, engine_cc=110, fuel_type="petrol")
    mounting_point(vm, "Rear Hub Motor Mount", "battery", x=0, y=700, z=300)

    vm = model("TVS Motor Company", "iQube", "scooter", year_start=2020)
    spec(vm, wheelbase_mm=1280, overall_length_mm=1880, overall_width_mm=730,
         overall_height_mm=1200, ground_clearance_mm=170, kerb_weight_kg=118,
         seating_capacity=2, fuel_type="electric",
         notes="TVS factory electric. Reference platform for aftermarket conversion.")

    vm = model("Suzuki Motorcycle India", "Access 125", "scooter", year_start=2015)
    spec(vm, wheelbase_mm=1265, overall_length_mm=1840, overall_width_mm=705,
         overall_height_mm=1160, ground_clearance_mm=170, kerb_weight_kg=103,
         seating_capacity=2, engine_cc=124, fuel_type="petrol")

    vm = model("Bajaj Auto", "Pulsar 150", "motorcycle", year_start=2010)
    spec(vm, wheelbase_mm=1320, overall_length_mm=2035, overall_width_mm=755,
         overall_height_mm=1135, ground_clearance_mm=165, kerb_weight_kg=140,
         seating_capacity=2, engine_cc=149, fuel_type="petrol",
         notes="Popular commuter motorcycle. Mid-drive conversion fits engine bay.")

    # ═══════════════════════════════════════════════════════════════════
    # FOUR-WHEELERS — Compact cars & SUVs
    # ═══════════════════════════════════════════════════════════════════

    vm = model("Maruti Suzuki", "Alto 800", "four_wheeler", year_start=2012)
    spec(vm, wheelbase_mm=2360, overall_length_mm=3455, overall_width_mm=1505,
         overall_height_mm=1475, ground_clearance_mm=160, kerb_weight_kg=725,
         gross_weight_kg=1160, payload_kg=435, seating_capacity=4, engine_cc=796,
         fuel_type="petrol",
         notes="India's most popular entry-level car. Common DIY EV conversion target.")
    mounting_point(vm, "Engine Mount LH", "engine", x=-200, y=800, z=400, bolt_pattern="3xM10")
    mounting_point(vm, "Engine Mount RH", "engine", x=200, y=800, z=400, bolt_pattern="3xM10")
    mounting_point(vm, "Transmission Mount", "engine", x=0, y=1200, z=350)
    mounting_point(vm, "Battery Tray Front", "battery", x=0, y=400, z=200)
    mounting_point(vm, "Battery Tray Rear", "battery", x=0, y=1500, z=150)
    routing_path(vm, "Chassis Rail LH", "chassis_rail", "Front bumper", "Rear crossmember", 3400,
                 {"section": "hat 100x50mm", "material": "steel", "wall_thickness_mm": 1.5})
    routing_path(vm, "Chassis Rail RH", "chassis_rail", "Front bumper", "Rear crossmember", 3400,
                 {"section": "hat 100x50mm", "material": "steel", "wall_thickness_mm": 1.5})
    routing_path(vm, "Transmission Tunnel", "underbody_tunnel", "Engine bay", "Rear seat", 1400,
                 {"max_width": 250, "max_height": 180})

    vm = model("Maruti Suzuki", "Alto K10", "four_wheeler", year_start=2015)
    spec(vm, wheelbase_mm=2360, overall_length_mm=3455, overall_width_mm=1505,
         overall_height_mm=1475, ground_clearance_mm=160, kerb_weight_kg=745,
         gross_weight_kg=1160, payload_kg=415, seating_capacity=5, engine_cc=998,
         fuel_type="petrol")

    vm = model("Tata Motors", "Nano", "four_wheeler", year_start=2009, year_end=2019)
    spec(vm, wheelbase_mm=2230, overall_length_mm=3099, overall_width_mm=1495,
         overall_height_mm=1652, ground_clearance_mm=180, kerb_weight_kg=635,
         gross_weight_kg=950, payload_kg=315, seating_capacity=4, engine_cc=624,
         fuel_type="petrol",
         notes="World's cheapest car; rear engine. Excellent EV conversion candidate due to light weight and rear layout.")
    mounting_point(vm, "Engine Mount Front", "engine", x=0, y=400, z=350)
    mounting_point(vm, "Engine Mount Rear", "engine", x=0, y=900, z=350)
    routing_path(vm, "Chassis Rail LH", "chassis_rail", "Front crossmember", "Rear crossmember", 3000)
    routing_path(vm, "Chassis Rail RH", "chassis_rail", "Front crossmember", "Rear crossmember", 3000)

    vm = model("Tata Motors", "Tiago", "four_wheeler", year_start=2016)
    spec(vm, wheelbase_mm=2400, overall_length_mm=3747, overall_width_mm=1647,
         overall_height_mm=1535, ground_clearance_mm=170, kerb_weight_kg=830,
         gross_weight_kg=1310, payload_kg=480, seating_capacity=5, engine_cc=1199,
         fuel_type="petrol",
         notes="Popular hatchback. Front-engine layout, good underhood space for motor.")
    mounting_point(vm, "Engine Mount LH", "engine", x=-150, y=700, z=380)
    mounting_point(vm, "Engine Mount RH", "engine", x=150, y=700, z=380)
    mounting_point(vm, "Battery Tray Underfloor", "battery", x=0, y=1600, z=100)

    vm = model("Renault", "Kwid", "four_wheeler", year_start=2015)
    spec(vm, wheelbase_mm=2422, overall_length_mm=3679, overall_width_mm=1579,
         overall_height_mm=1478, ground_clearance_mm=180, kerb_weight_kg=790,
         gross_weight_kg=1180, payload_kg=390, seating_capacity=5, engine_cc=799,
         fuel_type="petrol",
         notes="Popular entry-level hatchback with good ground clearance for battery underfloor.")

    vm = model("Datsun", "redi-GO", "four_wheeler", year_start=2016, year_end=2020)
    spec(vm, wheelbase_mm=2422, overall_length_mm=3428, overall_width_mm=1560,
         overall_height_mm=1564, ground_clearance_mm=185, kerb_weight_kg=726,
         seating_capacity=4, engine_cc=799, fuel_type="petrol",
         notes="Lightweight entry-level car. Similar platform to Renault Kwid.")

    vm = model("Mahindra & Mahindra", "Scorpio N", "four_wheeler", year_start=2022)
    spec(vm, wheelbase_mm=2770, overall_length_mm=4662, overall_width_mm=1917,
         overall_height_mm=1857, ground_clearance_mm=180, kerb_weight_kg=1900,
         gross_weight_kg=2500, payload_kg=600, seating_capacity=7, engine_cc=2198,
         fuel_type="diesel",
         notes="Popular ladder-frame SUV. Excellent for conversion due to body-on-frame construction.")
    mounting_point(vm, "Front Subframe Mount LH", "frame", x=-400, y=600, z=350, bolt_pattern="4xM12")
    mounting_point(vm, "Front Subframe Mount RH", "frame", x=400, y=600, z=350, bolt_pattern="4xM12")
    mounting_point(vm, "Transfer Case Mount", "engine", x=0, y=1400, z=500)
    mounting_point(vm, "Rear Axle Spring Mount", "suspension", x=0, y=2600, z=200)
    routing_path(vm, "Ladder Frame LH", "chassis_rail", "Front bumper", "Rear crossmember", 4500,
                 {"section": "C-channel 150x50mm", "material": "steel", "wall_thickness_mm": 3.0})
    routing_path(vm, "Ladder Frame RH", "chassis_rail", "Front bumper", "Rear crossmember", 4500,
                 {"section": "C-channel 150x50mm", "material": "steel", "wall_thickness_mm": 3.0})
    routing_path(vm, "Propeller Shaft Tunnel", "underbody_tunnel", "Transfer case", "Rear differential", 2200,
                 {"max_width": 300, "max_height": 200})

    vm = model("Toyota", "Fortuner", "four_wheeler", year_start=2015)
    spec(vm, wheelbase_mm=2745, overall_length_mm=4630, overall_width_mm=1845,
         overall_height_mm=1820, ground_clearance_mm=200, kerb_weight_kg=1900,
         gross_weight_kg=2500, payload_kg=600, seating_capacity=7, engine_cc=2694,
         fuel_type="diesel",
         notes="Popular ladder-frame SUV. Large engine bay accommodates EV motor easily.")
    mounting_point(vm, "Front Subframe", "frame", x=0, y=500, z=400)
    mounting_point(vm, "Engine Mount LH", "engine", x=-250, y=700, z=450)
    mounting_point(vm, "Engine Mount RH", "engine", x=250, y=700, z=450)
    routing_path(vm, "Ladder Frame LH", "chassis_rail", "Front crossmember", "Rear crossmember", 4600)
    routing_path(vm, "Ladder Frame RH", "chassis_rail", "Front crossmember", "Rear crossmember", 4600)

    vm = model("Maruti Suzuki", "Wagon R", "four_wheeler", year_start=2013)
    spec(vm, wheelbase_mm=2400, overall_length_mm=3595, overall_width_mm=1475,
         overall_height_mm=1640, ground_clearance_mm=170, kerb_weight_kg=800,
         seating_capacity=5, engine_cc=998, fuel_type="petrol",
         notes="Tall-boy design offers good packaging flexibility for battery.")
    mounting_point(vm, "Battery Tray Underfloor", "battery", x=0, y=1200, z=100)

    vm = model("Hyundai", "i10", "four_wheeler", year_start=2013)
    spec(vm, wheelbase_mm=2425, overall_length_mm=3595, overall_width_mm=1550,
         overall_height_mm=1500, ground_clearance_mm=160, kerb_weight_kg=805,
         seating_capacity=5, engine_cc=1086, fuel_type="petrol")

    vm = model("Honda", "City", "four_wheeler", year_start=2014)
    spec(vm, wheelbase_mm=2550, overall_length_mm=4395, overall_width_mm=1695,
         overall_height_mm=1480, ground_clearance_mm=165, kerb_weight_kg=1045,
         seating_capacity=5, engine_cc=1497, fuel_type="petrol",
         notes="Popular sedan. Mid-size package good for conversion.")

    vm = model("Maruti Suzuki", "Swift", "four_wheeler", year_start=2011)
    spec(vm, wheelbase_mm=2430, overall_length_mm=3840, overall_width_mm=1535,
         overall_height_mm=1515, ground_clearance_mm=160, kerb_weight_kg=855,
         seating_capacity=5, engine_cc=1197, fuel_type="petrol",
         notes="Popular hatchback. Good conversion candidate.")

    vm = model("Maruti Suzuki", "Eeco", "four_wheeler", year_start=2015)
    spec(vm, wheelbase_mm=2430, overall_length_mm=3660, overall_width_mm=1465,
         overall_height_mm=1665, ground_clearance_mm=155, cargo_length_mm=1400,
         cargo_width_mm=1300, kerb_weight_kg=865, gross_weight_kg=1400,
         payload_kg=535, seating_capacity=5, engine_cc=1197, fuel_type="petrol",
         notes="Budget MPV/van. Popular for passenger and cargo use. Large interior volume good for battery.")
    mounting_point(vm, "Battery Tray Underfloor", "battery", x=0, y=1400, z=100)
    mounting_point(vm, "Engine Mount LH", "engine", x=-180, y=700, z=350)
    mounting_point(vm, "Engine Mount RH", "engine", x=180, y=700, z=350)
    routing_path(vm, "Chassis Rail LH", "chassis_rail", "Front crossmember", "Rear crossmember", 3600,
                 {"section": "hat 90x45mm", "material": "steel"})
    routing_path(vm, "Chassis Rail RH", "chassis_rail", "Front crossmember", "Rear crossmember", 3600,
                 {"section": "hat 90x45mm", "material": "steel"})

    vm = model("Tata Motors", "Safari", "four_wheeler", year_start=2021)
    spec(vm, wheelbase_mm=2720, overall_length_mm=4612, overall_width_mm=1880,
         overall_height_mm=1760, ground_clearance_mm=210, kerb_weight_kg=1780,
         gross_weight_kg=2350, payload_kg=570, seating_capacity=7, engine_cc=1956,
         fuel_type="diesel",
         notes="Popular ladder-frame SUV from Tata. Extensive conversion space in engine bay and underbody.")
    mounting_point(vm, "Front Subframe", "frame", x=0, y=500, z=420)
    mounting_point(vm, "Engine Mount LH", "engine", x=-200, y=800, z=400)
    mounting_point(vm, "Engine Mount RH", "engine", x=200, y=800, z=400)
    mounting_point(vm, "Battery Tray Mid", "battery", x=0, y=1600, z=150)
    routing_path(vm, "Chassis Rail LH", "chassis_rail", "Front crossmember", "Rear crossmember", 4600,
                 {"section": "C-channel 140x50mm", "material": "steel"})
    routing_path(vm, "Chassis Rail RH", "chassis_rail", "Front crossmember", "Rear crossmember", 4600,
                 {"section": "C-channel 140x50mm", "material": "steel"})

    vm = model("MG Motor India", "ZS EV", "four_wheeler", year_start=2020)
    spec(vm, wheelbase_mm=2585, overall_length_mm=4323, overall_width_mm=1809,
         overall_height_mm=1620, ground_clearance_mm=180, kerb_weight_kg=1560,
         seating_capacity=5, fuel_type="electric",
         notes="Factory electric compact SUV. Reference for 44.5kWh battery pack and motor layout.")

    vm = model("Tata Motors", "Nexon EV", "four_wheeler", year_start=2022)
    spec(vm, wheelbase_mm=2498, overall_length_mm=3993, overall_width_mm=1804,
         overall_height_mm=1612, ground_clearance_mm=205, kerb_weight_kg=1400,
         seating_capacity=5, fuel_type="electric",
         notes="India's best-selling factory EV. Reference for 40.5kWh battery and front motor.")

    # ═══════════════════════════════════════════════════════════════════
    # COMMERCIAL / UTILITY
    # ═══════════════════════════════════════════════════════════════════

    vm = model("Mahindra & Mahindra", "Bolero", "four_wheeler", year_start=2010)
    spec(vm, wheelbase_mm=2680, overall_length_mm=4330, overall_width_mm=1745,
         overall_height_mm=1910, ground_clearance_mm=190, cargo_length_mm=1300,
         cargo_width_mm=1300, kerb_weight_kg=1460, gross_weight_kg=2100,
         payload_kg=640, seating_capacity=7, engine_cc=2523, fuel_type="diesel",
         notes="Popular ladder-frame utility SUV. Strong conversion candidate in rural areas.")
    mounting_point(vm, "Front Bumper Mount", "frame", x=0, y=200, z=400)

    vm = model("Tata Motors", "Ace", "commercial", year_start=2010)
    spec(vm, wheelbase_mm=2000, overall_length_mm=3420, overall_width_mm=1480,
         overall_height_mm=1830, ground_clearance_mm=180, cargo_length_mm=1640,
         cargo_width_mm=1420, kerb_weight_kg=665, gross_weight_kg=1350,
         payload_kg=685, seating_capacity=2, engine_cc=700, fuel_type="diesel",
         notes="India's most popular mini-truck. Ideal for cargo EV conversion.")
    mounting_point(vm, "Battery Tray Mid", "battery", x=0, y=900, z=120)
    mounting_point(vm, "Motor Mount Front", "engine", x=0, y=500, z=350)
    mounting_point(vm, "Motor Mount Rear", "engine", x=0, y=1100, z=350)
    routing_path(vm, "Chassis Rail LH", "chassis_rail", "Front bumper", "Rear crossmember", 3400,
                 {"section": "C-channel 100x40mm", "material": "steel"})
    routing_path(vm, "Chassis Rail RH", "chassis_rail", "Front bumper", "Rear crossmember", 3400,
                 {"section": "C-channel 100x40mm", "material": "steel"})

    vm = model("Tata Motors", "Super Ace", "commercial", year_start=2012)
    spec(vm, wheelbase_mm=2400, overall_length_mm=4040, overall_width_mm=1520,
         overall_height_mm=1890, ground_clearance_mm=185, cargo_length_mm=2000,
         cargo_width_mm=1480, kerb_weight_kg=980, gross_weight_kg=1900,
         payload_kg=920, seating_capacity=2, engine_cc=1400, fuel_type="diesel",
         notes="Larger mini-truck with more payload. Good candidate for commercial EV conversion fleet.")
    mounting_point(vm, "Battery Tray Underfloor", "battery", x=0, y=1200, z=150)
    mounting_point(vm, "Motor Mount LH", "engine", x=-200, y=700, z=400)
    mounting_point(vm, "Motor Mount RH", "engine", x=200, y=700, z=400)

    vm = model("Mahindra & Mahindra", "Maxximo", "commercial", year_start=2013)
    spec(vm, wheelbase_mm=2150, overall_length_mm=3400, overall_width_mm=1500,
         overall_height_mm=1870, ground_clearance_mm=175, cargo_length_mm=1700,
         cargo_width_mm=1440, kerb_weight_kg=720, gross_weight_kg=1450,
         payload_kg=730, seating_capacity=2, engine_cc=909, fuel_type="diesel",
         notes="Popular mini cargo van. Compact dimensions with good payload.")
    mounting_point(vm, "Battery Tray Rear", "battery", x=0, y=1700, z=100)

    vm = model("Ashok Leyland", "DOST", "commercial", year_start=2016)
    spec(vm, wheelbase_mm=2515, overall_length_mm=4740, overall_width_mm=1700,
         overall_height_mm=1995, ground_clearance_mm=190, cargo_length_mm=2260,
         cargo_width_mm=1620, kerb_weight_kg=1130, gross_weight_kg=2250,
         payload_kg=1120, seating_capacity=2, engine_cc=1478, fuel_type="diesel",
         notes="Light commercial vehicle with high payload. Strong EV conversion candidate for logistics fleets.")

    # ═══════════════════════════════════════════════════════════════════
    # ADDITIONAL POPULAR MOTORCYCLES
    # ═══════════════════════════════════════════════════════════════════

    vm = model("Bajaj Auto", "CT 100", "motorcycle", year_start=2010)
    spec(vm, wheelbase_mm=1270, overall_length_mm=2010, overall_width_mm=740,
         overall_height_mm=1070, ground_clearance_mm=165, kerb_weight_kg=116,
         seating_capacity=2, engine_cc=102, fuel_type="petrol",
         notes="High-volume commuter motorcycle. Hub motor conversion platform.")

    vm = model("Hero MotoCorp", "HF Deluxe", "motorcycle", year_start=2015)
    spec(vm, wheelbase_mm=1240, overall_length_mm=1985, overall_width_mm=720,
         overall_height_mm=1060, ground_clearance_mm=165, kerb_weight_kg=111,
         seating_capacity=2, engine_cc=97, fuel_type="petrol",
         notes="Popular commuter motorcycle. Lightweight platform.")

    vm = model("TVS Motor Company", "Apache RTR 160", "motorcycle", year_start=2016)
    spec(vm, wheelbase_mm=1300, overall_length_mm=2035, overall_width_mm=790,
         overall_height_mm=1090, ground_clearance_mm=165, kerb_weight_kg=137,
         seating_capacity=2, engine_cc=159, fuel_type="petrol",
         notes="Sporty commuter motorcycle. Good hub motor conversion candidate.")

    # ═══════════════════════════════════════════════════════════════════
    # ADDITIONAL THREE-WHEELER PASSENGER VARIANTS
    # ═══════════════════════════════════════════════════════════════════

    vm = model("Mahindra & Mahindra", "Alfa", "three_wheeler", year_start=2016)
    spec(vm, wheelbase_mm=2300, overall_length_mm=3350, overall_width_mm=1480,
         overall_height_mm=1800, ground_clearance_mm=170, cargo_length_mm=1200,
         cargo_width_mm=1350, kerb_weight_kg=420, gross_weight_kg=1000,
         payload_kg=580, seating_capacity=3, engine_cc=225, fuel_type="diesel",
         notes="Three-wheeler passenger variant. Similar to Bajaj RE, well-suited for conversion.")

    # Commit all seed data
    db.commit()
    logger.info("Seeded %d manufacturers with %d vehicle models, specs, mounting points, and routing paths",
                len(manufacturers), db.query(OEMVehicleModel).count())
