import * as THREE from 'three';
import type { VehicleDimensions, Deviation3D, RetrofitComponent3D } from '@/types/assessment';

const SCALE = 1 / 1000;

function makeMaterials() {
  const bodyMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.7, metalness: 0.1 });
  const accentMat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.6, metalness: 0.2 });
  const wheelMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.9 });
  const rimMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.4, metalness: 0.6 });
  const glassMat = new THREE.MeshStandardMaterial({ color: 0x7dd3fc, transparent: true, opacity: 0.3, roughness: 0.1, metalness: 0.0 });
  const bedMat = new THREE.MeshStandardMaterial({ color: 0x78716c, roughness: 0.8, metalness: 0.0 });
  const seatMat = new THREE.MeshStandardMaterial({ color: 0x292524, roughness: 0.9 });
  const headlightMat = new THREE.MeshStandardMaterial({ color: 0xfef9c3, emissive: 0xfef9c3, emissiveIntensity: 0.2 });
  const taillightMat = new THREE.MeshStandardMaterial({ color: 0xef4444, emissive: 0xef4444, emissiveIntensity: 0.1 });
  const handlebarMat = new THREE.MeshStandardMaterial({ color: 0x44403c, roughness: 0.5, metalness: 0.4 });
  return { bodyMat, accentMat, wheelMat, rimMat, glassMat, bedMat, seatMat, headlightMat, taillightMat, handlebarMat };
}

function addWheel(group: THREE.Group, x: number, z: number, wheelRadius: number, wheelThickness: number, wheelMat: THREE.MeshStandardMaterial, rimMat: THREE.MeshStandardMaterial) {
  const wheel = new THREE.Mesh(new THREE.CylinderGeometry(wheelRadius, wheelRadius, wheelThickness, 16), wheelMat);
  wheel.rotation.x = Math.PI / 2;
  wheel.position.set(x, wheelRadius, z);
  wheel.castShadow = true;
  group.add(wheel);

  const rim = new THREE.Mesh(new THREE.CylinderGeometry(wheelRadius * 0.4, wheelRadius * 0.4, wheelThickness * 1.02, 8), rimMat);
  rim.rotation.x = Math.PI / 2;
  rim.position.set(x, wheelRadius, z);
  group.add(rim);
}

export function buildRickshawModel(dimensions: VehicleDimensions): THREE.Group {
  const group = new THREE.Group();
  const l = Math.max(dimensions.length * SCALE, 0.1);
  const w = Math.max(dimensions.width * SCALE, 0.1);
  const h = Math.max(dimensions.height * SCALE, 0.1);
  const M = makeMaterials();

  const body = new THREE.Mesh(new THREE.BoxGeometry(l, h * 0.5, w * 0.9), M.bodyMat);
  body.position.set(0, h * 0.25, 0);
  body.castShadow = true;
  group.add(body);

  const cabin = new THREE.Mesh(new THREE.BoxGeometry(l * 0.35, h * 0.35, w * 0.85), M.accentMat);
  cabin.position.set(l * 0.2, h * 0.55, 0);
  cabin.castShadow = true;
  group.add(cabin);

  const windshield = new THREE.Mesh(new THREE.BoxGeometry(l * 0.01, h * 0.25, w * 0.7), M.glassMat);
  windshield.position.set(l * 0.38, h * 0.5, 0);
  group.add(windshield);

  const bed = new THREE.Mesh(new THREE.BoxGeometry(l * 0.55, h * 0.06, w * 0.85), M.bedMat);
  bed.position.set(-l * 0.15, h * 0.3, 0);
  bed.castShadow = true;
  group.add(bed);

  const wheelRadius = h * 0.2;
  const wheelThickness = w * 0.08;
  addWheel(group, -l * 0.2, w * 0.45, wheelRadius, wheelThickness, M.wheelMat, M.rimMat);
  addWheel(group, -l * 0.2, -w * 0.45, wheelRadius, wheelThickness, M.wheelMat, M.rimMat);
  addWheel(group, l * 0.35, 0, wheelRadius, wheelThickness, M.wheelMat, M.rimMat);

  return group;
}

