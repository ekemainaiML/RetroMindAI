import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.models import (
    OEMManufacturer,
    OEMMountingPoint,
    OEMRoutingPath,
    OEMSpecification,
    OEMVehicleModel,
)


def _clean_oem(db: Session) -> None:
    db.query(OEMRoutingPath).delete()
    db.query(OEMMountingPoint).delete()
    db.query(OEMSpecification).delete()
    db.query(OEMVehicleModel).delete()
    db.query(OEMManufacturer).delete()
    db.commit()


def _seed_dummy(db: Session) -> tuple[OEMManufacturer, OEMVehicleModel]:
    m = OEMManufacturer(name="Test Mfr", country="Testland")
    db.add(m)
    db.flush()
    vm = OEMVehicleModel(manufacturer_id=m.id, model_name="Test Model", vehicle_type="four_wheeler")
    db.add(vm)
    db.flush()
    db.commit()
    return m, vm


class TestOEMListManufacturers:
    def test_returns_list(self, auth_client: TestClient):
        resp = auth_client.get("/api/v1/oem/manufacturers")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_search(self, auth_client: TestClient):
        db = SessionLocal()
        try:
            _clean_oem(db)
            m1 = OEMManufacturer(name="Bajaj Auto")
            m2 = OEMManufacturer(name="Tata Motors")
            db.add_all([m1, m2])
            db.commit()
        finally:
            db.close()

        resp = auth_client.get("/api/v1/oem/manufacturers", params={"search": "Baj"})
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Bajaj Auto"


