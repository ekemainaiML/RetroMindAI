"use client";

import * as THREE from "three";
import type { BatteryFitment } from "@/types/assessment";

const CLEAR_COLOR = 0x10b981;
const TIGHT_COLOR = 0xf97316;
const CLEAR_OPACITY = 0.35;
const TIGHT_OPACITY = 0.5;
const EDGE_COLOR = 0xffffff;
const EDGE_OPACITY = 0.6;

export function buildBatteryFitment(
  fitment: BatteryFitment
): THREE.Group {
  const group = new THREE.Group();
  group.name = "battery-fitment";

  const isTight = fitment.fitment_status === "tight";
  const color = isTight ? TIGHT_COLOR : CLEAR_COLOR;
  const opacity = isTight ? TIGHT_OPACITY : CLEAR_OPACITY;

  const geometry = new THREE.BoxGeometry(
    fitment.size.w,
    fitment.size.h,
    fitment.size.d
  );
  const material = new THREE.MeshPhysicalMaterial({
    color,
    transparent: true,
    opacity,
    roughness: 0.3,
    metalness: 0.1,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(fitment.position.x, fitment.position.y, fitment.position.z);
  mesh.userData = {
    isBatteryFitment: true,
    label: fitment.label,
    zoneId: fitment.zone_id,
    clearance: fitment.clearance,
    fitment_status: fitment.fitment_status,
  };
  group.add(mesh);

  const edges = new THREE.EdgesGeometry(geometry);
  const edgeMaterial = new THREE.LineBasicMaterial({
    color: EDGE_COLOR,
    transparent: true,
    opacity: EDGE_OPACITY,
  });
  const wireframe = new THREE.LineSegments(edges, edgeMaterial);
  wireframe.position.copy(mesh.position);
  group.add(wireframe);

  return group;
}