function buildCarModel(dimensions: VehicleDimensions): THREE.Group {
  const group = new THREE.Group();
  const l = Math.max(dimensions.length * SCALE, 0.1);
  const w = Math.max(dimensions.width * SCALE, 0.1);
  const h = Math.max(dimensions.height * SCALE, 0.1);
  const M = makeMaterials();

  const body = new THREE.Mesh(new THREE.BoxGeometry(l, h * 0.5, w * 0.95), M.bodyMat);
  body.position.set(0, h * 0.25, 0);
  body.castShadow = true;
  group.add(body);

  const cabin = new THREE.Mesh(new THREE.BoxGeometry(l * 0.45, h * 0.35, w * 0.88), M.accentMat);
  cabin.position.set(l * 0.07, h * 0.57, 0);
  cabin.castShadow = true;
  group.add(cabin);

  const windshield = new THREE.Mesh(new THREE.BoxGeometry(l * 0.01, h * 0.28, w * 0.75), M.glassMat);
  windshield.position.set(l * 0.28, h * 0.53, 0);
  group.add(windshield);

  const rearWindow = new THREE.Mesh(new THREE.BoxGeometry(l * 0.01, h * 0.25, w * 0.75), M.glassMat);
  rearWindow.position.set(-l * 0.15, h * 0.52, 0);
  group.add(rearWindow);

  const hood = new THREE.Mesh(new THREE.BoxGeometry(l * 0.22, h * 0.02, w * 0.85), M.accentMat);
  hood.position.set(l * 0.36, h * 0.48, 0);
  group.add(hood);

  const trunk = new THREE.Mesh(new THREE.BoxGeometry(l * 0.18, h * 0.02, w * 0.85), M.accentMat);
  trunk.position.set(-l * 0.35, h * 0.48, 0);
  group.add(trunk);

  const headlightL = new THREE.Mesh(new THREE.BoxGeometry(l * 0.02, h * 0.08, w * 0.12), M.headlightMat);
  headlightL.position.set(l * 0.49, h * 0.28, w * 0.38);
  group.add(headlightL);
  const headlightR = new THREE.Mesh(new THREE.BoxGeometry(l * 0.02, h * 0.08, w * 0.12), M.headlightMat);
  headlightR.position.set(l * 0.49, h * 0.28, -w * 0.38);
  group.add(headlightR);

  const taillightL = new THREE.Mesh(new THREE.BoxGeometry(l * 0.02, h * 0.08, w * 0.12), M.taillightMat);
  taillightL.position.set(-l * 0.49, h * 0.28, w * 0.38);
  group.add(taillightL);
  const taillightR = new THREE.Mesh(new THREE.BoxGeometry(l * 0.02, h * 0.08, w * 0.12), M.taillightMat);
  taillightR.position.set(-l * 0.49, h * 0.28, -w * 0.38);
  group.add(taillightR);

  const wheelRadius = h * 0.18;
  const wheelThickness = w * 0.06;
  addWheel(group, l * 0.3, w * 0.46, wheelRadius, wheelThickness, M.wheelMat, M.rimMat);
  addWheel(group, l * 0.3, -w * 0.46, wheelRadius, wheelThickness, M.wheelMat, M.rimMat);
  addWheel(group, -l * 0.3, w * 0.46, wheelRadius, wheelThickness, M.wheelMat, M.rimMat);
  addWheel(group, -l * 0.3, -w * 0.46, wheelRadius, wheelThickness, M.wheelMat, M.rimMat);

  return group;
}

