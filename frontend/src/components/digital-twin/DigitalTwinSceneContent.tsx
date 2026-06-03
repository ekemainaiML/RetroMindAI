'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import * as THREE from 'three';
import { setupScene } from '@/lib/three-setup';
import { buildRickshawModel, buildDeviationOverlays, buildRetrofitComponents } from '@/lib/rickshaw-model';
import type { DigitalTwinData } from '@/types/assessment';

interface Props {
  twinData: DigitalTwinData;
}

interface TooltipState {
  visible: boolean;
  label: string;
  x: number;
  y: number;
  color: string;
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
  const raycasterRef = useRef<THREE.Raycaster>(new THREE.Raycaster());
  const mouseRef = useRef<THREE.Vector2>(new THREE.Vector2());
  const [tooltip, setTooltip] = useState<TooltipState>({ visible: false, label: '', x: 0, y: 0, color: '' });
  const [selectedComponent, setSelectedComponent] = useState<{ label: string; color: string } | null>(null);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  }, []);

  const handleClick = useCallback(() => {
    if (!sceneRef.current || !cameraRef.current) return;
    raycasterRef.current.setFromCamera(mouseRef.current, cameraRef.current);
    const intersects = raycasterRef.current.intersectObjects(componentMeshesRef.current);
    if (intersects.length > 0) {
      const obj = intersects[0].object;
      const data = obj.userData;
      if (data.isRetrofit) {
        setSelectedComponent({ label: data.label, color: data.color });
      }
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

    const rickshaw = buildRickshawModel(twinData.dimensions);
    scene.add(rickshaw);

    const deviations = buildDeviationOverlays(twinData.deviations_3d, twinData.dimensions);
    deviations.forEach((m) => scene.add(m));
    deviationMeshesRef.current = deviations;

    const components = buildRetrofitComponents(twinData.retrofit_components);
    components.forEach((m) => scene.add(m));
    componentMeshesRef.current = components;

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
      cleanup();
    };
  }, [twinData]);

  useEffect(() => {
    if (!containerRef.current || !rendererRef.current || !cameraRef.current) return;
    const renderer = rendererRef.current;
    const camera = cameraRef.current;

    const updateTooltip = () => {
      raycasterRef.current.setFromCamera(mouseRef.current, camera);
      const intersects = raycasterRef.current.intersectObjects(componentMeshesRef.current);
      if (intersects.length > 0) {
        const obj = intersects[0].object;
        if (obj.userData.isRetrofit) {
          const rect = containerRef.current!.getBoundingClientRect();
          const point = intersects[0].point;
          const screenPoint = point.clone().project(camera);
          const x = ((screenPoint.x + 1) / 2) * rect.width;
          const y = ((-screenPoint.y + 1) / 2) * rect.height;
          setTooltip({ visible: true, label: obj.userData.label, x, y, color: obj.userData.color });
          return;
        }
      }
      setTooltip((prev) => ({ ...prev, visible: false }));
    };

    const interval = setInterval(updateTooltip, 100);
    return () => clearInterval(interval);
  }, []);

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
          <p className="mt-1 text-[10px] text-zinc-500 dark:text-zinc-400">
            Recommended retrofit component — click a component to inspect
          </p>
        </div>
      )}
    </div>
  );
}
