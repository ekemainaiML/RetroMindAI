"use client";

import * as THREE from "three";
import type { WiringRoute3D } from "@/types/assessment";

const TUBE_RADIUS = 0.025;
const TUBE_SEGMENTS = 64;
const POINT_RADIUS = 0.04;

export function buildWiringRoute(route: WiringRoute3D): THREE.Group {
  const group = new THREE.Group();
  group.name = `wiring-${route.id}`;

  const points = route.waypoints.map(
    (wp) => new THREE.Vector3(wp.x, wp.y, wp.z)
  );

  if (points.length < 2) return group;

  const curve = new THREE.CatmullRomCurve3(points);
  const tubeGeometry = new THREE.TubeGeometry(curve, TUBE_SEGMENTS, TUBE_RADIUS, 8, false);
  const material = new THREE.MeshBasicMaterial({
    color: route.color,
    transparent: true,
    opacity: route.confidence < 0.5 ? 0.4 : 0.8,
    side: THREE.DoubleSide,
  });
  const tube = new THREE.Mesh(tubeGeometry, material);
  tube.userData = { isWiringRoute: true, label: route.label, routeId: route.id };
  group.add(tube);

  points.forEach((p, i) => {
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(POINT_RADIUS, 8, 8),
      new THREE.MeshBasicMaterial({ color: route.color })
    );
    sphere.position.copy(p);
    sphere.userData = { isWiringRoute: true, label: `${route.label} — waypoint ${i + 1}`, routeId: route.id };
    group.add(sphere);
  });

  return group;
}
