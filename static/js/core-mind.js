// V.E.R.A. 3D Cosmic Particle Core
// Transformed from Particle.jpg into a volumetric moving 3D particle system
// Integrates with VERA's state ("speaking", "thinking", "idle"), settings panel,
// and mouse interactivity.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

(() => {
  const canvas = document.getElementById("core-canvas");
  const stage = document.getElementById("core-stage");
  if (!canvas || !stage || !window.WebGLRenderingContext) return;

  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");

  // Default Particle Settings (can be overridden by VERA preferences)
  const particleSettings = {
    mode: "nebula",       // 'nebula', 'galaxy', 'supernova', 'pulse', 'original'
    size: 2.2,
    speed: 1.0,
    turbulence: 1.0,
    depth: 1.0,
    glow: 1.2,
    mouseEffect: "repel", // 'repel', 'attract', 'vortex', 'none'
  };

  const TIERS = {
    cinematic: { maxCount: 75000, bloom: 1.6, dpr: 2 },
    balanced: { maxCount: 45000, bloom: 1.3, dpr: 1.5 },
    performance: { maxCount: 25000, bloom: 0.9, dpr: 1 },
  };

  let activeTier = TIERS.balanced;
  let visualState = "idle";
  let pulseEnergy = 0;
  let speechWaveFactor = 0;
  let running = true;
  let frameId = 0;

  // Scene & Rendering setup
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x071019, 0.0012);

  const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 2000);
  camera.position.set(0, 0, 180);

  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    powerPreference: "high-performance"
  });
  renderer.setClearColor(0x000000, 0);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.8;
  controls.enablePan = true;
  controls.enableZoom = true;
  controls.minDistance = 25;
  controls.maxDistance = 500;

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloomPass = new UnrealBloomPass(new THREE.Vector2(256, 256), 1.4, 0.4, 0.85);
  bloomPass.radius = 0.45;
  bloomPass.threshold = 0.1;
  composer.addPass(bloomPass);

  // Mouse Interaction Setup
  const mouse = new THREE.Vector2(-9999, -9999);
  const mouseWorld = new THREE.Vector3(-9999, -9999, 0);
  const raycaster = new THREE.Raycaster();
  const interactionPlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
  let isMouseActive = false;

  // Particle System Buffers
  let particlePoints = null;
  let particleGeometry = null;
  let particleMaterial = null;
  let positions = null;
  let colors = null;
  let originPositions = null;
  let velocities = null;
  let phases = null;
  let frequencies = null;
  let radii = null;
  let angles = null;
  let currentParticleCount = 0;

  function createParticleTexture() {
    const texCanvas = document.createElement("canvas");
    texCanvas.width = 64;
    texCanvas.height = 64;
    const ctx = texCanvas.getContext("2d");

    const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, "rgba(255, 255, 255, 1.0)");
    grad.addColorStop(0.2, "rgba(210, 245, 255, 0.85)");
    grad.addColorStop(0.5, "rgba(79, 172, 254, 0.4)");
    grad.addColorStop(0.8, "rgba(103, 216, 220, 0.12)");
    grad.addColorStop(1.0, "rgba(0, 0, 0, 0)");

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 64, 64);

    const texture = new THREE.CanvasTexture(texCanvas);
    texture.generateMipmaps = false;
    texture.minFilter = THREE.LinearFilter;
    return texture;
  }

  function initParticleSwarm() {
    if (particlePoints) {
      scene.remove(particlePoints);
      particleGeometry?.dispose();
      particleMaterial?.dispose();
    }

    const rawData = window.PARTICLE_DATA || [];
    const sourceLen = rawData.length;
    const targetCount = Math.min(activeTier.maxCount, sourceLen > 0 ? sourceLen : 40000);
    currentParticleCount = targetCount;

    positions = new Float32Array(targetCount * 3);
    colors = new Float32Array(targetCount * 3);
    originPositions = new Float32Array(targetCount * 3);
    velocities = new Float32Array(targetCount * 3);
    phases = new Float32Array(targetCount);
    frequencies = new Float32Array(targetCount);
    radii = new Float32Array(targetCount);
    angles = new Float32Array(targetCount);

    const step = sourceLen > 0 ? Math.max(1, Math.floor(sourceLen / targetCount)) : 1;

    for (let i = 0; i < targetCount; i++) {
      let x = 0, y = 0, z = 0, r = 0.2, g = 0.8, b = 0.9;
      if (sourceLen > 0) {
        const srcIdx = (i * step) % sourceLen;
        const p = rawData[srcIdx];
        x = p[0];
        y = p[1];
        z = p[2];
        r = p[3];
        g = p[4];
        b = p[5];
      } else {
        // Procedural cosmic dust fallback
        const rad = Math.cbrt(Math.random()) * 70;
        const theta = Math.random() * Math.PI * 2;
        const phi = (Math.random() - 0.5) * Math.PI;
        x = rad * Math.cos(phi) * Math.cos(theta);
        y = rad * Math.cos(phi) * Math.sin(theta);
        z = rad * Math.sin(phi) * 0.4;
      }

      const idx3 = i * 3;
      positions[idx3] = x;
      positions[idx3 + 1] = y;
      positions[idx3 + 2] = z;

      originPositions[idx3] = x;
      originPositions[idx3 + 1] = y;
      originPositions[idx3 + 2] = z;

      colors[idx3] = r;
      colors[idx3 + 1] = g;
      colors[idx3 + 2] = b;

      velocities[idx3] = 0;
      velocities[idx3 + 1] = 0;
      velocities[idx3 + 2] = 0;

      phases[i] = Math.random() * Math.PI * 2;
      frequencies[i] = 0.6 + Math.random() * 1.4;
      radii[i] = Math.sqrt(x * x + y * y);
      angles[i] = Math.atan2(y, x);
    }

    particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    particleGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    particleMaterial = new THREE.PointsMaterial({
      size: particleSettings.size,
      map: createParticleTexture(),
      vertexColors: true,
      transparent: true,
      opacity: Math.min(1.0, particleSettings.glow * 0.85),
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });

    particlePoints = new THREE.Points(particleGeometry, particleMaterial);
    scene.add(particlePoints);
  }

  function resize() {
    const rect = stage.getBoundingClientRect();
    const w = Math.max(1, rect.width || window.innerWidth);
    const h = Math.max(1, rect.height || window.innerHeight);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
    composer.setSize(w, h);
    bloomPass.resolution.set(w, h);
  }

  const clock = new THREE.Clock();

  function updatePhysics(delta, time) {
    if (!particlePoints || !particleGeometry) return;

    const posAttr = particleGeometry.attributes.position;
    const posArr = posAttr.array;

    const mode = particleSettings.mode;
    const speed = particleSettings.speed;
    const turb = particleSettings.turbulence;
    const depthScale = particleSettings.depth;
    const mouseEffect = particleSettings.mouseEffect;

    // Speaking state dynamic calculation
    const isSpeaking = visualState === "speaking" && !reducedMotion.matches;
    if (isSpeaking) {
      // Harmonic voice cadence between 3.0 Hz and 6.0 Hz
      const voiceCadence = Math.sin(time * 5.2) * Math.cos(time * 2.8);
      speechWaveFactor = THREE.MathUtils.lerp(speechWaveFactor, 0.5 + 0.5 * Math.max(0, voiceCadence) + pulseEnergy * 0.5, 0.15);
    } else {
      speechWaveFactor = THREE.MathUtils.lerp(speechWaveFactor, 0, 0.08);
    }
    pulseEnergy = reducedMotion.matches ? 0 : pulseEnergy * 0.86;

    // Raycast mouse position onto interaction plane
    let hasMouseForce = false;
    let mx = 0, my = 0, mz = 0;
    if (isMouseActive && mouseEffect !== "none") {
      raycaster.setFromCamera(mouse, camera);
      const camDir = new THREE.Vector3();
      camera.getWorldDirection(camDir);
      interactionPlane.set(camDir.negate(), 0);
      const intersect = new THREE.Vector3();
      if (raycaster.ray.intersectPlane(interactionPlane, intersect)) {
        mouseWorld.copy(intersect);
        mx = mouseWorld.x;
        my = mouseWorld.y;
        mz = mouseWorld.z;
        hasMouseForce = true;
      }
    }

    const mouseRadius = 60.0;
    const mouseRadiusSq = mouseRadius * mouseRadius;
    const t = time * speed;

    // Supernova burst phase calculation
    const supernovaPeriod = 9.0;
    const supernovaProgress = (t % supernovaPeriod) / supernovaPeriod;
    let burstScale = 1.0;
    if (mode === "supernova") {
      if (supernovaProgress < 0.2) burstScale = 1.0 - (supernovaProgress / 0.2) * 0.25;
      else if (supernovaProgress < 0.5) {
        const prog = (supernovaProgress - 0.2) / 0.3;
        burstScale = 0.75 + (1 - Math.pow(1 - prog, 3)) * 2.8;
      } else if (supernovaProgress < 0.75) {
        burstScale = 3.55 - ((supernovaProgress - 0.5) / 0.25) * 0.5;
      } else {
        const prog = (supernovaProgress - 0.75) / 0.25;
        const easeInOut = prog < 0.5 ? 2 * prog * prog : 1 - Math.pow(-2 * prog + 2, 2) / 2;
        burstScale = 3.05 - easeInOut * 2.05;
      }
    }

    for (let i = 0; i < currentParticleCount; i++) {
      const idx3 = i * 3;
      const origX = originPositions[idx3];
      const origY = originPositions[idx3 + 1];
      const origZ = originPositions[idx3 + 2];
      const phase = phases[i];
      const freq = frequencies[i];
      const r = radii[i];
      const ang = angles[i];

      let targetX = origX;
      let targetY = origY;
      let targetZ = origZ * depthScale;

      // Base Mode Target Calculation
      if (mode === "nebula") {
        const wave1 = Math.sin(t * 0.8 * freq + origY * 0.04 + phase);
        const wave2 = Math.cos(t * 0.7 * freq + origX * 0.04 + phase * 1.2);
        const waveZ = Math.sin(t * 1.1 * freq + (origX + origY) * 0.03);
        targetX = origX + wave1 * 6.5 * turb;
        targetY = origY + wave2 * 6.5 * turb;
        targetZ = (origZ + waveZ * 9.0 * turb) * depthScale;
      } else if (mode === "galaxy") {
        const orbitalSpeed = (20.0 / (r + 25.0)) * 0.45 * turb;
        const newAngle = ang + t * orbitalSpeed;
        targetX = r * Math.cos(newAngle);
        targetY = r * Math.sin(newAngle);
        const waveZ = Math.sin(r * 0.12 - t * 2.0 + phase) * 7.5 * turb;
        targetZ = (origZ + waveZ) * depthScale;
      } else if (mode === "supernova") {
        const angleShift = (burstScale - 1.0) * 0.8 * (freq - 1.0);
        targetX = origX * burstScale * Math.cos(angleShift) - origY * burstScale * Math.sin(angleShift);
        targetY = origX * burstScale * Math.sin(angleShift) + origY * burstScale * Math.cos(angleShift);
        targetZ = origZ * (1.0 + (burstScale - 1.0) * 1.5) * depthScale;
      } else if (mode === "pulse") {
        const wave = Math.sin(r * 0.06 - t * 2.5);
        const scale = 1.0 + 0.3 * wave * turb;
        targetX = origX * scale;
        targetY = origY * scale;
        targetZ = origZ * scale * depthScale + Math.cos(t * 2.0 + phase) * 4.0 * turb;
      } else if (mode === "original") {
        targetX = origX + Math.sin(t + phase) * 0.6 * turb;
        targetY = origY + Math.cos(t + phase) * 0.6 * turb;
        targetZ = origZ * depthScale;
      }

      // Voice / Speech Dynamic Reaction
      if (speechWaveFactor > 0.01) {
        const speechExpansion = 1.0 + speechWaveFactor * 0.28;
        const ripple = Math.sin(r * 0.12 - time * 8.0 + phase) * (speechWaveFactor * 10.0);
        const zVibration = Math.cos(time * 6.0 + phase * 2.0) * (speechWaveFactor * 14.0);

        targetX = targetX * speechExpansion + (targetX / Math.max(1, r)) * ripple;
        targetY = targetY * speechExpansion + (targetY / Math.max(1, r)) * ripple;
        targetZ = targetZ * speechExpansion + zVibration;
      }

      let currX = posArr[idx3];
      let currY = posArr[idx3 + 1];
      let currZ = posArr[idx3 + 2];

      let vx = velocities[idx3];
      let vy = velocities[idx3 + 1];
      let vz = velocities[idx3 + 2];

      // Mouse Force Field Interaction
      if (hasMouseForce) {
        const dx = currX - mx;
        const dy = currY - my;
        const dz = currZ - mz;
        const distSq = dx * dx + dy * dy + dz * dz;

        if (distSq < mouseRadiusSq && distSq > 0.1) {
          const dist = Math.sqrt(distSq);
          const forceStrength = 1.0 - dist / mouseRadius;

          if (mouseEffect === "repel") {
            const push = forceStrength * 15.0;
            vx += (dx / dist) * push;
            vy += (dy / dist) * push;
            vz += (dz / dist) * push;
          } else if (mouseEffect === "attract") {
            const pull = forceStrength * 13.0;
            vx -= (dx / dist) * pull;
            vy -= (dy / dist) * pull;
            vz -= (dz / dist) * pull;
          } else if (mouseEffect === "vortex") {
            const spin = forceStrength * 16.0;
            vx += (-dy / dist) * spin;
            vy += (dx / dist) * spin;
            vz += Math.sin(dist) * 4.0;
          }
        }
      }

      // Spring-damper physics
      const springK = isSpeaking ? 0.085 : 0.065;
      const damping = 0.84;

      vx += (targetX - currX) * springK;
      vy += (targetY - currY) * springK;
      vz += (targetZ - currZ) * springK;

      vx *= damping;
      vy *= damping;
      vz *= damping;

      velocities[idx3] = vx;
      velocities[idx3 + 1] = vy;
      velocities[idx3 + 2] = vz;

      posArr[idx3] = currX + vx;
      posArr[idx3 + 1] = currY + vy;
      posArr[idx3 + 2] = currZ + vz;
    }

    posAttr.needsUpdate = true;

    // Dynamic bloom & particle size pulse during speech
    if (particleMaterial) {
      const activeSize = particleSettings.size * (1.0 + speechWaveFactor * 0.35);
      particleMaterial.size = activeSize;
      bloomPass.strength = activeTier.bloom * (1.0 + speechWaveFactor * 0.45);
    }
  }

  function step() {
    const delta = clock.getDelta();
    const time = clock.getElapsedTime();

    controls.autoRotate = !reducedMotion.matches;
    controls.update();

    updatePhysics(delta, time);
    composer.render();
  }

  function loop() {
    if (!running) return;
    step();
    frameId = requestAnimationFrame(loop);
  }

  function pause() {
    running = false;
    cancelAnimationFrame(frameId);
  }

  function resume() {
    if (running) return;
    running = true;
    frameId = requestAnimationFrame(loop);
  }

  // Bind Mouse Movement on Canvas
  window.addEventListener("pointermove", (e) => {
    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    isMouseActive = true;
  }, { passive: true });

  window.addEventListener("pointerleave", () => {
    isMouseActive = false;
    mouse.set(-9999, -9999);
  }, { passive: true });

  // Public Interface for VERA UI Integration
  window.veraCore = {
    setState(next) {
      visualState = next;
      if (next === "speaking") {
        pulseEnergy = Math.min(3, pulseEnergy + 1.5);
      }
    },
    pulse(amount = 1) {
      pulseEnergy = Math.min(3, pulseEnergy + amount);
    },
    updateParticleSettings(newSettings) {
      if (!newSettings) return;
      Object.assign(particleSettings, newSettings);
      if (particleMaterial) {
        if (particleSettings.size !== undefined) particleMaterial.size = particleSettings.size;
        if (particleSettings.glow !== undefined) particleMaterial.opacity = Math.min(1.0, particleSettings.glow * 0.85);
      }
    },
    getParticleSettings() {
      return { ...particleSettings };
    },
    configure(level) {
      const tier = TIERS[level] || TIERS.performance;
      activeTier = tier;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, tier.dpr));
      bloomPass.strength = tier.bloom;
      resize();
      initParticleSwarm();
      if (reducedMotion.matches) step();
    }
  };

  window.addEventListener("resize", resize, { passive: true });
  document.addEventListener("visibilitychange", () => (document.hidden ? pause() : resume()));

  // Start Core
  initParticleSwarm();
  resize();
  step();
  if (!reducedMotion.matches) frameId = requestAnimationFrame(loop);
})();
