'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { buildVehicleModel, buildDeviationOverlays, buildRetrofitComponents } from '@/lib/rickshaw-model';
import { buildBatteryFitment } from '@/lib/battery-fitment';
import { buildThermalZoneMesh } from '@/lib/thermal-zones';
import { buildWiringRoute } from '@/lib/wiring-routes';
import type { DigitalTwinData, ThermalZone, WiringRoute3D } from '@/types/assessment';

export default function DigitalTwinViewerPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);

  const [twinData, setTwinData] = useState<DigitalTwinData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [bodyOpacity, setBodyOpacity] = useState(80);
  const [viewMode, setViewMode] = useState<'before' | 'after'>('after');
  const viewModeRef = useRef<'before' | 'after'>('after');
  const [showBattery, setShowBattery] = useState(false);
  const [showHeat, setShowHeat] = useState(false);
  const [showWiring, setShowWiring] = useState(false);

  const groupsRef = useRef<{
    body?: THREE.Group;
    deviations?: THREE.Group;
    components?: THREE.Group;
    battery?: THREE.Group;
    thermalZones?: { group: THREE.Group; zone: ThermalZone }[];
    wiring?: { group: THREE.Group; route: WiringRoute3D }[];
  }>({});
  const animFrameRef = useRef<number>(0);
  const clockRef = useRef<THREE.Clock>(new THREE.Clock());

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  useEffect(() => {
    if (!id) return;
    fetch(`${API_BASE}/intake/${id}/digital-twin`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setTwinData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const animate = useCallback(() => {
    const dt = clockRef.current.getDelta();
    const elapsed = clockRef.current.getElapsedTime();

    if (groupsRef.current.thermalZones) {
      for (const { group, zone } of groupsRef.current.thermalZones) {
        const pulse = 0.7 + 0.3 * Math.sin(elapsed * 2 + group.id);
        group.scale.setScalar(pulse);
        group.children.forEach((child) => {
          if (child instanceof THREE.Mesh) {
            child.material.opacity = 0.4 + 0.3 * Math.sin(elapsed * 2 + group.id);
          }
        });
      }
    }

    controlsRef.current?.update();
    if (rendererRef.current && sceneRef.current && cameraRef.current) {
      rendererRef.current.render(sceneRef.current, cameraRef.current);
    }
    animFrameRef.current = requestAnimationFrame(animate);
  }, []);

  useEffect(() => {
    if (!twinData || !containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111118);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(5, 4, 6);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 2;
    controls.maxDistance = 12;
    controls.update();
    controlsRef.current = controls;

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
    dirLight.position.set(5, 8, 6);
    dirLight.castShadow = true;
    scene.add(dirLight);
    const fillLight = new THREE.DirectionalLight(0x8888ff, 0.3);
    fillLight.position.set(-3, 1, -4);
    scene.add(fillLight);

    const body = buildVehicleModel(twinData.vehicle_type, twinData.dimensions);
    scene.add(body);
    groupsRef.current.body = body;

    const deviations = buildDeviationOverlays(twinData.deviations_3d, twinData.dimensions);
    const deviationsGroup = new THREE.Group();
    deviations.forEach((m) => deviationsGroup.add(m));
    scene.add(deviationsGroup);
    groupsRef.current.deviations = deviationsGroup;

    const components = buildRetrofitComponents(twinData.retrofit_components);
    const componentsGroup = new THREE.Group();
    components.forEach((m) => componentsGroup.add(m));
    scene.add(componentsGroup);
    groupsRef.current.components = componentsGroup;

    if (twinData.battery_fitment) {
      const bat = buildBatteryFitment(twinData.battery_fitment);
      bat.visible = false;
      scene.add(bat);
      groupsRef.current.battery = bat;
    }

    if (twinData.thermal_zones && twinData.thermal_zones.length > 0) {
      const zones: { group: THREE.Group; zone: ThermalZone }[] = [];
      for (const z of twinData.thermal_zones) {
        const g = buildThermalZoneMesh(z);
        g.visible = false;
        scene.add(g);
        zones.push({ group: g, zone: z });
      }
      groupsRef.current.thermalZones = zones;
    }

    if (twinData.wiring_routes && twinData.wiring_routes.length > 0) {
      const routes: { group: THREE.Group; route: WiringRoute3D }[] = [];
      for (const wr of twinData.wiring_routes) {
        const g = buildWiringRoute(wr);
        g.visible = false;
        scene.add(g);
        routes.push({ group: g, route: wr });
      }
      groupsRef.current.wiring = routes;
    }

    const handleResize = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener('resize', handleResize);
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentElement === container) {
        container.removeChild(renderer.domElement);
      }
      scene.clear();
    };
  }, [twinData, animate]);

  useEffect(() => {
    viewModeRef.current = viewMode;
    if (viewMode === 'before') {
      if (groupsRef.current.components) groupsRef.current.components.visible = false;
      if (groupsRef.current.deviations) groupsRef.current.deviations.visible = true;
      if (groupsRef.current.battery) groupsRef.current.battery.visible = false;
      if (groupsRef.current.thermalZones) groupsRef.current.thermalZones.forEach((z) => (z.group.visible = false));
      if (groupsRef.current.wiring) groupsRef.current.wiring.forEach((w) => (w.group.visible = false));
    } else {
      if (groupsRef.current.components) groupsRef.current.components.visible = true;
      if (groupsRef.current.deviations) groupsRef.current.deviations.visible = true;
      if (groupsRef.current.battery) groupsRef.current.battery.visible = showBattery;
      if (groupsRef.current.thermalZones) groupsRef.current.thermalZones.forEach((z) => (z.group.visible = showHeat));
      if (groupsRef.current.wiring) groupsRef.current.wiring.forEach((w) => (w.group.visible = showWiring));
    }
  }, [viewMode, showBattery, showHeat, showWiring]);

  useEffect(() => {
    if (viewModeRef.current === 'after' && groupsRef.current.battery) {
      groupsRef.current.battery.visible = showBattery;
    }
  }, [showBattery]);

  useEffect(() => {
    if (viewModeRef.current === 'after' && groupsRef.current.thermalZones) {
      groupsRef.current.thermalZones.forEach((z) => (z.group.visible = showHeat));
    }
  }, [showHeat]);

  useEffect(() => {
    if (viewModeRef.current === 'after' && groupsRef.current.wiring) {
      groupsRef.current.wiring.forEach((w) => (w.group.visible = showWiring));
    }
  }, [showWiring]);

  useEffect(() => {
    if (!groupsRef.current.body) return;
    const traverse = (obj: THREE.Object3D) => {
      if (obj instanceof THREE.Mesh) {
        obj.material.transparent = true;
        obj.material.opacity = bodyOpacity / 100;
        obj.material.depthWrite = bodyOpacity > 50;
        obj.material.needsUpdate = true;
      }
      obj.children.forEach(traverse);
    };
    groupsRef.current.body.children.forEach(traverse);
  }, [bodyOpacity]);

  const toggle = (btn: HTMLButtonElement) => {
    btn.blur();
  };

  if (loading) {
    return (
      <div className="flex h-dvh items-center justify-center bg-zinc-900">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-zinc-600 border-t-blue-400" />
          <p className="text-sm text-zinc-400">Loading 3D model…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-dvh items-center justify-center bg-zinc-900 p-6">
        <div className="text-center">
          <p className="mb-2 text-lg font-semibold text-red-400">Unable to load model</p>
          <p className="text-sm text-zinc-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-dvh w-full bg-zinc-900">
      <div ref={containerRef} className="h-full w-full" />

      {twinData && (
        <>
          <div className="absolute left-0 right-0 top-2 z-10 flex flex-wrap items-center justify-center gap-1.5 px-2">
            <button
              onClick={(e) => { toggle(e.currentTarget); setViewMode(viewMode === 'before' ? 'after' : 'before'); }}
              className="rounded-full px-3 py-1 text-xs font-medium transition-colors"
              style={{ backgroundColor: viewMode === 'before' ? '#7c3aed' : '#3f3f46', color: '#fff' }}
            >
              {viewMode === 'before' ? 'Before' : 'After'}
            </button>
            {twinData.battery_fitment && (
              <button
                onClick={(e) => { toggle(e.currentTarget); setShowBattery((v) => !v); }}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${showBattery ? 'bg-green-600 text-white' : 'bg-zinc-700 text-zinc-300'}`}
              >
                Battery
              </button>
            )}
            {twinData.thermal_zones && twinData.thermal_zones.length > 0 && (
              <button
                onClick={(e) => { toggle(e.currentTarget); setShowHeat((v) => !v); }}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${showHeat ? 'bg-red-600 text-white' : 'bg-zinc-700 text-zinc-300'}`}
              >
                Heat
              </button>
            )}
            {twinData.wiring_routes && twinData.wiring_routes.length > 0 && (
              <button
                onClick={(e) => { toggle(e.currentTarget); setShowWiring((v) => !v); }}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${showWiring ? 'bg-amber-600 text-white' : 'bg-zinc-700 text-zinc-300'}`}
              >
                Wiring
              </button>
            )}
          </div>

          <div className="absolute bottom-4 left-0 right-0 z-10 flex items-center justify-center gap-3 px-4">
            <span className="text-[10px] font-medium text-zinc-400">Body</span>
            <input
              type="range"
              min={10}
              max={100}
              value={bodyOpacity}
              onChange={(e) => setBodyOpacity(Number(e.target.value))}
              className="w-28 accent-blue-500"
            />
            <span className="text-[10px] text-zinc-400">{bodyOpacity}%</span>
          </div>
        </>
      )}
    </div>
  );
}