function buildMotorcycleModel(dimensions: VehicleDimensions): THREE.Group {
  const group = new THREE.Group();
  const l = Math.max(dimensions.length * SCALE, 0.1);
  const w = Math.max(dimensions.width * SCALE, 0.1);
  const h = Math.max(dimensions.height * SCALE, 0.1);
  const M = makeMaterials();

  const body = new THREE.Mesh(new THREE.BoxGeometry(l * 0.8, h * 0.15, w * 0.3), M.bodyMat);
  body.position.set(0, h * 0.15, 0);
  body.castShadow = true;
  group.add(body);

  const seat = new THREE.Mesh(new THREE.BoxGeometry(l * 0.3, h * 0.06, w * 0.28), M.seatMat);
  seat.position.set(l * 0.05, h * 0.28, 0);
  group.add(seat);

  const fuelTank = new THREE.Mesh(new THREE.BoxGeometry(l * 0.15, h * 0.12, w * 0.25), M.accentMat);
  fuelTank.position.set(l * 0.22, h * 0.28, 0);
  group.add(fuelTank);

  const handlebars = new THREE.Mesh(new THREE.BoxGeometry(l * 0.01, h * 0.15, w * 0.45), M.handlebarMat);
  handlebars.position.set(l * 0.42, h * 0.38, 0);
  group.add(handlebars);

  const headlight = new THREE.Mesh(new THREE.SphereGeometry(w * 0.08, 8, 8), M.headlightMat);
  headlight.position.set(l * 0.48, h * 0.25, 0);
  group.add(headlight);

  const taillight = new THREE.Mesh(new THREE.BoxGeometry(l * 0.02, h * 0.06, w * 0.15), M.taillightMat);
  taillight.position.set(-l * 0.48, h * 0.2, 0);
  group.add(taillight);

  const fork = new THREE.Mesh(new THREE.CylinderGeometry(w * 0.015, w * 0.015, h * 0.3, 6), M.handlebarMat);
  fork.position.set(l * 0.42, h * 0.12, 0);
  group.add(fork);

  const swingarm = new THREE.Mesh(new THREE.BoxGeometry(l * 0.2, h * 0.02, w * 0.02), M.handlebarMat);
  swingarm.position.set(-l * 0.2, h * 0.1, 0);
  group.add(swingarm);

  const wheelRadius = h * 0.16;
  const wheelThickness = w * 0.12;
  addWheel(group, l * 0.4, 0, wheelRadius, wheelThickness, M.wheelMat, M.rimMat);
  addWheel(group, -l * 0.35, 0, wheelRadius, wheelThickness, M.wheelMat, M.rimMat);

  return group;
}

export function buildVehicleModel(vehicleType: string, dimensions: VehicleDimensions): THREE.Group {
  if (vehicleType === 'four_wheeler') {
    return buildCarModel(dimensions);
  }
  if (vehicleType === 'motorcycle') {
    return buildMotorcycleModel(dimensions);
  }
  return buildRickshawModel(dimensions);
}

export function buildDeviationOverlays(
  deviations: Deviation3D[],
  dimensions: VehicleDimensions
): THREE.Mesh[] {
  const l = dimensions.length * SCALE;
  const h = dimensions.height * SCALE;
  const w = dimensions.width * SCALE;

  return deviations.map((dev) => {
    const boxSize = new THREE.Vector3(l * 0.3, h * 0.15, w * 0.3);
    const color = new THREE.Color(dev.color);
    const mat = new THREE.MeshPhongMaterial({
      color,
      transparent: true,
      opacity: 0.35,
      emissive: color,
      emissiveIntensity: 0.15,
    });
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(boxSize.x, boxSize.y, boxSize.z), mat);

    const nx = (dev.location === 'chassis_width' || dev.parameter === 'overall_width_mm') ? 0 : 0;
    const ny = dev.location === 'underbody' ? -h * 0.3 : h * 0.35;
    const nz = dev.location === 'cargo_area' ? -l * 0.2 : 0;
    mesh.position.set(nx, ny, nz);

    mesh.userData = { parameter: dev.parameter, severity: dev.severity, delta: dev.delta_pct };
    return mesh;
  });
}

export function buildRetrofitComponents(
  components: RetrofitComponent3D[]
): THREE.Mesh[] {
  const baseScale = 1.5;

  return components.map((comp) => {
    const color = new THREE.Color(comp.color);
    const mat = new THREE.MeshPhongMaterial({
      color,
      transparent: true,
      opacity: 0.85,
      emissive: color,
      emissiveIntensity: 0.1,
    });
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(comp.size.w * baseScale, comp.size.h * baseScale, comp.size.d * baseScale),
      mat
    );

    mesh.position.set(comp.position.x, comp.position.y, comp.position.z);

    const edgeMat = new THREE.LineBasicMaterial({ color });
    const edges = new THREE.EdgesGeometry(mesh.geometry);
    const wireframe = new THREE.LineSegments(edges, edgeMat);
    mesh.add(wireframe);

    mesh.userData = {
      componentId: comp.id,
      label: comp.label,
      color: comp.color,
      isRetrofit: true,
    };
    return mesh;
  });
}
