"use client";

import * as THREE from "three";
import type { ThermalZone } from "@/types/assessment";

const SEVERITY_COLORS: Record<string, number> = {
  low: 0x22c55e,
  medium: 0xeab308,
  high: 0xef4444,
};

export function buildThermalZoneMesh(zone: ThermalZone): THREE.Group {
  const color = SEVERITY_COLORS[zone.severity] ?? SEVERITY_COLORS.high;

  const group = new THREE.Group();
  group.name = `thermal-${zone.id}`;

  const geometry = new THREE.SphereGeometry(zone.radius, 24, 24);
  const material = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: 0.6,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.set(zone.position.x, zone.position.y, zone.position.z);
  mesh.userData = {
    isThermalZone: true,
    label: zone.label,
    temperature: zone.temperature_c,
    severity: zone.severity,
    zoneId: zone.id,
  };
  group.add(mesh);

  const wireframe = new THREE.LineSegments(
    new THREE.EdgesGeometry(geometry),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.8 })
  );
  wireframe.position.copy(mesh.position);
  group.add(wireframe);

  return group;
}