class TestOEMCreateManufacturer:
    @pytest.fixture(autouse=True)
    def _clean(self):
        db = SessionLocal()
        try:
            _clean_oem(db)
        finally:
            db.close()

    def test_create(self, auth_client: TestClient):
        resp = auth_client.post("/api/v1/oem/manufacturers", json={
            "name": "New Mfr",
            "country": "Japan",
            "founded_year": 1950,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "New Mfr"
        assert data["country"] == "Japan"
        assert data["founded_year"] == 1950

    def test_duplicate(self, auth_client: TestClient):
        auth_client.post("/api/v1/oem/manufacturers", json={"name": "Dup"})
        resp = auth_client.post("/api/v1/oem/manufacturers", json={"name": "Dup"})
        assert resp.status_code == 409

    def test_get(self, auth_client: TestClient):
        create_resp = auth_client.post("/api/v1/oem/manufacturers", json={"name": "Single"})
        mfr_id = create_resp.json()["id"]
        resp = auth_client.get(f"/api/v1/oem/manufacturers/{mfr_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Single"

    def test_update(self, auth_client: TestClient):
        create_resp = auth_client.post("/api/v1/oem/manufacturers", json={"name": "Old"})
        mfr_id = create_resp.json()["id"]
        resp = auth_client.put(f"/api/v1/oem/manufacturers/{mfr_id}", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_delete(self, auth_client: TestClient):
        create_resp = auth_client.post("/api/v1/oem/manufacturers", json={"name": "Delete"})
        mfr_id = create_resp.json()["id"]
        resp = auth_client.delete(f"/api/v1/oem/manufacturers/{mfr_id}")
        assert resp.status_code == 204
        resp = auth_client.get(f"/api/v1/oem/manufacturers/{mfr_id}")
        assert resp.status_code == 404

    def test_404(self, auth_client: TestClient):
        resp = auth_client.get("/api/v1/oem/manufacturers/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestOEMVehicleModels:
    @pytest.fixture(autouse=True)
    def _clean(self):
        db = SessionLocal()
        try:
            _clean_oem(db)
            _seed_dummy(db)
        finally:
            db.close()

    def test_list(self, auth_client: TestClient):
        resp = auth_client.get("/api/v1/oem/models")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_filter_by_type(self, auth_client: TestClient):
        db = SessionLocal()
        try:
            _clean_oem(db)
            m = OEMManufacturer(name="Mfr")
            db.add(m)
            db.flush()
            db.add(OEMVehicleModel(manufacturer_id=m.id, model_name="Car", vehicle_type="four_wheeler"))
            db.add(OEMVehicleModel(manufacturer_id=m.id, model_name="Bike", vehicle_type="motorcycle"))
            db.commit()
        finally:
            db.close()

        resp = auth_client.get("/api/v1/oem/models", params={"vehicle_type": "motorcycle"})
        assert len(resp.json()) == 1
        assert resp.json()[0]["model_name"] == "Bike"

    def test_create(self, auth_client: TestClient):
        mfr_id = auth_client.get("/api/v1/oem/models").json()[0]["manufacturer_id"]
        resp = auth_client.post("/api/v1/oem/models", json={
            "manufacturer_id": mfr_id,
            "model_name": "New Model",
            "vehicle_type": "scooter",
            "year_start": 2020,
        })
        assert resp.status_code == 201
        assert resp.json()["model_name"] == "New Model"

    def test_search(self, auth_client: TestClient):
        resp = auth_client.get("/api/v1/oem/search", params={"model": "Test Model"})
        data = resp.json()
        assert data["total"] >= 1

    def test_search_by_year(self, auth_client: TestClient):
        db = SessionLocal()
        try:
            _clean_oem(db)
            m = OEMManufacturer(name="Mfr")
            db.add(m)
            db.flush()
            db.add(OEMVehicleModel(manufacturer_id=m.id, model_name="V1", vehicle_type="car", year_start=2010, year_end=2015))
            db.add(OEMVehicleModel(manufacturer_id=m.id, model_name="V2", vehicle_type="car", year_start=2016, year_end=2022))
            db.commit()
        finally:
            db.close()

        resp = auth_client.get("/api/v1/oem/search", params={"year": 2012})
        assert resp.json()["total"] == 1
        assert resp.json()["models"][0]["model_name"] == "V1"


class TestOEMSpecifications:
    @pytest.fixture(autouse=True)
    def _clean(self):
        db = SessionLocal()
        try:
            _clean_oem(db)
            _seed_dummy(db)
        finally:
            db.close()

    def test_crud(self, auth_client: TestClient):
        vm_id = auth_client.get("/api/v1/oem/models").json()[0]["id"]

        resp = auth_client.post(f"/api/v1/oem/models/{vm_id}/specifications", json={
            "model_id": vm_id,
            "wheelbase_mm": 2400,
            "engine_cc": 1200,
        })
        assert resp.status_code == 201
        spec_id = resp.json()["id"]
        assert resp.json()["wheelbase_mm"] == 2400

        resp = auth_client.get(f"/api/v1/oem/models/{vm_id}/specifications")
        assert len(resp.json()) == 1

        resp = auth_client.put(f"/api/v1/oem/specifications/{spec_id}", json={"wheelbase_mm": 2500})
        assert resp.status_code == 200
        assert resp.json()["wheelbase_mm"] == 2500

        resp = auth_client.delete(f"/api/v1/oem/specifications/{spec_id}")
        assert resp.status_code == 204
        resp = auth_client.get(f"/api/v1/oem/models/{vm_id}/specifications")
        assert resp.json() == []


class TestOEMMountingPoints:
    @pytest.fixture(autouse=True)
    def _clean(self):
        db = SessionLocal()
        try:
            _clean_oem(db)
            _seed_dummy(db)
        finally:
            db.close()

    def test_crud(self, auth_client: TestClient):
        vm_id = auth_client.get("/api/v1/oem/models").json()[0]["id"]
        resp = auth_client.post(f"/api/v1/oem/models/{vm_id}/mounting-points", json={
            "model_id": vm_id,
            "point_name": "Engine Mount",
            "point_type": "engine",
            "position_x_mm": 100,
            "position_y_mm": 200,
            "torque_spec_nm": 45,
        })
        assert resp.status_code == 201
        point_id = resp.json()["id"]

        resp = auth_client.get(f"/api/v1/oem/models/{vm_id}/mounting-points")
        assert len(resp.json()) == 1

        resp = auth_client.delete(f"/api/v1/oem/mounting-points/{point_id}")
        assert resp.status_code == 204


class TestOEMRoutingPaths:
    @pytest.fixture(autouse=True)
    def _clean(self):
        db = SessionLocal()
        try:
            _clean_oem(db)
            _seed_dummy(db)
        finally:
            db.close()

    def test_crud(self, auth_client: TestClient):
        vm_id = auth_client.get("/api/v1/oem/models").json()[0]["id"]
        resp = auth_client.post(f"/api/v1/oem/models/{vm_id}/routing-paths", json={
            "model_id": vm_id,
            "path_name": "Main Rail LH",
            "path_type": "chassis_rail",
            "length_estimate_mm": 3400,
        })
        assert resp.status_code == 201
        path_id = resp.json()["id"]

        resp = auth_client.get(f"/api/v1/oem/models/{vm_id}/routing-paths")
        assert len(resp.json()) == 1

        resp = auth_client.put(f"/api/v1/oem/routing-paths/{path_id}", json={"length_estimate_mm": 3500})
        assert resp.status_code == 200
        assert resp.json()["length_estimate_mm"] == 3500

        resp = auth_client.delete(f"/api/v1/oem/routing-paths/{path_id}")
        assert resp.status_code == 204


class TestOEMAuthRequired:
    def test_401_on_missing_key(self, client: TestClient):
        endpoints = [
            ("POST", "/api/v1/oem/manufacturers"),
            ("POST", "/api/v1/oem/models"),
        ]
        for method, path in endpoints:
            resp = client.request(method, path)
            assert resp.status_code == 401, f"{method} {path} returned {resp.status_code}"


class TestOEMSeedData:
    @pytest.fixture(autouse=True)
    def _clean_and_seed(self):
        db = SessionLocal()
        try:
            _clean_oem(db)
            from seed_data.seed_oem import seed_oem_data
            seed_oem_data(db)
        finally:
            db.close()

    def test_seed_manufacturers_count(self, auth_client: TestClient):
        resp = auth_client.get("/api/v1/oem/manufacturers", params={"limit": 200})
        assert resp.status_code == 200
        assert len(resp.json()) >= 15

    def test_seed_models_have_specs(self, auth_client: TestClient):
        resp = auth_client.get("/api/v1/oem/models", params={"limit": 200})
        models = resp.json()
        with_specs = [m for m in models if m["spec_count"] > 0]
        assert len(with_specs) >= 10

    def test_seed_search_by_type(self, auth_client: TestClient):
        for vtype in ("three_wheeler", "scooter", "motorcycle", "four_wheeler", "commercial"):
            resp = auth_client.get("/api/v1/oem/search", params={"vehicle_type": vtype})
            assert resp.json()["total"] >= 1, f"no models for type={vtype}"

    def test_seed_mounting_points_exist(self, auth_client: TestClient):
        models_resp = auth_client.get("/api/v1/oem/models", params={"limit": 200})
        total_mp = 0
        total_rp = 0
        for vm in models_resp.json():
            mp_resp = auth_client.get(f"/api/v1/oem/models/{vm['id']}/mounting-points")
            rp_resp = auth_client.get(f"/api/v1/oem/models/{vm['id']}/routing-paths")
            total_mp += len(mp_resp.json())
            total_rp += len(rp_resp.json())
        assert total_mp >= 1, "no mounting points found in seed data"
        assert total_rp >= 1, "no routing paths found in seed data"
