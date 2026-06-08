"use client";

import * as THREE from "three";

const POINT_RADIUS = 0.03;
const LINE_COLOR = 0x60a5fa;

export function createPoint(position: THREE.Vector3, color: number = 0x22c55e): THREE.Mesh {
  const geometry = new THREE.SphereGeometry(POINT_RADIUS, 12, 12);
  const material = new THREE.MeshBasicMaterial({ color });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.copy(position);
  mesh.userData.isMeasurementPoint = true;
  return mesh;
}

export function createMeasurementLine(start: THREE.Vector3, end: THREE.Vector3): THREE.Line {
  const geometry = new THREE.BufferGeometry().setFromPoints([start.clone(), end.clone()]);
  const material = new THREE.LineDashedMaterial({
    color: LINE_COLOR,
    dashSize: 0.02,
    gapSize: 0.015,
    transparent: true,
    opacity: 0.85,
  });
  const line = new THREE.Line(geometry, material);
  line.computeLineDistances();
  return line;
}

export function distanceToMm(a: THREE.Vector3, b: THREE.Vector3): number {
  return Math.round(a.distanceTo(b) * 1000);
}
