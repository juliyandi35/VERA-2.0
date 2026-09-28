import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';

export class ParticlesSwarm {
    constructor(container, count = 20000) {
        this.count = count;
        this.container = container;
        this.speedMult = 1;
        
        // SETUP
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x000000, 0.01);
        this.camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
        this.camera.position.set(0, 0, 100);
        
        this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.container.appendChild(this.renderer.domElement);

        // POST PROCESSING
        this.composer = new EffectComposer(this.renderer);
        this.composer.addPass(new RenderPass(this.scene, this.camera));
        const bloomPass = new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 1.5, 0.4, 0.85);
        bloomPass.strength = 1.8; bloomPass.radius = 0.4; bloomPass.threshold = 0;
        this.composer.addPass(bloomPass);

        // OBJECTS
        this.dummy = new THREE.Object3D();
        this.color = new THREE.Color();
        this.target = new THREE.Vector3();
        this.pColor = new THREE.Color();
        
        this.geometry = new THREE.TetrahedronGeometry(0.25);
        this.material = new THREE.MeshBasicMaterial({ color: 0xffffff });
        
        this.mesh = new THREE.InstancedMesh(this.geometry, this.material, this.count);
        this.mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        this.scene.add(this.mesh);
        
        this.positions = [];
        for(let i=0; i<this.count; i++) {
            this.positions.push(new THREE.Vector3((Math.random()-0.5)*100, (Math.random()-0.5)*100, (Math.random()-0.5)*100));
            this.mesh.setColorAt(i, this.color.setHex(0x00ff88));
        }
        
        this.clock = new THREE.Clock();
        this.animate = this.animate.bind(this);
        this.animate();
    }

    animate() {
        requestAnimationFrame(this.animate);
        const time = this.clock.getElapsedTime() * this.speedMult;
        
        if(this.material.uniforms && this.material.uniforms.uTime) {
            this.material.uniforms.uTime.value = time;
        }

        // API Stubs
        const PARAMS = {"foldIntensity":0.5,"plasticity":0.37,"expansion":47,"consciousnessFlow":1.2,"chaos":0,"rotationSpeed":0.53,"fireRate":3.305,"mood":0.2};
        const addControl = (id, l, min, max, val) => {
             return PARAMS[id] !== undefined ? PARAMS[id] : val;
        };
        const setInfo = () => {};
        const annotate = () => {};
        let THREE_LIB = THREE;
        
        let THREE_LIB = THREE;
        const count = this.count; // Alias for user code
        
        for(let i=0; i<this.count; i++) {
            let target = this.target;
            let color = this.pColor;
            
            // INJECTED CODE
            const idxF = i + 0.5;
            const denom = Math.max(count, 1);
            const goldenAngle = Math.PI * (3 - Math.sqrt(5));
            const cosPhiArg = 1 - 2 * idxF / denom;
            const clampedArg = Math.min(1, Math.max(-1, cosPhiArg));
            const phi = Math.acos(clampedArg);
            const theta = goldenAngle * idxF;
            
            const dirX = Math.sin(phi) * Math.cos(theta);
            const dirY = Math.cos(phi);
            const dirZ = Math.sin(phi) * Math.sin(theta);
            
            const regionIndex = i % 8;
            const regionT = regionIndex / 8;
            
            const lobeAngle = regionT * Math.PI * 2;
            const lobeX = Math.cos(lobeAngle);
            const lobeZ = Math.sin(lobeAngle);
            const lobeY = Math.cos(regionIndex * Math.PI);
            
            const lobePull = 0.35;
            const blendX = dirX * (1 - lobePull) + lobeX * lobePull;
            const blendY = dirY * (1 - lobePull) + lobeY * lobePull * 0.6;
            const blendZ = dirZ * (1 - lobePull) + lobeZ * lobePull;
            const vecLen = Math.max(Math.sqrt(blendX * blendX + blendY * blendY + blendZ * blendZ), 0.0001);
            const normX = blendX / vecLen;
            const normY = blendY / vecLen;
            const normZ = blendZ / vecLen;
            
            const foldIntensity = addControl("foldIntensity", "Cortical Folding", 0, 1, 0.4);
            const fold = Math.sin(phi * 14 + theta * 4 + time * 0.15) * 0.5
            
            Math.sin(theta * 9 - phi * 6 + time * 0.2) * 0.3
            Math.sin(phi * 22 + theta * 17 - time * 0.1) * 0.2;
            const foldedRadius = 1 + fold * foldIntensity * 0.3;
            
            const hemiSign = Math.sign(normX + 0.0001);
            const fissureGap = 0.06;
            
            const plasticity = addControl("plasticity", "Neuroplasticity Pulse", 0, 1, 0.3);
            const breathe = 1 + Math.sin(time * 0.25 + regionT * 6.28) * 0.08 * plasticity;
            
            const expansion = addControl("expansion", "Brain Size", 20, 120, 60);
            const scaleX = 1.15;
            const scaleY = 0.95;
            const scaleZ = 1.0;
            
            const radiusVal = expansion * foldedRadius * breathe;
            const surfaceX = normX * scaleX * radiusVal + hemiSign * fissureGap * expansion;
            const surfaceY = normY * scaleY * radiusVal;
            const surfaceZ = normZ * scaleZ * radiusVal;
            
            const coreWeight = Math.exp(-Math.pow(regionIndex - 2, 2) * 1.5);
            const consciousnessFlow = addControl("consciousnessFlow", "Consciousness Flow", 0, 4, 1.2);
            const spiralAngle = i * 0.15 + time * consciousnessFlow;
            const spiralRadius = (i % 400) * 0.05 + 2;
            const spiralX = Math.cos(spiralAngle) * spiralRadius;
            const spiralZ = Math.sin(spiralAngle) * spiralRadius;
            const spiralY = Math.sin(time * 0.5 + i * 0.01) * expansion * 0.15;
            
            let posX = surfaceX * (1 - coreWeight) + spiralX * coreWeight;
            let posY = surfaceY * (1 - coreWeight) + spiralY * coreWeight;
            let posZ = surfaceZ * (1 - coreWeight) + spiralZ * coreWeight;
            
            const chaos = addControl("chaos", "Subconscious Chaos", 0, 3, 0.8);
            const chaosWeight = Math.exp(-Math.pow(regionIndex - 7, 2) * 1.5);
            const hashA = Math.sin(i * 12.9898 + time * 1.3) * 43758.5453;
            const jitterA = hashA - Math.floor(hashA);
            const hashB = Math.sin(i * 78.233 + time * 0.7) * 24634.6345;
            const jitterB = hashB - Math.floor(hashB);
            const hashC = Math.sin(i * 45.164 + time * 1.9) * 11753.314;
            const jitterC = hashC - Math.floor(hashC);
            posX += (jitterA - 0.5) * chaos * chaosWeight * expansion * 0.15;
            posY += (jitterB - 0.5) * chaos * chaosWeight * expansion * 0.15;
            posZ += (jitterC - 0.5) * chaos * chaosWeight * expansion * 0.15;
            
            const rotationSpeed = addControl("rotationSpeed", "Rotation Speed", 0, 1, 0.15);
            const rotAngle = time * rotationSpeed;
            const cosR = Math.cos(rotAngle);
            const sinR = Math.sin(rotAngle);
            const rotX = posX * cosR - posZ * sinR;
            const rotZ = posX * sinR + posZ * cosR;
            posX = rotX;
            posZ = rotZ;
            
            target.set(posX, posY, posZ);
            
            const fireRate = addControl("fireRate", "Synaptic Firing Rate", 0.5, 6, 2.2);
            const mood = addControl("mood", "Neurochemical Mood", -1, 1, 0.0);
            
            const baseHue = regionT * 0.85 + 0.05;
            const moodShift = mood * 0.12;
            const hueRaw = baseHue + moodShift + time * 0.01;
            const hue = ((hueRaw % 1) + 1) % 1;
            
            const distFromCenter = Math.sqrt(posX * posX + posY * posY + posZ * posZ);
            const firingPhase = Math.sin(distFromCenter * 0.35 - time * fireRate + regionIndex * 0.8);
            const firing = Math.pow(Math.max(0, firingPhase), 6);
            
            const saturation = 0.55 + firing * 0.35 + coreWeight * 0.1;
            const lightness = 0.35 + firing * 0.4 + coreWeight * 0.15 - chaosWeight * 0.05;
            const clampedSat = Math.min(1, Math.max(0.15, saturation));
            const clampedLight = Math.min(0.9, Math.max(0.12, lightness));
            
            color.setHSL(hue, clampedSat, clampedLight);
            
            if (i === 0) {
            setInfo("The Architecture of Mind", "86 billion neurons and trillions of synapses form 8 interwoven layers here: biology, cognition, consciousness, memory, executive control, emotion, empathy and the subconscious, all pulsing with neurochemical rhythm.");
            annotate("core", new THREE.Vector3(0, 0, 0), "Consciousness - the continuous stream of awareness");
            annotate("cortex", new THREE.Vector3(expansion * 1.1, expansion * 0.3, 0), "Cortical Folding - Cognitive Processing");
            annotate("emotion", new THREE.Vector3(-expansion * 0.7, -expansion * 0.4, expansion * 0.6), "Emotional and Social Depth");
            annotate("subconscious", new THREE.Vector3(0, -expansion * 1.1, -expansion * 0.3), "Subconscious - habits, reflexes, imagination");
            }
            
            // UPDATE
            this.positions[i].lerp(this.target, 0.1);
            this.dummy.position.copy(this.positions[i]);
            this.dummy.updateMatrix();
            this.mesh.setMatrixAt(i, this.dummy.matrix);
            this.mesh.setColorAt(i, this.pColor);
        }
        this.mesh.instanceMatrix.needsUpdate = true;
        this.mesh.instanceColor.needsUpdate = true;
        
        this.composer.render();
    }
    
    dispose() {
        this.geometry.dispose();
        this.material.dispose();
        this.scene.remove(this.mesh);
        this.renderer.dispose();
    }
}