import * as THREE from 'three';
import type { VehicleDimensions, Deviation3D, RetrofitComponent3D } from '@/types/assessment';

const SCALE = 1 / 1000;

export function buildRickshawModel(dimensions: VehicleDimensions): THREE.Group {
  const group = new THREE.Group();

  const l = Math.max(dimensions.length * SCALE, 0.1);
  const w = Math.max(dimensions.width * SCALE, 0.1);
  const h = Math.max(dimensions.height * SCALE, 0.1);

  const bodyMat = new THREE.MeshStandardMaterial({
    color: 0x94a3b8,
    roughness: 0.7,
    metalness: 0.1,
  });
  const accentMat = new THREE.MeshStandardMaterial({
    color: 0x64748b,
    roughness: 0.6,
    metalness: 0.2,
  });
  const wheelMat = new THREE.MeshStandardMaterial({
    color: 0x1e293b,
    roughness: 0.9,
  });
  const rimMat = new THREE.MeshStandardMaterial({
    color: 0x94a3b8,
    roughness: 0.4,
    metalness: 0.6,
  });
  const glassMat = new THREE.MeshStandardMaterial({
    color: 0x7dd3fc,
    transparent: true,
    opacity: 0.3,
    roughness: 0.1,
    metalness: 0.0,
  });
  const bedMat = new THREE.MeshStandardMaterial({
    color: 0x78716c,
    roughness: 0.8,
    metalness: 0.0,
  });

  const body = new THREE.Mesh(new THREE.BoxGeometry(l, h * 0.5, w * 0.9), bodyMat);
  body.position.set(0, h * 0.25, 0);
  body.castShadow = true;
  group.add(body);

  const cabin = new THREE.Mesh(new THREE.BoxGeometry(l * 0.35, h * 0.35, w * 0.85), accentMat);
  cabin.position.set(l * 0.2, h * 0.55, 0);
  cabin.castShadow = true;
  group.add(cabin);

  const windshield = new THREE.Mesh(new THREE.BoxGeometry(l * 0.01, h * 0.25, w * 0.7), glassMat);
  windshield.position.set(l * 0.38, h * 0.5, 0);
  group.add(windshield);

  const bed = new THREE.Mesh(new THREE.BoxGeometry(l * 0.55, h * 0.06, w * 0.85), bedMat);
  bed.position.set(-l * 0.15, h * 0.3, 0);
  bed.castShadow = true;
  group.add(bed);

  const wheelRadius = h * 0.2;
  const wheelThickness = w * 0.08;
  const frontZ = w * 0.45;
  const rearZ = w * 0.45;

  const addWheel = (x: number, z: number) => {
    const wheel = new THREE.Mesh(
      new THREE.CylinderGeometry(wheelRadius, wheelRadius, wheelThickness, 16),
      wheelMat
    );
    wheel.rotation.x = Math.PI / 2;
    wheel.position.set(x, wheelRadius, z);
    wheel.castShadow = true;
    group.add(wheel);

    const rim = new THREE.Mesh(
      new THREE.CylinderGeometry(wheelRadius * 0.4, wheelRadius * 0.4, wheelThickness * 1.02, 8),
      rimMat
    );
    rim.rotation.x = Math.PI / 2;
    rim.position.set(x, wheelRadius, z);
    group.add(rim);
  };

  addWheel(-l * 0.2, rearZ);
  addWheel(-l * 0.2, -rearZ);
  addWheel(l * 0.35, 0);

  return group;
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
