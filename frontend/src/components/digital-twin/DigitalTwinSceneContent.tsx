'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import * as THREE from 'three';
import { setupScene } from '@/lib/three-setup';
import { buildVehicleModel, buildDeviationOverlays, buildRetrofitComponents } from '@/lib/rickshaw-model';
import { buildBatteryFitment } from '@/lib/battery-fitment';
import { createPoint, createMeasurementLine, distanceToMm } from '@/lib/measurement-tool';
import { buildThermalZoneMesh } from '@/lib/thermal-zones';
import { buildWiringRoute } from '@/lib/wiring-routes';
import type { DigitalTwinData, BatteryFitment, Measurement, ThermalZone, WiringRoute3D } from '@/types/assessment';

interface Props {
  twinData: DigitalTwinData;
}

interface TooltipState {
  visible: boolean;
  label: string;
  x: number;
  y: number;
  color: string;
  clearance?: BatteryFitment['clearance'];
}

export default function DigitalTwinSceneContent({ twinData }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<ReturnType<typeof Object> | null>(null);
  const animFrameRef = useRef<number>(0);
  const deviationMeshesRef = useRef<THREE.Mesh[]>([]);
  const componentMeshesRef = useRef<THREE.Mesh[]>([]);
  const batteryGroupRef = useRef<THREE.Group | null>(null);
  const batteryMeshesRef = useRef<THREE.Mesh[]>([]);
  const raycasterRef = useRef<THREE.Raycaster>(new THREE.Raycaster());
  const mouseRef = useRef<THREE.Vector2>(new THREE.Vector2());
  const [tooltip, setTooltip] = useState<TooltipState>({ visible: false, label: '', x: 0, y: 0, color: '' });
  const [selectedComponent, setSelectedComponent] = useState<{ label: string; color: string; clearance?: BatteryFitment['clearance'] } | null>(null);
  const [showBatteryFitment, setShowBatteryFitment] = useState(true);
  const [measurementMode, setMeasurementMode] = useState(false);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [measurementLabels, setMeasurementLabels] = useState<Array<{ id: string; midX: number; midY: number; distance: number }>>([]);
  const [showThermalZones, setShowThermalZones] = useState(true);
  const measurementGroupRef = useRef<THREE.Group | null>(null);
  const pendingPointRef = useRef<THREE.Vector3 | null>(null);
  const measurementModeRef = useRef(measurementMode);
  measurementModeRef.current = measurementMode;
  const thermalZoneGroupRef = useRef<THREE.Group | null>(null);
  const [showWiringRoutes, setShowWiringRoutes] = useState(true);
  const wiringGroupRef = useRef<THREE.Group | null>(null);
  const [bodyOpacity, setBodyOpacity] = useState(100);
  const rickshawGroupRef = useRef<THREE.Group | null>(null);
  const [viewMode, setViewMode] = useState<'before' | 'after'>('after');
  const viewModeRef = useRef(viewMode);
  viewModeRef.current = viewMode;

  const handleMouseMove = useCallback((e: MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  }, []);

  const handleClick = useCallback(() => {
    if (!sceneRef.current || !cameraRef.current) return;
    raycasterRef.current.setFromCamera(mouseRef.current, cameraRef.current);

    if (measurementModeRef.current) {
      const scene = sceneRef.current;
      const meshes: THREE.Object3D[] = [];
      scene.traverse((child) => {
        if (child instanceof THREE.Mesh && !child.userData.isMeasurementPoint) {
          meshes.push(child);
        }
      });
      const intersects = raycasterRef.current.intersectObjects(meshes, false);
      if (intersects.length === 0) return;
      const point = intersects[0].point.clone();

      if (!pendingPointRef.current) {
        pendingPointRef.current = point;
        const sphere = createPoint(point, 0x22c55e);
        sphere.userData.isTempPoint = true;
        if (measurementGroupRef.current) measurementGroupRef.current.add(sphere);
        return;
      }

      const start = pendingPointRef.current;
      pendingPointRef.current = null;

      const startSphere = createPoint(start, 0x22c55e);
      const endSphere = createPoint(point, 0xef4444);
      const line = createMeasurementLine(start, point);
      const id = `m-${Date.now()}`;
      const distance = distanceToMm(start, point);

      if (measurementGroupRef.current) {
        measurementGroupRef.current.add(startSphere);
        measurementGroupRef.current.add(endSphere);
        measurementGroupRef.current.add(line);
      }

      setMeasurements((prev) => [...prev, { id, start: { x: start.x, y: start.y, z: start.z }, end: { x: point.x, y: point.y, z: point.z }, distance }]);
      return;
    }

    const allMeshes = [...componentMeshesRef.current, ...batteryMeshesRef.current];
    if (thermalZoneGroupRef.current) {
      thermalZoneGroupRef.current.children.forEach((group) => {
        if (group instanceof THREE.Group) {
          group.children.forEach((child) => {
            if (child instanceof THREE.Mesh) allMeshes.push(child);
          });
        }
      });
    }
    const intersects = raycasterRef.current.intersectObjects(allMeshes);
    if (intersects.length > 0) {
      const obj = intersects[0].object;
      const data = obj.userData;
      if (data.isRetrofit) {
        setSelectedComponent({ label: data.label, color: data.color });
      } else if (data.isBatteryFitment) {
        setSelectedComponent({
          label: data.label,
          color: data.fitment_status === 'tight' ? '#f97316' : '#10b981',
          clearance: data.clearance,
        });
      } else if (data.isThermalZone) {
        const severity = data.severity || 'high';
        setSelectedComponent({
          label: `${data.label} (${data.temperature}°C)`,
          color: severity === 'high' ? '#ef4444' : severity === 'medium' ? '#eab308' : '#22c55e',
        });
      } else if (data.isWiringRoute) {
        setSelectedComponent({
          label: data.label,
          color: '#f59e0b',
        });
      }
    }
    if (wiringGroupRef.current) {
      wiringGroupRef.current.children.forEach((group) => {
        if (group instanceof THREE.Group) {
          group.children.forEach((child) => {
            if (child instanceof THREE.Mesh) allMeshes.push(child);
          });
        }
      });
    }
  }, []);

  useEffect(() => {
    if (!containerRef.current || !twinData) return;
    const { length, width, height } = twinData.dimensions;
    if (!length || !width || !height) return;

    const { scene, camera, renderer, controls, cleanup } = setupScene(containerRef.current);
    sceneRef.current = scene;
    cameraRef.current = camera;
    rendererRef.current = renderer;
    controlsRef.current = controls;

    const rickshaw = buildVehicleModel(twinData.vehicle_type, twinData.dimensions);
    rickshawGroupRef.current = rickshaw;
    scene.add(rickshaw);

    const deviations = buildDeviationOverlays(twinData.deviations_3d, twinData.dimensions);
    deviations.forEach((m) => scene.add(m));
    deviationMeshesRef.current = deviations;

    const components = buildRetrofitComponents(twinData.retrofit_components);
    components.forEach((m) => scene.add(m));
    componentMeshesRef.current = components;

    if (twinData.battery_fitment) {
      const batteryGroup = buildBatteryFitment(twinData.battery_fitment);
      batteryGroupRef.current = batteryGroup;
      scene.add(batteryGroup);
      const batteryMesh = batteryGroup.children.find((c) => c instanceof THREE.Mesh) as THREE.Mesh | undefined;
      batteryMeshesRef.current = batteryMesh ? [batteryMesh] : [];
    }

    const measurementGroup = new THREE.Group();
    measurementGroup.name = 'measurements';
    measurementGroupRef.current = measurementGroup;
    scene.add(measurementGroup);

    const thermalGroup = new THREE.Group();
    thermalGroup.name = 'thermal-zones';
    thermalZoneGroupRef.current = thermalGroup;
    if (twinData.thermal_zones) {
      twinData.thermal_zones.forEach((z) => {
        const sprite = buildThermalZoneMesh(z);
        thermalGroup.add(sprite);
      });
    }
    scene.add(thermalGroup);

    const wiringGroup = new THREE.Group();
    wiringGroup.name = 'wiring-routes';
    wiringGroupRef.current = wiringGroup;
    if (twinData.wiring_routes) {
      twinData.wiring_routes.forEach((r) => {
        const routeGroup = buildWiringRoute(r);
        wiringGroup.add(routeGroup);
      });
    }
    scene.add(wiringGroup);

    const gridHelper = new THREE.GridHelper(6, 12, 0x94a3b8, 0xcbd5e1);
    gridHelper.position.y = -twinData.dimensions.height * 0.001 * 0.5 - 0.1;
    scene.add(gridHelper);

    if (twinData.view_angles?.default_camera) {
      const { theta, phi, radius } = twinData.view_angles.default_camera;
      camera.position.set(
        radius * Math.sin(theta) * Math.cos(phi),
        radius * Math.sin(phi),
        radius * Math.cos(theta) * Math.cos(phi)
      );
      camera.lookAt(0, 0, 0);
      controls.update();
    }

    const timer = new THREE.Timer();

    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate);
      timer.update();
      const elapsed = timer.getElapsed();

      deviations.forEach((mesh, i) => {
        const pulse = 0.25 + 0.15 * Math.sin(elapsed * 2 + i * 1.5);
        const mat = mesh.material as THREE.MeshPhongMaterial;
        mat.opacity = pulse;
      });

      if (thermalZoneGroupRef.current) {
        thermalZoneGroupRef.current.children.forEach((child, i) => {
          if (child instanceof THREE.Group) {
            child.children.forEach((sub) => {
              if (sub instanceof THREE.Mesh) {
                const mat = sub.material as THREE.MeshBasicMaterial;
                mat.opacity = 0.35 + 0.25 * Math.sin(elapsed * 1.2 + i * 2);
              }
            });
          }
        });
      }

      raycasterRef.current.setFromCamera(mouseRef.current, camera);
      const intersects = raycasterRef.current.intersectObjects(componentMeshesRef.current);

      componentMeshesRef.current.forEach((mesh) => {
        const mat = mesh.material as THREE.MeshPhongMaterial;
        if (mat) mat.emissiveIntensity = 0.1;
      });

      if (intersects.length > 0) {
        const obj = intersects[0].object as THREE.Mesh;
        if (obj.userData.isRetrofit) {
          const mat = obj.material as THREE.MeshPhongMaterial;
          mat.emissiveIntensity = 0.5;
        }
      }

      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    containerRef.current.addEventListener('mousemove', handleMouseMove);
    containerRef.current.addEventListener('click', handleClick);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      containerRef.current?.removeEventListener('mousemove', handleMouseMove);
      containerRef.current?.removeEventListener('click', handleClick);
      scene.remove(rickshaw);
      deviations.forEach((m) => {
        scene.remove(m);
        m.geometry.dispose();
        (m.material as THREE.Material).dispose();
      });
      components.forEach((m) => {
        scene.remove(m);
        m.geometry.dispose();
        (m.material as THREE.Material).dispose();
        m.children.forEach((child) => {
          if (child instanceof THREE.LineSegments) {
            child.geometry.dispose();
            (child.material as THREE.Material).dispose();
          }
        });
      });
      if (batteryGroupRef.current) {
        scene.remove(batteryGroupRef.current);
        batteryGroupRef.current.children.forEach((child) => {
          if (child instanceof THREE.Mesh) {
            child.geometry.dispose();
            (child.material as THREE.Material).dispose();
          }
          if (child instanceof THREE.LineSegments) {
            child.geometry.dispose();
            (child.material as THREE.Material).dispose();
          }
        });
        batteryGroupRef.current = null;
        batteryMeshesRef.current = [];
      }
      if (measurementGroupRef.current) {
        scene.remove(measurementGroupRef.current);
        measurementGroupRef.current.children.forEach((child) => {
          if (child instanceof THREE.Mesh || child instanceof THREE.Line) {
            child.geometry.dispose();
            (child.material as THREE.Material).dispose();
          }
        });
        measurementGroupRef.current = null;
      }
      if (thermalZoneGroupRef.current) {
        scene.remove(thermalZoneGroupRef.current);
        thermalZoneGroupRef.current.children.forEach((child) => {
          if (child instanceof THREE.Group) {
            child.children.forEach((sub) => {
              if (sub instanceof THREE.Mesh || sub instanceof THREE.LineSegments) {
                sub.geometry.dispose();
                (sub.material as THREE.Material).dispose();
              }
            });
          }
          if (child instanceof THREE.Mesh) {
            child.geometry.dispose();
            (child.material as THREE.Material).dispose();
          }
        });
        thermalZoneGroupRef.current = null;
      }
      if (wiringGroupRef.current) {
        scene.remove(wiringGroupRef.current);
        wiringGroupRef.current.children.forEach((child) => {
          if (child instanceof THREE.Group) {
            child.children.forEach((sub) => {
              if (sub instanceof THREE.Mesh || sub instanceof THREE.LineSegments) {
                sub.geometry.dispose();
                (sub.material as THREE.Material).dispose();
              }
            });
          }
        });
        wiringGroupRef.current = null;
      }
      cleanup();
    };
  }, [twinData]);

  useEffect(() => {
    if (!containerRef.current || !rendererRef.current || !cameraRef.current) return;
    const renderer = rendererRef.current;
    const camera = cameraRef.current;

    const updateTooltip = () => {
      raycasterRef.current.setFromCamera(mouseRef.current, camera);
      const allMeshes = [...componentMeshesRef.current, ...batteryMeshesRef.current];
      if (thermalZoneGroupRef.current) {
        thermalZoneGroupRef.current.children.forEach((group) => {
          if (group instanceof THREE.Group) {
            group.children.forEach((child) => {
              if (child instanceof THREE.Mesh) allMeshes.push(child);
            });
          }
        });
      }
      if (wiringGroupRef.current) {
        wiringGroupRef.current.children.forEach((group) => {
          if (group instanceof THREE.Group) {
            group.children.forEach((child) => {
              if (child instanceof THREE.Mesh) allMeshes.push(child);
            });
          }
        });
      }
      const intersects = raycasterRef.current.intersectObjects(allMeshes);
      if (intersects.length > 0) {
        const obj = intersects[0].object;
        const data = obj.userData;
        if (data.isRetrofit) {
          const rect = containerRef.current!.getBoundingClientRect();
          const point = intersects[0].point;
          const screenPoint = point.clone().project(camera);
          const x = ((screenPoint.x + 1) / 2) * rect.width;
          const y = ((-screenPoint.y + 1) / 2) * rect.height;
          setTooltip({ visible: true, label: data.label, x, y, color: data.color });
          return;
        }
        if (data.isBatteryFitment) {
          const rect = containerRef.current!.getBoundingClientRect();
          const point = intersects[0].point;
          const screenPoint = point.clone().project(camera);
          const x = ((screenPoint.x + 1) / 2) * rect.width;
          const y = ((-screenPoint.y + 1) / 2) * rect.height;
          const color = data.fitment_status === 'tight' ? '#f97316' : '#10b981';
          setTooltip({ visible: true, label: data.label, x, y, color, clearance: data.clearance });
          return;
        }
        if (data.isThermalZone) {
          const rect = containerRef.current!.getBoundingClientRect();
          const point = intersects[0].point;
          const screenPoint = point.clone().project(camera);
          const x = ((screenPoint.x + 1) / 2) * rect.width;
          const y = ((-screenPoint.y + 1) / 2) * rect.height;
          const severity = data.severity || 'high';
          const temp = data.temperature || 0;
          setTooltip({ visible: true, label: `${data.label} (${temp}°C)`, x, y, color: severity === 'high' ? '#ef4444' : severity === 'medium' ? '#eab308' : '#22c55e' });
          return;
        }
        if (data.isWiringRoute) {
          const rect = containerRef.current!.getBoundingClientRect();
          const point = intersects[0].point;
          const screenPoint = point.clone().project(camera);
          const x = ((screenPoint.x + 1) / 2) * rect.width;
          const y = ((-screenPoint.y + 1) / 2) * rect.height;
          setTooltip({ visible: true, label: data.label, x, y, color: '#f59e0b' });
          return;
        }
      }
      setTooltip((prev) => ({ ...prev, visible: false }));

      if (measurements.length === 0) {
        setMeasurementLabels([]);
        return;
      }
      const rect = containerRef.current!.getBoundingClientRect();
      const labels = measurements.map((m) => {
        const startVec = new THREE.Vector3(m.start.x, m.start.y, m.start.z);
        const endVec = new THREE.Vector3(m.end.x, m.end.y, m.end.z);
        const mid = startVec.clone().add(endVec).multiplyScalar(0.5);
        const screenMid = mid.clone().project(camera);
        return {
          id: m.id,
          midX: ((screenMid.x + 1) / 2) * rect.width,
          midY: ((-screenMid.y + 1) / 2) * rect.height,
          distance: m.distance,
        };
      });
      setMeasurementLabels(labels);
    };

    const interval = setInterval(updateTooltip, 100);
    return () => clearInterval(interval);
  }, [measurements]);

  useEffect(() => {
    if (batteryGroupRef.current) {
      batteryGroupRef.current.visible = viewModeRef.current === 'after' && showBatteryFitment;
    }
  }, [showBatteryFitment]);

  useEffect(() => {
    if (thermalZoneGroupRef.current) {
      thermalZoneGroupRef.current.visible = viewModeRef.current === 'after' && showThermalZones;
    }
  }, [showThermalZones]);

  useEffect(() => {
    if (wiringGroupRef.current) {
      wiringGroupRef.current.visible = viewModeRef.current === 'after' && showWiringRoutes;
    }
  }, [showWiringRoutes]);

  useEffect(() => {
    if (!rickshawGroupRef.current) return;
    const opacity = bodyOpacity / 100;
    rickshawGroupRef.current.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const mat = child.material as THREE.MeshStandardMaterial;
        mat.transparent = opacity < 1;
        mat.opacity = opacity;
        mat.depthWrite = opacity >= 1;
        mat.needsUpdate = true;
      }
    });
  }, [bodyOpacity]);

  useEffect(() => {
    const isBefore = viewMode === 'before';

    deviationMeshesRef.current.forEach((mesh) => {
      mesh.visible = isBefore;
    });

    componentMeshesRef.current.forEach((mesh) => {
      mesh.visible = !isBefore;
    });

    if (isBefore) {
      if (batteryGroupRef.current) batteryGroupRef.current.visible = false;
      if (thermalZoneGroupRef.current) thermalZoneGroupRef.current.visible = false;
      if (wiringGroupRef.current) wiringGroupRef.current.visible = false;
    } else {
      if (batteryGroupRef.current) batteryGroupRef.current.visible = showBatteryFitment;
      if (thermalZoneGroupRef.current) thermalZoneGroupRef.current.visible = showThermalZones;
      if (wiringGroupRef.current) wiringGroupRef.current.visible = showWiringRoutes;
    }
  }, [viewMode, showBatteryFitment, showThermalZones, showWiringRoutes]);

  useEffect(() => {
    if (!containerRef.current) return;
    containerRef.current.style.cursor = measurementMode ? 'crosshair' : 'grab';
  }, [measurementMode]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && measurementMode) {
        setMeasurementMode(false);
        pendingPointRef.current = null;
        if (measurementGroupRef.current) {
          const toRemove: THREE.Object3D[] = [];
          measurementGroupRef.current.children.forEach((child) => {
            if (child.userData.isTempPoint) toRemove.push(child);
          });
          toRemove.forEach((child) => {
            measurementGroupRef.current!.remove(child);
            if (child instanceof THREE.Mesh) {
              child.geometry.dispose();
              (child.material as THREE.Material).dispose();
            }
          });
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [measurementMode]);

  return (
    <div className="relative w-full">
      <div
        ref={containerRef}
        className="h-[400px] w-full overflow-hidden rounded-lg"
        style={{ cursor: 'grab' }}
      />
      {tooltip.visible && (
        <div
          className="pointer-events-none absolute z-10 rounded-md px-2.5 py-1.5 text-xs font-medium text-white shadow-lg transition-opacity"
          style={{
            left: tooltip.x,
            top: tooltip.y - 36,
            backgroundColor: tooltip.color,
            opacity: tooltip.visible ? 1 : 0,
          }}
        >
          {tooltip.label}
        </div>
      )}
      {selectedComponent && (
        <div className="absolute inset-x-0 bottom-2 mx-auto w-fit rounded-lg border bg-white px-4 py-2 shadow-lg dark:border-zinc-600 dark:bg-zinc-800">
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ backgroundColor: selectedComponent.color }}
            />
            <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
              {selectedComponent.label}
            </span>
            <button
              type="button"
              onClick={() => setSelectedComponent(null)}
              className="ml-2 text-xs text-zinc-400 hover:text-zinc-600"
            >
              ✕
            </button>
          </div>
          {selectedComponent.clearance ? (
            <div className="mt-1 grid grid-cols-3 gap-x-4 gap-y-0.5 text-[10px] text-zinc-500 dark:text-zinc-400">
              <span>Front: {selectedComponent.clearance.front}mm</span>
              <span>Rear: {selectedComponent.clearance.rear}mm</span>
              <span>Left: {selectedComponent.clearance.left}mm</span>
              <span>Right: {selectedComponent.clearance.right}mm</span>
              <span>Top: {selectedComponent.clearance.top}mm</span>
              <span>Bottom: {selectedComponent.clearance.bottom}mm</span>
            </div>
          ) : (
            <p className="mt-1 text-[10px] text-zinc-500 dark:text-zinc-400">
              Recommended retrofit component — click a component to inspect
            </p>
          )}
        </div>
      )}
      {measurementLabels.map((l) => (
        <div
          key={l.id}
          className="pointer-events-none absolute z-10 rounded-md bg-blue-500 px-2 py-0.5 text-[11px] font-medium text-white shadow"
          style={{ left: l.midX, top: l.midY - 14, transform: 'translateX(-50%)' }}
        >
          {l.distance >= 1000
            ? `${(l.distance / 1000).toFixed(2)}m`
            : `${l.distance}mm`}
        </div>
      ))}
      <div className="absolute left-2 top-2 flex gap-1.5">
        <button
          type="button"
          onClick={() => setViewMode((v) => (v === 'after' ? 'before' : 'after'))}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            viewMode === 'after'
              ? 'bg-violet-500 text-white'
              : 'bg-zinc-200 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400'
          }`}
        >
          {viewMode === 'after' ? 'After' : 'Before'}
        </button>
        <button
          type="button"
          onClick={() => {
            setShowBatteryFitment((v) => !v);
          }}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            showBatteryFitment
              ? 'bg-emerald-500 text-white'
              : 'bg-zinc-200 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400'
          }`}
        >
          Battery
        </button>
        <button
          type="button"
          onClick={() => {
            setShowThermalZones((v) => !v);
          }}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            showThermalZones
              ? 'bg-red-500 text-white'
              : 'bg-zinc-200 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400'
          }`}
        >
          Heat
        </button>
        <button
          type="button"
          onClick={() => setShowWiringRoutes((v) => !v)}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            showWiringRoutes
              ? 'bg-amber-500 text-white'
              : 'bg-zinc-200 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400'
          }`}
        >
          Wiring
        </button>
        <button
          type="button"
          onClick={() => {
            const newMode = !measurementMode;
            setMeasurementMode(newMode);
            if (!newMode) {
              pendingPointRef.current = null;
              if (measurementGroupRef.current) {
                const toRemove: THREE.Object3D[] = [];
                measurementGroupRef.current.children.forEach((child) => {
                  if (child.userData.isTempPoint) toRemove.push(child);
                });
                toRemove.forEach((child) => {
                  measurementGroupRef.current!.remove(child);
                  if (child instanceof THREE.Mesh) {
                    child.geometry.dispose();
                    (child.material as THREE.Material).dispose();
                  }
                });
              }
            }
          }}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            measurementMode
              ? 'bg-blue-500 text-white'
              : 'bg-zinc-200 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400'
          }`}
        >
          {measurementMode ? 'Measuring...' : 'Measure'}
        </button>
        {measurements.length > 0 && (
          <button
            type="button"
            onClick={() => {
              setMeasurements([]);
              setMeasurementLabels([]);
              pendingPointRef.current = null;
              if (measurementGroupRef.current) {
                while (measurementGroupRef.current.children.length > 0) {
                  const child = measurementGroupRef.current.children[0];
                  measurementGroupRef.current.remove(child);
                  if (child instanceof THREE.Mesh || child instanceof THREE.Line) {
                    child.geometry.dispose();
                    (child.material as THREE.Material).dispose();
                  }
                }
              }
            }}
            className="rounded-md bg-red-500 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-red-600"
          >
            Clear All
          </button>
        )}
      </div>
      <div className="absolute bottom-2 left-2 flex items-center gap-2 rounded-md bg-white/80 px-2.5 py-1.5 shadow-sm backdrop-blur dark:bg-zinc-800/80">
        <span className="text-[10px] font-medium text-zinc-500 dark:text-zinc-400">Body</span>
        <input
          type="range"
          min="10"
          max="100"
          value={bodyOpacity}
          onChange={(e) => setBodyOpacity(Number(e.target.value))}
          className="h-1 w-20 cursor-pointer appearance-none rounded-full bg-zinc-300 accent-zinc-600 dark:bg-zinc-600 dark:accent-zinc-300"
        />
        <span className="w-8 text-right text-[10px] text-zinc-500 dark:text-zinc-400">{bodyOpacity}%</span>
      </div>
    </div>
  );
}
