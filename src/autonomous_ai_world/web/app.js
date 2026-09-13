"use strict";

const ui = {
  canvas: document.getElementById("world-canvas"),
  connection: document.getElementById("connection"),
  director: document.getElementById("director"),
  worldTime: document.getElementById("world-time"),
  weather: document.getElementById("weather"),
  tick: document.getElementById("tick"),
  characters: document.getElementById("characters"),
  population: document.getElementById("population"),
  events: document.getElementById("events"),
  adventurePanel: document.getElementById("adventure-panel"),
  adventureTitle: document.getElementById("adventure-title"),
  adventurePremise: document.getElementById("adventure-premise"),
  adventurePhases: document.getElementById("adventure-phases"),
  adventureStakes: document.getElementById("adventure-stakes"),
  pause: document.getElementById("pause"),
  speed: document.getElementById("speed"),
  voices: document.getElementById("voices"),
  volume: document.getElementById("volume"),
  labels: document.getElementById("location-labels"),
  speech: document.getElementById("speech-layer"),
  notice: document.getElementById("notice"),
};

const LOCATION_POINTS = {
  main_tent: [0, 0, 0], center_stage: [0, 0, -13], bedroom_hall: [-19, 0, 8],
  dining_hall: [19, 0, 8], backstage: [0, 0, 16], adventure_portal: [20, 0, -13],
};
const CHARACTER_COLORS = {
  pomni: "#ef3e4d", ragatha: "#496fc7", jax: "#8e58bd",
  gangle: "#e53c46", kinger: "#f3ebd4", zooble: "#69c59f",
};
const PHASES = ["hook", "investigation", "discovery", "escalation", "resolution"];
const VOICE_PROFILES = {
  pomni: { pitch: 1.35, rate: 1.08, hints: ["zira", "samantha", "female"] },
  ragatha: { pitch: 1.12, rate: .94, hints: ["aria", "jenny", "female"] },
  jax: { pitch: .78, rate: 1.12, hints: ["guy", "david", "male"] },
  gangle: { pitch: 1.45, rate: .88, hints: ["zira", "female"] },
  kinger: { pitch: .68, rate: .82, hints: ["mark", "george", "male"] },
  zooble: { pitch: .96, rate: 1.03, hints: ["aria", "samantha"] },
  caine: { pitch: 1.25, rate: 1.16, hints: ["david", "guy", "male"] },
};
const NAV_ROUTES = {
  "main_tent>center_stage": [[0,0,-4],[0,0,-8]],
  "main_tent>bedroom_hall": [[-6,0,2],[-12,0,5]],
  "main_tent>dining_hall": [[6,0,2],[12,0,5]],
  "main_tent>backstage": [[-3,0,6],[-2,0,11]],
  "center_stage>backstage": [[-5,0,-8],[-6,0,5],[-3,0,11]],
  "main_tent>adventure_portal": [[7,0,-4],[13,0,-8],[17,0,-11]],
  "center_stage>adventure_portal": [[7,0,-13],[14,0,-13]],
  "backstage>adventure_portal": [[8,0,10],[14,0,1],[18,0,-8]],
  "bedroom_hall>adventure_portal": [[-11,0,4],[-3,0,-2],[8,0,-7],[17,0,-11]],
  "dining_hall>adventure_portal": [[18,0,3],[19,0,-6]],
};
const worldView = { engine: null, scene: null, camera: null, sun: null, state: null, socket: null,
  locations: new Map(), characters: new Map(), objects: new Map(), paths: new Set(), reconnects: 0,
  rain: null, locationIndex: 0, sessionId: null, lastMessageId: 0, lastSeenAt: 0 };
const voiceState = {
  supported: "speechSynthesis" in window && "SpeechSynthesisUtterance" in window,
  enabled: localStorage.getItem("circus-voices") !== "off",
  volume: Number(localStorage.getItem("circus-volume") ?? .8),
  voices: [],
};

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function material(name, color, roughness = 1) {
  const mat = new BABYLON.PBRMaterial(name, worldView.scene);
  mat.albedoColor = BABYLON.Color3.FromHexString(color);
  mat.roughness = roughness;
  mat.metallic = 0;
  return mat;
}

function pointFor(id) {
  if (LOCATION_POINTS[id]) return BABYLON.Vector3.FromArray(LOCATION_POINTS[id]);
  const angle = worldView.locationIndex++ * 1.9;
  return new BABYLON.Vector3(Math.cos(angle) * 23, 0, Math.sin(angle) * 23);
}

function createWorld() {
  if (!window.BABYLON) {
    showNotice("The 3D library could not load. Check your internet connection and refresh.");
    return;
  }
  worldView.engine = new BABYLON.Engine(ui.canvas, true, { preserveDrawingBuffer: true, stencil: true });
  const scene = new BABYLON.Scene(worldView.engine);
  worldView.scene = scene;
  scene.collisionsEnabled = true;
  scene.clearColor = new BABYLON.Color4(0.12, 0.055, 0.19, 1);
  scene.fogMode = BABYLON.Scene.FOGMODE_EXP2;
  scene.fogDensity = 0.005;
  scene.fogColor = new BABYLON.Color3(0.12, 0.055, 0.19);
  scene.imageProcessingConfiguration.toneMappingEnabled = true;
  scene.imageProcessingConfiguration.exposure = 1.05;
  scene.imageProcessingConfiguration.contrast = 1.12;

  const camera = new BABYLON.ArcRotateCamera("observer", -Math.PI / 2.4, 1.05, 53, BABYLON.Vector3.Zero(), scene);
  camera.attachControl(ui.canvas, true);
  camera.lowerRadiusLimit = 15;
  camera.upperRadiusLimit = 75;
  camera.lowerBetaLimit = 0.48;
  camera.upperBetaLimit = 1.42;
  camera.wheelDeltaPercentage = 0.015;
  camera.panningSensibility = 90;
  worldView.camera = camera;

  const hemi = new BABYLON.HemisphericLight("sky-light", new BABYLON.Vector3(0.2, 1, 0.1), scene);
  hemi.intensity = 1.15;
  hemi.groundColor = new BABYLON.Color3(0.2, 0.08, 0.23);
  const sun = new BABYLON.DirectionalLight("sun", new BABYLON.Vector3(-0.5, -1, 0.3), scene);
  sun.position = new BABYLON.Vector3(20, 35, -20);
  sun.intensity = 1.25;
  worldView.sun = sun;

  const ground = BABYLON.MeshBuilder.CreateCylinder("circus-floor", { diameter: 72, height: .25, tessellation: 64 }, scene);
  ground.position.y = -.13;
  const floorMat = new BABYLON.PBRMaterial("checker-floor", scene);
  const floorTexture = new BABYLON.DynamicTexture("checker-pattern", { width: 1024, height: 1024 }, scene, false);
  const floorContext = floorTexture.getContext();
  const tile = 128;
  for (let row = 0; row < 8; row++) for (let col = 0; col < 8; col++) {
    floorContext.fillStyle = (row + col) % 2 ? "#d8c8a5" : "#a76a83";
    floorContext.fillRect(col * tile, row * tile, tile, tile);
  }
  floorTexture.update();
  floorMat.albedoTexture = floorTexture; floorMat.roughness = .88; floorMat.metallic = 0;
  ground.material = floorMat;
  ground.receiveShadows = true;

  const shadow = new BABYLON.ShadowGenerator(1024, sun);
  shadow.useBlurExponentialShadowMap = true;
  shadow.blurKernel = 16;
  worldView.shadow = shadow;

  createCircusInterior();
  createRain();
  scene.onBeforeRenderObservable.add(animateWorld);
  worldView.engine.runRenderLoop(() => scene.render());
  window.addEventListener("resize", () => worldView.engine.resize());
}

function beamBetween(name, from, to, diameter, mat) {
  const midpoint = BABYLON.Vector3.Center(from, to);
  const distance = BABYLON.Vector3.Distance(from, to);
  const beam = BABYLON.MeshBuilder.CreateCylinder(name, { diameter, height: distance, tessellation: 10 }, worldView.scene);
  beam.position = midpoint; beam.material = mat;
  beam.rotationQuaternion = BABYLON.Quaternion.FromUnitVectorsToRef(
    BABYLON.Axis.Y, to.subtract(from).normalize(), new BABYLON.Quaternion()
  );
  worldView.shadow.addShadowCaster(beam);
  return beam;
}

function createCircusInterior() {
  const red = material("tent-red", "#c9384a");
  const gold = material("tent-gold", "#f3c845", .62);
  const blue = material("tent-blue", "#3aaac4");
  const plum = material("tent-plum", "#552b67");
  const cream = material("tent-cream", "#f1ddaf");
  const dark = material("tent-dark", "#25152e");
  const radius = 34;

  for (let i = 0; i < 32; i++) {
    const angle = i / 32 * Math.PI * 2;
    const panel = BABYLON.MeshBuilder.CreateBox(`wall-panel-${i}`, { width: 6.9, height: 11, depth: .6 }, worldView.scene);
    panel.position = new BABYLON.Vector3(Math.cos(angle) * radius, 5.5, Math.sin(angle) * radius);
    panel.rotation.y = -angle + Math.PI / 2;
    panel.material = i % 2 ? red : cream;
    worldView.shadow.addShadowCaster(panel);
    if (i % 4 === 0) {
      const pillar = BABYLON.MeshBuilder.CreateCylinder(`gold-pillar-${i}`, { diameter: 1.05, height: 14, tessellation: 12 }, worldView.scene);
      pillar.position = new BABYLON.Vector3(Math.cos(angle) * (radius-.3), 7, Math.sin(angle) * (radius-.3));
      pillar.material = gold; worldView.shadow.addShadowCaster(pillar);
      beamBetween(`canopy-beam-${i}`, pillar.position.add(new BABYLON.Vector3(0,7,0)), new BABYLON.Vector3(0,21,0), .34, i % 8 ? red : blue);
    }
  }

  const crown = BABYLON.MeshBuilder.CreateCylinder("canopy-crown", { diameterTop: 1.2, diameterBottom: 4.5, height: 4, tessellation: 16 }, worldView.scene);
  crown.position.y = 21; crown.material = gold;
  const centerPole = BABYLON.MeshBuilder.CreateCylinder("center-pole", { diameter: .7, height: 20, tessellation: 16 }, worldView.scene);
  centerPole.position.y = 10; centerPole.material = gold;

  [-13, 0, 13].forEach((x, i) => {
    const ring = BABYLON.MeshBuilder.CreateTorus(`show-ring-${i}`, { diameter: 9.5, thickness: .34, tessellation: 48 }, worldView.scene);
    ring.position = new BABYLON.Vector3(x, .18, 0); ring.material = i === 1 ? gold : blue;
    const inner = BABYLON.MeshBuilder.CreateCylinder(`ring-carpet-${i}`, { diameter: 8.8, height: .14, tessellation: 48 }, worldView.scene);
    inner.position = new BABYLON.Vector3(x,.07,0); inner.material = i === 1 ? red : plum;
  });

  [[-20,-9,.35],[20,-9,-.35],[-20,17,2.8],[20,17,-2.8]].forEach(([x,z,rotation], group) => {
    for (let tier = 0; tier < 4; tier++) {
      const bench = BABYLON.MeshBuilder.CreateBox(`bleacher-${group}-${tier}`, { width: 9, height: .8 + tier*.55, depth: 1.4 }, worldView.scene);
      bench.position = new BABYLON.Vector3(x, (.8+tier*.55)/2, z+tier*1.3); bench.rotation.y = rotation;
      bench.material = tier % 2 ? red : blue;
    }
  });

  for (let i = 0; i < 28; i++) {
    const angle = i / 28 * Math.PI * 2;
    const bulb = BABYLON.MeshBuilder.CreateSphere(`marquee-bulb-${i}`, { diameter: .48, segments: 8 }, worldView.scene);
    bulb.position = new BABYLON.Vector3(Math.cos(angle)*25, 8 + Math.sin(i*.8)*1.3, Math.sin(angle)*25);
    bulb.material = i % 3 === 0 ? gold : i % 3 === 1 ? red : blue;
  }

  const trapezeBar = beamBetween("trapeze-bar", new BABYLON.Vector3(-5,12,1), new BABYLON.Vector3(5,12,1), .25, cream);
  beamBetween("trapeze-rope-left", new BABYLON.Vector3(-5,12,1), new BABYLON.Vector3(-5,19,1), .08, cream);
  beamBetween("trapeze-rope-right", new BABYLON.Vector3(5,12,1), new BABYLON.Vector3(5,19,1), .08, cream);
  trapezeBar.metadata = { animated: true };

  const curtainLeft = BABYLON.MeshBuilder.CreateBox("curtain-left", { width: 5, height: 10, depth: .65 }, worldView.scene);
  curtainLeft.position = new BABYLON.Vector3(-4.2,5,-25.5); curtainLeft.material = red;
  const curtainRight = curtainLeft.clone("curtain-right"); curtainRight.position.x = 4.2;
  const valance = BABYLON.MeshBuilder.CreateCylinder("curtain-valance", { diameter: 11, height: 1.2, tessellation: 18 }, worldView.scene);
  valance.position = new BABYLON.Vector3(0,10,-25.4); valance.rotation.z = Math.PI/2; valance.material = gold;

  createCaine(new BABYLON.Vector3(0, 10.5, -15.5), dark, cream, gold, red);
}

function createCaine(position, dark, cream, gold, red) {
  const root = new BABYLON.TransformNode("director-caine", worldView.scene); root.position = position;
  const mouth = BABYLON.MeshBuilder.CreateTorus("caine-mouth", { diameter: 4.3, thickness: .85, tessellation: 32 }, worldView.scene);
  mouth.parent = root; mouth.rotation.x = Math.PI/2; mouth.material = red;
  for (let i = 0; i < 10; i++) {
    const angle = i/10*Math.PI*2;
    const tooth = BABYLON.MeshBuilder.CreateBox(`caine-tooth-${i}`, { width: .46, height: .7, depth: .24 }, worldView.scene);
    tooth.parent = root; tooth.position = new BABYLON.Vector3(Math.cos(angle)*1.65, Math.sin(angle)*1.65, -.55); tooth.rotation.z = angle+Math.PI/2; tooth.material = cream;
  }
  [-.72,.72].forEach((x,i) => {
    const eye = BABYLON.MeshBuilder.CreateSphere(`caine-eye-${i}`, { diameter: 1.25, segments: 12 }, worldView.scene);
    eye.parent = root; eye.position = new BABYLON.Vector3(x,2.15,0); eye.material = cream;
    const pupil = BABYLON.MeshBuilder.CreateSphere(`caine-pupil-${i}`, { diameter: .38, segments: 8 }, worldView.scene);
    pupil.parent = root; pupil.position = new BABYLON.Vector3(x,2.15,-.57); pupil.material = i ? red : dark;
  });
  const hat = BABYLON.MeshBuilder.CreateCylinder("caine-hat", { diameter: 2.35, height: 2.1, tessellation: 18 }, worldView.scene);
  hat.parent = root; hat.position.y = 3.55; hat.material = dark;
  const brim = BABYLON.MeshBuilder.CreateCylinder("caine-brim", { diameter: 3.4, height: .22, tessellation: 20 }, worldView.scene);
  brim.parent = root; brim.position.y = 2.65; brim.material = dark;
  const band = BABYLON.MeshBuilder.CreateTorus("caine-band", { diameter: 2.2, thickness: .18, tessellation: 20 }, worldView.scene);
  band.parent = root; band.position.y = 3.1; band.material = gold;
  worldView.caine = root;
}

function createRain() {
  const texture = new BABYLON.DynamicTexture("rain-drop", 16, worldView.scene, false);
  const context = texture.getContext();
  context.clearRect(0, 0, 16, 16);
  context.strokeStyle = "white";
  context.lineWidth = 2;
  context.beginPath(); context.moveTo(9, 1); context.lineTo(6, 15); context.stroke();
  texture.hasAlpha = true; texture.update();
  const rain = new BABYLON.ParticleSystem("rain", 900, worldView.scene);
  rain.particleTexture = texture;
  rain.emitter = new BABYLON.Vector3(0, 24, 0);
  rain.minEmitBox = new BABYLON.Vector3(-36, 0, -30);
  rain.maxEmitBox = new BABYLON.Vector3(36, 0, 30);
  rain.color1 = new BABYLON.Color4(.65, .82, .9, .65);
  rain.color2 = new BABYLON.Color4(.7, .86, .95, .35);
  rain.minSize = .08; rain.maxSize = .16; rain.minLifeTime = .4; rain.maxLifeTime = .8;
  rain.emitRate = 0; rain.gravity = new BABYLON.Vector3(-1, -34, 0);
  rain.direction1 = new BABYLON.Vector3(-1, -1, 0);
  rain.direction2 = new BABYLON.Vector3(-1, -1, 0);
  rain.start();
  worldView.rain = rain;
}

function addPrimitive(parent, kind, name, options, position, mat) {
  const mesh = BABYLON.MeshBuilder[kind](name, options, worldView.scene);
  mesh.parent = parent; mesh.position = BABYLON.Vector3.FromArray(position); mesh.material = mat;
  worldView.shadow.addShadowCaster(mesh);
  return mesh;
}

function buildLocation(location) {
  if (worldView.locations.has(location.id)) return;
  const root = new BABYLON.TransformNode(`location-${location.id}`, worldView.scene);
  root.position = pointFor(location.id);
  const zoneMat = material(`${location.id}-ground`, location.id === "adventure_portal" ? "#5b3176" : "#e0b955");
  if (location.id === "main_tent") {
    const pedestal = addPrimitive(root, "CreateCylinder", "tent-map-pedestal", { diameter: 3.6, height: .65, tessellation: 24 }, [0,.33,0], material("pedestal", "#f2cf50"));
    const globe = addPrimitive(root, "CreateSphere", "tent-map-globe", { diameter: 1.8, segments: 16 }, [0,1.65,0], material("globe", "#62c8e5", .22));
    pedestal.metadata = { display: true }; globe.metadata = { display: true };
    for (let i=0; i<8; i++) {
      const balloon = addPrimitive(root, "CreateSphere", `balloon-${i}`, { diameter: .75, segments: 10 }, [Math.cos(i*.78)*3.5, 3.4+(i%3)*.5, Math.sin(i*.78)*3.5], material(`balloon-mat-${i}`, i%3===0 ? "#f04f58" : i%3===1 ? "#4ec2df" : "#f2d34f"));
      balloon.scaling.y = 1.25;
    }
  } else if (location.id === "center_stage") {
    addPrimitive(root, "CreateCylinder", "center-stage-platform", { diameter: 11, height: .8, tessellation: 48 }, [0,.4,0], material("stage-red", "#b42e48"));
    addPrimitive(root, "CreateTorus", "center-stage-trim", { diameter: 10.6, thickness: .35, tessellation: 48 }, [0,.86,0], material("stage-gold", "#f6cf4a", .3));
    for (let i=0; i<12; i++) {
      const angle = i/12*Math.PI*2;
      addPrimitive(root, "CreateSphere", `stage-light-${i}`, { diameter: .35, segments: 8 }, [Math.cos(angle)*5.2,1.1,Math.sin(angle)*5.2], material(`stage-light-mat-${i}`, i%2 ? "#ffec8a" : "#64d8ee", .2));
    }
    const mic = addPrimitive(root, "CreateCylinder", "stage-mic", { diameter: .18, height: 3.2, tessellation: 10 }, [0,2.3,0], material("mic-stand", "#34273e", .25));
    mic.rotation.z = -.12;
  } else if (location.id === "bedroom_hall") {
    const wall = material("hall-wall", "#e5b1c7"); const trim = material("hall-trim", "#5cbfd8");
    addPrimitive(root, "CreateBox", "hall-back", { width: 12, height: 6.5, depth: .7 }, [0,3.25,2.6], wall);
    const names = ["P", "R", "J", "G", "K", "Z"];
    names.forEach((letter,i) => {
      const x = -5 + i*2;
      addPrimitive(root, "CreateBox", `room-door-${letter}`, { width: 1.55, height: 3.5, depth: .35 }, [x,1.75,2.15], material(`door-${letter}`, i%2 ? "#8a59b0" : "#d64b58"));
      addPrimitive(root, "CreateSphere", `door-knob-${letter}`, { diameter: .18, segments: 8 }, [x+.5,1.7,1.94], trim);
    });
    const exitSign = addPrimitive(root, "CreateBox", "false-exit-sign", { width: 3.1, height: .8, depth: .25 }, [0,5.7,2.12], material("exit-sign", "#6ee88f", .25));
    exitSign.metadata = { liar: true };
  } else if (location.id === "dining_hall") {
    const tableMat = material("banquet-table", "#8c4d38");
    addPrimitive(root, "CreateBox", "long-table", { width: 11, height: .55, depth: 3.2 }, [0,2,0], tableMat);
    for (let i=-4; i<=4; i+=2) for (const side of [-1,1]) {
      addPrimitive(root, "CreateBox", `chair-${i}-${side}`, { width: 1, height: 1.7, depth: 1 }, [i,.85,side*2.5], material(`chair-mat-${i}-${side}`, "#4f78b7"));
    }
    const cake = addPrimitive(root, "CreateCylinder", "banquet-cake", { diameter: 2.2, height: 1.5, tessellation: 24 }, [0,3,0], material("cake", "#ef8fb1"));
    addPrimitive(root, "CreateCylinder", "cake-frosting", { diameter: 2.35, height: .25, tessellation: 24 }, [0,3.78,0], material("frosting", "#fff0cb"));
    cake.metadata = { regenerates: true };
  } else if (location.id === "backstage") {
    const crateMat = material("prop-crates", "#ad7049");
    [[-4,0,0],[3,0,1],[-2,0,3],[4,0,-3]].forEach(([x,,z],i) => {
      const crate = addPrimitive(root, "CreateBox", `prop-crate-${i}`, { size: 2.2 }, [x,1.1,z], crateMat); crate.rotation.y = i*.38;
    });
    const cannon = addPrimitive(root, "CreateCylinder", "toy-cannon", { diameter: 1.7, height: 4.4, tessellation: 16 }, [0,2,-2], material("cannon", "#6150a0", .32));
    cannon.rotation.z = Math.PI/2; cannon.rotation.x = .35;
    for (let i=0;i<4;i++) {
      const hoop = addPrimitive(root, "CreateTorus", `prop-hoop-${i}`, { diameter: 2.4+i*.25, thickness: .14, tessellation: 24 }, [-5+i*1.2,2.2+i*.3,-2], material(`hoop-mat-${i}`, i%2 ? "#f2ce44" : "#e64856"));
      hoop.rotation.x = Math.PI/2;
    }
  } else if (location.id === "adventure_portal") {
    const colors = ["#ec4451","#f1ce47","#55c7dd","#8752af"];
    colors.forEach((color,i) => {
      const portal = addPrimitive(root, "CreateTorus", `portal-ring-${i}`, { diameter: 8-i*1.2, thickness: .42, tessellation: 40 }, [0,4,0], material(`portal-mat-${i}`, color, .18));
      portal.rotation.x = Math.PI/2;
    });
    const door = addPrimitive(root, "CreateBox", "portal-void", { width: 5.2, height: 6.8, depth: .35 }, [0,3.4,.15], material("portal-void-mat", "#1e102c", .1));
    door.metadata = { portal: true };
  } else {
    addPrimitive(root, "CreateCylinder", `${location.id}-marker`, { diameter: 6, height: .3, tessellation: 12 }, [0,.15,0], zoneMat);
  }
  const marker = BABYLON.MeshBuilder.CreateDisc(`marker-${location.id}`, { radius: 5, tessellation: 48 }, worldView.scene);
  marker.parent = root; marker.position.y = .035; marker.rotation.x = Math.PI / 2; marker.material = zoneMat;
  const label = node("div", "location-label", location.name);
  ui.labels.appendChild(label);
  worldView.locations.set(location.id, { root, label, location, anchor: new BABYLON.Vector3(0, 7.5, 0) });
}

function syncPaths(locations) {
  const byId = new Map(locations.map(item => [item.id, item]));
  for (const location of locations) for (const targetId of location.exits) {
    if (!byId.has(targetId)) continue;
    const key = [location.id, targetId].sort().join("|");
    if (worldView.paths.has(key)) continue;
    const from = worldView.locations.get(location.id).root.position;
    const to = worldView.locations.get(targetId).root.position;
    const midpoint = BABYLON.Vector3.Center(from, to); midpoint.y = .025;
    const distance = BABYLON.Vector3.Distance(from, to);
    const path = BABYLON.MeshBuilder.CreateBox(`path-${key}`, { width: 1.05, height: .035, depth: distance }, worldView.scene);
    path.position = midpoint; path.rotation.y = Math.atan2(to.x-from.x, to.z-from.z);
    path.material = material(`path-mat-${key}`, "#a4916e");
    worldView.paths.add(key);
  }
}

function createCharacter(character, index) {
  const root = new BABYLON.TransformNode(`character-${character.id}`, worldView.scene);
  const color = CHARACTER_COLORS[character.id] || ["#d77970", "#588fc3", "#73a77e", "#a480bc"][index % 4];
  const primary = material(`primary-${character.id}`, color);
  const white = material(`white-${character.id}`, "#f4ecd9");
  const dark = material(`detail-${character.id}`, "#262033");
  const red = material(`red-${character.id}`, "#e63d4d");
  const blue = material(`blue-${character.id}`, "#3476c7");
  const gold = material(`gold-${character.id}`, "#f0cf4c", .35);
  const leftArm = new BABYLON.TransformNode(`${character.id}-left-arm-joint`, worldView.scene);
  const rightArm = new BABYLON.TransformNode(`${character.id}-right-arm-joint`, worldView.scene);
  const leftLeg = new BABYLON.TransformNode(`${character.id}-left-leg-joint`, worldView.scene);
  const rightLeg = new BABYLON.TransformNode(`${character.id}-right-leg-joint`, worldView.scene);
  [leftArm,rightArm,leftLeg,rightLeg].forEach(joint => joint.parent = root);

  if (character.id === "pomni") {
    const leftBody = addPrimitive(root, "CreateBox", "pomni-red-torso", { width: .62, height: 1.45, depth: .7 }, [-.3,2.15,0], red);
    const rightBody = addPrimitive(root, "CreateBox", "pomni-blue-torso", { width: .62, height: 1.45, depth: .7 }, [.3,2.15,0], blue);
    leftBody.rotation.z = -.04; rightBody.rotation.z = .04;
    addPrimitive(root, "CreateSphere", "pomni-head", { diameter: 1.12, segments: 14 }, [0,3.4,0], white);
    [-.22,.22].forEach((x,i) => addPrimitive(root, "CreateSphere", `pomni-eye-${i}`, { diameter: .18, segments: 8 }, [x,3.47,-.51], i ? blue : red));
    const hatLeft = addPrimitive(root, "CreateCylinder", "pomni-hat-red", { diameterTop: 0, diameterBottom: .72, height: 1.55, tessellation: 10 }, [-.32,4.35,0], red); hatLeft.rotation.z = -.38;
    const hatRight = addPrimitive(root, "CreateCylinder", "pomni-hat-blue", { diameterTop: 0, diameterBottom: .72, height: 1.55, tessellation: 10 }, [.32,4.35,0], blue); hatRight.rotation.z = .38;
    addPrimitive(root, "CreateSphere", "pomni-bell-red", { diameter: .28, segments: 8 }, [-.64,5,0], gold);
    addPrimitive(root, "CreateSphere", "pomni-bell-blue", { diameter: .28, segments: 8 }, [.64,5,0], gold);
    leftArm.position = new BABYLON.Vector3(-.72,2.45,0); rightArm.position = new BABYLON.Vector3(.72,2.45,0);
    addPrimitive(leftArm,"CreateCylinder","pomni-left-arm",{diameter:.25,height:1.35,tessellation:8},[0,-.5,0],red);
    addPrimitive(rightArm,"CreateCylinder","pomni-right-arm",{diameter:.25,height:1.35,tessellation:8},[0,-.5,0],blue);
    leftLeg.position = new BABYLON.Vector3(-.3,1.45,0); rightLeg.position = new BABYLON.Vector3(.3,1.45,0);
    addPrimitive(leftLeg,"CreateCylinder","pomni-left-leg",{diameter:.31,height:1.45,tessellation:8},[0,-.7,0],red);
    addPrimitive(rightLeg,"CreateCylinder","pomni-right-leg",{diameter:.31,height:1.45,tessellation:8},[0,-.7,0],blue);
  } else if (character.id === "ragatha") {
    const dress = addPrimitive(root,"CreateCylinder","ragatha-dress",{diameterTop:1.05,diameterBottom:1.8,height:2.1,tessellation:12},[0,1.7,0],blue);
    addPrimitive(root,"CreateSphere","ragatha-head",{diameter:1.15,segments:12},[0,3.25,0],white);
    for(let i=0;i<9;i++) { const hair=addPrimitive(root,"CreateCylinder",`ragatha-yarn-${i}`,{diameter:.16,height:1.35,tessellation:6},[-.48+i*.12,3.75+(i%2)*.1,.18],red); hair.rotation.z=(i-4)*.08; }
    addPrimitive(root,"CreateSphere","ragatha-button-eye",{diameter:.22,segments:8},[-.23,3.32,-.52],dark);
    addPrimitive(root,"CreateSphere","ragatha-eye",{diameter:.15,segments:8},[.23,3.32,-.54],blue);
    leftArm.position=new BABYLON.Vector3(-.75,2.35,0); rightArm.position=new BABYLON.Vector3(.75,2.35,0);
    addPrimitive(leftArm,"CreateCylinder","ragatha-left-arm",{diameter:.24,height:1.5,tessellation:7},[0,-.6,0],white);
    addPrimitive(rightArm,"CreateCylinder","ragatha-right-arm",{diameter:.24,height:1.5,tessellation:7},[0,-.6,0],white);
    leftLeg.position=new BABYLON.Vector3(-.33,.9,0); rightLeg.position=new BABYLON.Vector3(.33,.9,0);
    addPrimitive(leftLeg,"CreateCylinder","ragatha-left-leg",{diameter:.27,height:1.1,tessellation:7},[0,-.48,0],white);
    addPrimitive(rightLeg,"CreateCylinder","ragatha-right-leg",{diameter:.27,height:1.1,tessellation:7},[0,-.48,0],white);
    dress.rotation.y=.08;
  } else if (character.id === "jax") {
    addPrimitive(root,"CreateCylinder","jax-body",{diameterTop:.85,diameterBottom:1.2,height:2.15,tessellation:10},[0,2.2,0],primary);
    addPrimitive(root,"CreateSphere","jax-head",{diameter:1.3,segments:12},[0,3.75,0],primary);
    [-.33,.33].forEach((x,i)=>{ const ear=addPrimitive(root,"CreateCylinder",`jax-ear-${i}`,{diameterTop:.28,diameterBottom:.48,height:2.1,tessellation:9},[x,5.15,0],primary); ear.rotation.z=i?.12:-.12; });
    [-.25,.25].forEach((x,i)=>addPrimitive(root,"CreateSphere",`jax-eye-${i}`,{diameter:.18,segments:7},[x,3.88,-.59],gold));
    for(let i=0;i<6;i++) addPrimitive(root,"CreateBox",`jax-tooth-${i}`,{width:.18,height:.25,depth:.08},[-.45+i*.18,3.45,-.63],white);
    leftArm.position=new BABYLON.Vector3(-.73,2.7,0); rightArm.position=new BABYLON.Vector3(.73,2.7,0);
    addPrimitive(leftArm,"CreateCylinder","jax-left-arm",{diameter:.25,height:1.7,tessellation:8},[0,-.7,0],primary);
    addPrimitive(rightArm,"CreateCylinder","jax-right-arm",{diameter:.25,height:1.7,tessellation:8},[0,-.7,0],primary);
    leftLeg.position=new BABYLON.Vector3(-.3,1.25,0); rightLeg.position=new BABYLON.Vector3(.3,1.25,0);
    addPrimitive(leftLeg,"CreateCylinder","jax-left-leg",{diameter:.3,height:1.65,tessellation:8},[0,-.7,0],primary);
    addPrimitive(rightLeg,"CreateCylinder","jax-right-leg",{diameter:.3,height:1.65,tessellation:8},[0,-.7,0],primary);
  } else if (character.id === "gangle") {
    addPrimitive(root,"CreateTorus","gangle-ribbon-body",{diameter:1.4,thickness:.18,tessellation:24},[0,2,0],red);
    addPrimitive(root,"CreateSphere","gangle-mask",{diameter:1.3,segments:16},[0,3.45,0],white).scaling.z=.35;
    [-.25,.25].forEach((x,i)=>addPrimitive(root,"CreateSphere",`gangle-eye-${i}`,{diameter:.17,segments:8},[x,3.55,-.62],dark));
    const mouth=addPrimitive(root,"CreateTorus","gangle-smile",{diameter:.52,thickness:.07,tessellation:16,arc:.5},[0,3.23,-.62],dark); mouth.rotation.z=Math.PI;
    leftArm.position=new BABYLON.Vector3(-.65,2.3,0); rightArm.position=new BABYLON.Vector3(.65,2.3,0);
    addPrimitive(leftArm,"CreateCylinder","gangle-left-ribbon",{diameter:.12,height:1.6,tessellation:6},[0,-.65,0],red);
    addPrimitive(rightArm,"CreateCylinder","gangle-right-ribbon",{diameter:.12,height:1.6,tessellation:6},[0,-.65,0],red);
    leftLeg.position=new BABYLON.Vector3(-.28,1.45,0); rightLeg.position=new BABYLON.Vector3(.28,1.45,0);
    addPrimitive(leftLeg,"CreateCylinder","gangle-left-leg",{diameter:.12,height:1.5,tessellation:6},[0,-.7,0],red);
    addPrimitive(rightLeg,"CreateCylinder","gangle-right-leg",{diameter:.12,height:1.5,tessellation:6},[0,-.7,0],red);
  } else if (character.id === "kinger") {
    addPrimitive(root,"CreateCylinder","kinger-robe",{diameterTop:1.1,diameterBottom:2,height:2.7,tessellation:16},[0,1.45,0],primary);
    addPrimitive(root,"CreateSphere","kinger-head",{diameter:1.25,segments:12},[0,3.2,0],white);
    addPrimitive(root,"CreateCylinder","kinger-crown",{diameterTop:1.5,diameterBottom:1.1,height:1.15,tessellation:6},[0,4.22,0],gold);
    [-.24,.24].forEach((x,i)=>addPrimitive(root,"CreateSphere",`kinger-eye-${i}`,{diameter:.28,segments:8},[x,3.32,-.56],dark));
    leftArm.position=new BABYLON.Vector3(-.9,2.3,0); rightArm.position=new BABYLON.Vector3(.9,2.3,0);
    addPrimitive(leftArm,"CreateCylinder","kinger-left-arm",{diameter:.24,height:1.4,tessellation:7},[0,-.55,0],white);
    addPrimitive(rightArm,"CreateCylinder","kinger-right-arm",{diameter:.24,height:1.4,tessellation:7},[0,-.55,0],white);
    leftLeg.position=new BABYLON.Vector3(-.35,.45,0); rightLeg.position=new BABYLON.Vector3(.35,.45,0);
  } else {
    addPrimitive(root,"CreatePolyhedron","zooble-body",{type:2,size:1.05},[0,2.3,0],material("zooble-body","#efcf4c"));
    addPrimitive(root,"CreateSphere","zooble-head",{diameter:1.15,segments:10},[0,3.6,0],material("zooble-head","#d34c7f"));
    addPrimitive(root,"CreateCylinder","zooble-horn",{diameterTop:0,diameterBottom:.65,height:1.5,tessellation:9},[.45,4.48,0],blue).rotation.z=.38;
    [-.24,.24].forEach((x,i)=>addPrimitive(root,"CreateSphere",`zooble-eye-${i}`,{diameter:i?.16:.28,segments:8},[x,3.68,-.52],i?dark:white));
    leftArm.position=new BABYLON.Vector3(-.8,2.6,0); rightArm.position=new BABYLON.Vector3(.8,2.6,0);
    addPrimitive(leftArm,"CreateBox","zooble-left-arm",{width:.3,height:1.5,depth:.3},[0,-.6,0],material("zooble-left","#51bfa5"));
    addPrimitive(rightArm,"CreateCylinder","zooble-right-arm",{diameter:.34,height:1.5,tessellation:5},[0,-.6,0],material("zooble-right","#ef704d"));
    leftLeg.position=new BABYLON.Vector3(-.35,1.55,0); rightLeg.position=new BABYLON.Vector3(.35,1.55,0);
    addPrimitive(leftLeg,"CreateCylinder","zooble-left-leg",{diameter:.35,height:1.55,tessellation:6},[0,-.7,0],blue);
    addPrimitive(rightLeg,"CreateBox","zooble-right-leg",{width:.38,height:1.55,depth:.38},[0,-.7,0],red);
  }
  const location = worldView.locations.get(character.location_id);
  const offset = new BABYLON.Vector3(Math.cos(index*2.15)*1.65, 0, Math.sin(index*2.15)*1.65);
  root.position = (location ? location.root.position : BABYLON.Vector3.Zero()).add(offset);
  root.getChildMeshes().forEach(mesh => { mesh.checkCollisions = true; });
  worldView.characters.set(character.id, { root, leftArm, rightArm, leftLeg, rightLeg, color, locationId: character.location_id, movingUntil: 0, talkingUntil: 0, offset, movement: null });
}

function navigationRoute(fromId, toId, view) {
  const destination = worldView.locations.get(toId).root.position.add(view.offset);
  const directKey = `${fromId}>${toId}`;
  const reverseKey = `${toId}>${fromId}`;
  let points = NAV_ROUTES[directKey];
  if (!points && NAV_ROUTES[reverseKey]) points = NAV_ROUTES[reverseKey].slice().reverse();
  const lane = view.offset.scale(.28);
  const waypoints = (points || []).map(point => BABYLON.Vector3.FromArray(point).add(lane));
  return [view.root.position.clone(), ...waypoints, destination];
}

function moveCharacter(view, locationId) {
  const location = worldView.locations.get(locationId);
  if (!location) return;
  const route = navigationRoute(view.locationId, locationId, view);
  const distance = route.slice(1).reduce((total, point, index) => total + BABYLON.Vector3.Distance(route[index], point), 0);
  if (distance < .2) return;
  view.root.lookAt(route[1]);
  view.root.rotation.x = 0; view.root.rotation.z = 0;
  const frames = Math.max(30, Math.min(180, distance * 3.2));
  const ease = new BABYLON.CubicEase(); ease.setEasingMode(BABYLON.EasingFunction.EASINGMODE_EASEINOUT);
  const animation = new BABYLON.Animation("nav-route", "position", 30, BABYLON.Animation.ANIMATIONTYPE_VECTOR3, BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT);
  animation.setEasingFunction(ease);
  animation.setKeys(route.map((point, index) => ({ frame: Math.round(frames * index / (route.length - 1)), value: point })));
  if (view.movement) worldView.scene.stopAnimation(view.root);
  view.movement = worldView.scene.beginDirectAnimation(view.root, [animation], 0, frames, false, 1, () => {
    view.root.position.y = 0; view.movement = null;
  });
  view.movingUntil = performance.now() + frames / 30 * 1000;
  view.locationId = locationId;
}

function syncObjects(objects) {
  for (const item of objects) {
    if (worldView.objects.has(item.id)) continue;
    const location = item.location_id && worldView.locations.get(item.location_id);
    const holder = item.held_by && worldView.characters.get(item.held_by);
    if (!location && !holder) continue;
    const mesh = BABYLON.MeshBuilder.CreatePolyhedron(`object-${item.id}`, { type: 2, size: .55 }, worldView.scene);
    mesh.material = material(`object-mat-${item.id}`, item.tags.includes("food") ? "#8970ba" : "#e0b85e", .3);
    mesh.position = holder ? holder.root.position.add(new BABYLON.Vector3(.7,2.1,0)) : location.root.position.add(new BABYLON.Vector3(1,.7,1));
    worldView.objects.set(item.id, { mesh, item });
  }
  for (const item of objects) {
    const view = worldView.objects.get(item.id); if (!view) continue;
    if (item.held_by && worldView.characters.has(item.held_by)) {
      view.mesh.parent = worldView.characters.get(item.held_by).root;
      view.mesh.position = new BABYLON.Vector3(.72,2.1,0);
    } else if (item.location_id && worldView.locations.has(item.location_id)) {
      view.mesh.parent = null;
      view.mesh.position = worldView.locations.get(item.location_id).root.position.add(new BABYLON.Vector3(1,.7,1));
    }
  }
}

function applyState(state) {
  worldView.state = state;
  state.locations.forEach(buildLocation);
  syncPaths(state.locations);
  state.characters.forEach((character, index) => {
    if (!worldView.characters.has(character.id)) createCharacter(character, index);
    const view = worldView.characters.get(character.id);
    if (view.locationId !== character.location_id) moveCharacter(view, character.location_id);
  });
  syncObjects(state.objects || []);
  updateWeather(state.weather, state.time.is_night);
  renderDashboard(state);
}

function updateWeather(weather, isNight) {
  if (!worldView.scene) return;
  const palette = isNight ? [0.035, .07, .11] : weather === "storm" ? [.18,.24,.27] : weather === "fog" ? [.54,.6,.58] : [.56,.72,.72];
  worldView.scene.clearColor = new BABYLON.Color4(...palette, 1);
  worldView.scene.fogColor = new BABYLON.Color3(...palette);
  worldView.scene.fogDensity = weather === "fog" ? .026 : weather === "storm" ? .011 : .005;
  worldView.sun.intensity = isNight ? .25 : weather === "storm" ? .55 : 1.25;
  worldView.rain.emitRate = weather === "storm" ? 850 : weather === "rain" ? 450 : 0;
}

function animateWorld() {
  const now = performance.now();
  if (worldView.caine) {
    worldView.caine.position.y = 10.5 + Math.sin(now * .0017) * .45;
    worldView.caine.rotation.y = Math.sin(now * .0007) * .12;
  }
  for (const view of worldView.characters.values()) {
    const walking = now < view.movingUntil;
    const talking = now < view.talkingUntil;
    const swing = walking ? Math.sin(now * .012) * .55 : talking ? Math.sin(now * .018) * .28 : Math.sin(now * .002) * .04;
    view.leftArm.rotation.x = swing; view.rightArm.rotation.x = -swing;
    view.leftLeg.rotation.x = -swing; view.rightLeg.rotation.x = swing;
    if (!walking) view.root.position.y = Math.sin(now * (talking ? .007 : .0015) + view.root.uniqueId) * (talking ? .08 : .035);
  }
  for (const object of worldView.objects.values()) object.mesh.rotation.y += .008;
  positionOverlays();
}

function screenPoint(position) {
  const viewport = worldView.camera.viewport.toGlobal(worldView.engine.getRenderWidth(), worldView.engine.getRenderHeight());
  return BABYLON.Vector3.Project(position, BABYLON.Matrix.Identity(), worldView.scene.getTransformMatrix(), viewport);
}

function positionOverlays() {
  for (const location of worldView.locations.values()) {
    const point = screenPoint(location.root.position.add(location.anchor));
    location.label.style.left = `${point.x}px`; location.label.style.top = `${point.y}px`;
    location.label.style.opacity = point.z > 0 && point.z < 1 ? "1" : "0";
  }
  for (const bubble of ui.speech.children) {
    const view = worldView.characters.get(bubble.dataset.actor);
    const speaker = view?.root || (bubble.dataset.actor === "caine" ? worldView.caine : null);
    if (!speaker) continue;
    const point = screenPoint(speaker.position.add(new BABYLON.Vector3(0, view ? 4.7 : 5.8, 0)));
    bubble.style.left = `${point.x}px`; bubble.style.top = `${point.y}px`;
  }
}

function renderDashboard(state) {
  ui.worldTime.textContent = state.time.label.replace(" - ", " · ");
  ui.weather.textContent = state.weather[0].toUpperCase() + state.weather.slice(1);
  ui.tick.textContent = `Tick ${state.tick}`;
  if (state.director) {
    const suffix = state.director.last_event_day === state.time.day ? "today's adventure is live" : "preparing today's adventure";
    ui.director.textContent = `${state.director.name} · ${suffix}`;
  }
  ui.population.textContent = String(state.characters.length);
  const locationNames = new Map(state.locations.map(item => [item.id, item.name]));
  ui.characters.replaceChildren();
  state.characters.forEach(character => {
    const card = node("button", "character-card"); card.type = "button";
    card.style.setProperty("--character", CHARACTER_COLORS[character.id] || "#a480bc");
    const top = node("div", "card-top"); top.appendChild(node("i", "portrait"));
    const identity = node("div"); identity.appendChild(node("span", "character-name", character.name));
    identity.appendChild(node("span", "character-place", locationNames.get(character.location_id) || character.location_id));
    top.appendChild(identity); top.appendChild(node("span", "emotion", character.dominant_emotion)); card.appendChild(top);
    card.appendChild(node("p", "intention", character.intention ? character.intention.description : character.goal || "Observing the world"));
    const energy = node("div", "energy-row"); energy.appendChild(node("span", "", "Energy"));
    const track = node("div", "energy-track"); const fill = node("div", "energy-fill");
    fill.style.width = `${Math.max(0, Math.min(100, character.physical.energy / character.physical.max_energy * 100))}%`;
    track.appendChild(fill); energy.appendChild(track); energy.appendChild(node("span", "", `${character.physical.energy}/${character.physical.max_energy}`)); card.appendChild(energy);
    card.addEventListener("click", () => focusCharacter(character.id)); ui.characters.appendChild(card);
  });
  renderAdventure(state.adventures || []);
}

function renderAdventure(adventures) {
  const adventure = adventures.find(item => item.status === "active") || adventures[adventures.length - 1];
  if (!adventure) { ui.adventurePanel.classList.add("hidden"); return; }
  ui.adventurePanel.classList.remove("hidden"); ui.adventureTitle.textContent = adventure.title;
  ui.adventurePremise.textContent = adventure.status === "resolved" ? adventure.outcome || "The adventure is resolved." : adventure.premise;
  ui.adventureStakes.textContent = adventure.status === "resolved" ? `Resolved by ${adventure.resolved_by || "the group"}` : `At stake: ${adventure.stakes}`;
  ui.adventurePhases.replaceChildren(); const phaseIndex = PHASES.indexOf(adventure.phase);
  PHASES.forEach((phase, index) => { const segment = node("i", `phase ${index <= phaseIndex ? "done" : ""}`); segment.title = phase; ui.adventurePhases.appendChild(segment); });
}

function addEvents(events, replace = false) {
  if (replace) ui.events.replaceChildren();
  const shown = replace ? events.slice(-12).reverse() : events.slice().reverse();
  for (const event of shown) {
    const item = node("article", "event-item");
    item.style.setProperty("--event-color", event.kind.includes("adventure") ? "#edbb73" : event.kind === "action_rejected" ? "#ed8b79" : "#7cba99");
    item.appendChild(node("p", "", event.summary)); item.appendChild(node("span", "", `Tick ${event.tick} · ${event.kind.replaceAll("_", " ")}`));
    ui.events.prepend(item);
  }
  while (ui.events.children.length > 24) ui.events.lastElementChild.remove();
}

function animateEvents(events) {
  for (const event of events) {
    if ((event.kind === "spoke" || event.kind === "lied") && event.actor_id) {
      const words = event.data.message || event.summary;
      showSpeech(event.actor_id, words); speak(event.actor_id, words);
    }
    if (!event.actor_id && ["adventure_started", "situation_created", "weather_changed", "environment_changed"].includes(event.kind)) {
      showSpeech("caine", event.summary); speak("caine", event.summary);
    }
    if (event.kind.includes("adventure") && event.location_id) pulseLocation(event.location_id);
    if (event.actor_id) animateAction(event);
  }
}

function animateAction(event) {
  const view = worldView.characters.get(event.actor_id); if (!view || event.kind === "moved") return;
  if (["spoke", "lied", "helped"].includes(event.kind)) {
    const arm = event.kind === "helped" ? view.leftArm : view.rightArm;
    BABYLON.Animation.CreateAndStartAnimation("gesture", arm, "rotation.z", 30, 24, 0, event.kind === "lied" ? -1.2 : 1.1, BABYLON.Animation.ANIMATIONLOOPMODE_YOYO);
  } else if (["searched", "inspected", "explored", "object_discovered"].includes(event.kind)) {
    BABYLON.Animation.CreateAndStartAnimation("look-around", view.root, "rotation.y", 30, 36, view.root.rotation.y-.5, view.root.rotation.y+.5, BABYLON.Animation.ANIMATIONLOOPMODE_YOYO);
    pulseCharacter(event.actor_id);
  } else if (["item_picked_up", "item_dropped", "item_used"].includes(event.kind)) {
    BABYLON.Animation.CreateAndStartAnimation("reach", view.root, "scaling.y", 30, 18, 1, .72, BABYLON.Animation.ANIMATIONLOOPMODE_YOYO);
  } else if (["rested", "slept"].includes(event.kind)) {
    BABYLON.Animation.CreateAndStartAnimation("rest", view.root, "rotation.z", 30, 28, 0, event.kind === "slept" ? .7 : .25, BABYLON.Animation.ANIMATIONLOOPMODE_YOYO);
  } else {
    pulseCharacter(event.actor_id);
  }
}

function showSpeech(actorId, message) {
  const duration = Math.max(3200, Math.min(9000, message.length * 58));
  const bubble = node("div", "speech", message); bubble.dataset.actor = actorId;
  bubble.style.animationDuration = `${duration}ms`; ui.speech.appendChild(bubble);
  window.setTimeout(() => bubble.remove(), duration + 100);
}

function refreshVoices() {
  if (!voiceState.supported) return;
  voiceState.voices = window.speechSynthesis.getVoices().filter(voice => voice.lang.toLowerCase().startsWith("en"));
}

function chooseVoice(profile) {
  for (const hint of profile.hints) {
    const match = voiceState.voices.find(voice => voice.name.toLowerCase().includes(hint));
    if (match) return match;
  }
  return voiceState.voices[0] || null;
}

function speak(actorId, text) {
  if (!voiceState.supported || !voiceState.enabled || !text) return;
  const profile = VOICE_PROFILES[actorId] || { pitch: 1, rate: 1, hints: [] };
  const character = worldView.state?.characters.find(item => item.id === actorId);
  const emotion = character?.dominant_emotion;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.pitch = Math.max(.35, Math.min(1.8, profile.pitch + (emotion === "fear" ? .12 : emotion === "anger" ? -.1 : emotion === "excitement" ? .08 : 0)));
  utterance.rate = Math.max(.55, Math.min(1.6, profile.rate + (emotion === "anxiety" ? .12 : emotion === "happiness" ? .06 : emotion === "fear" ? -.08 : 0)));
  utterance.volume = voiceState.volume;
  const selected = chooseVoice(profile); if (selected) utterance.voice = selected;
  utterance.onstart = () => {
    const view = worldView.characters.get(actorId);
    if (view) view.talkingUntil = performance.now() + Math.max(1200, text.length * 55 / utterance.rate);
  };
  utterance.onend = utterance.onerror = () => {
    const view = worldView.characters.get(actorId); if (view) view.talkingUntil = 0;
  };
  window.speechSynthesis.speak(utterance);
}

function renderVoiceControls() {
  ui.voices.textContent = voiceState.supported ? (voiceState.enabled ? "Voices on" : "Voices off") : "Voices unavailable";
  ui.voices.disabled = !voiceState.supported;
  ui.volume.value = String(voiceState.volume);
}

function pulseLocation(locationId) {
  const location = worldView.locations.get(locationId); if (!location) return;
  const ring = BABYLON.MeshBuilder.CreateTorus("event-ring", { diameter: 8, thickness: .11, tessellation: 32 }, worldView.scene);
  ring.position = location.root.position.add(new BABYLON.Vector3(0,.2,0)); ring.material = material("event-ring-mat", "#edbb73", .2);
  BABYLON.Animation.CreateAndStartAnimation("ring-pulse", ring, "scaling", 30, 50, new BABYLON.Vector3(.2,.2,.2), new BABYLON.Vector3(1.5,1.5,1.5), BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT, null, () => ring.dispose());
}

function pulseCharacter(actorId) {
  const view = worldView.characters.get(actorId); if (!view) return;
  BABYLON.Animation.CreateAndStartAnimation("character-pulse", view.root, "scaling", 30, 22, BABYLON.Vector3.One(), new BABYLON.Vector3(1.14,1.14,1.14), BABYLON.Animation.ANIMATIONLOOPMODE_YOYO);
}

function focusCharacter(characterId) {
  const view = worldView.characters.get(characterId); if (!view) return;
  const ease = new BABYLON.CubicEase(); ease.setEasingMode(BABYLON.EasingFunction.EASINGMODE_EASEINOUT);
  BABYLON.Animation.CreateAndStartAnimation("camera-focus", worldView.camera, "target", 30, 35, worldView.camera.target.clone(), view.root.position.clone(), BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT, ease);
}

function showNotice(message) {
  ui.notice.textContent = message; ui.notice.classList.remove("hidden");
  window.setTimeout(() => ui.notice.classList.add("hidden"), 5500);
}

function setConnection(status, label) {
  ui.connection.className = `status ${status}`; ui.connection.lastChild.textContent = ` ${label}`;
}

function sendControl(control, value) {
  if (worldView.socket && worldView.socket.readyState === WebSocket.OPEN) {
    worldView.socket.send(JSON.stringify({ type: "observer_control", control, value }));
  }
}

function connect() {
  setConnection("connecting", "Connecting");
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const resume = worldView.state && worldView.sessionId
    ? `?session_id=${encodeURIComponent(worldView.sessionId)}&since=${worldView.lastMessageId}` : "";
  const socket = new WebSocket(`${protocol}://${location.host}/ws${resume}`); worldView.socket = socket;
  socket.addEventListener("open", () => { worldView.reconnects = 0; worldView.lastSeenAt = Date.now(); setConnection("live", "Live · synced"); });
  socket.addEventListener("message", event => {
    const message = JSON.parse(event.data);
    worldView.lastSeenAt = Date.now();
    if (message.protocol_version !== 1) { showNotice("The server uses an unsupported sync protocol."); socket.close(); return; }
    if (worldView.sessionId && message.session_id !== worldView.sessionId) {
      worldView.lastMessageId = 0;
      worldView.state = null;
    }
    worldView.sessionId = message.session_id;
    if (message.message_id <= worldView.lastMessageId) return;
    worldView.lastMessageId = message.message_id;
    socket.send(JSON.stringify({ type: "protocol_ack", message_id: message.message_id }));
    if (message.type === "snapshot") { applyState(message.state); addEvents(message.state.events || [], true); }
    else if (message.type === "tick") { applyState(message.state); addEvents(message.events || []); animateEvents(message.events || []); }
    else if (message.type === "control_state") { ui.pause.textContent = message.paused ? "Resume" : "Pause"; ui.speed.value = String(message.speed); }
    else if (message.type === "resumed") setConnection("live", message.replayed ? `Live · replayed ${message.replayed}` : "Live · synced");
    else if (message.type === "heartbeat") setConnection("live", "Live · synced");
    else if (message.type === "error") showNotice(message.message);
  });
  socket.addEventListener("close", () => {
    setConnection("offline", "Reconnecting");
    const delay = Math.min(10000, 700 * 2 ** worldView.reconnects++); window.setTimeout(connect, delay);
  });
  socket.addEventListener("error", () => socket.close());
}

ui.pause.addEventListener("click", () => sendControl("paused", ui.pause.textContent === "Pause"));
ui.speed.addEventListener("change", () => sendControl("speed", Number(ui.speed.value)));
ui.voices.addEventListener("click", () => {
  voiceState.enabled = !voiceState.enabled;
  localStorage.setItem("circus-voices", voiceState.enabled ? "on" : "off");
  if (!voiceState.enabled && voiceState.supported) window.speechSynthesis.cancel();
  renderVoiceControls();
});
ui.volume.addEventListener("input", () => {
  voiceState.volume = Number(ui.volume.value); localStorage.setItem("circus-volume", String(voiceState.volume));
});
refreshVoices();
if (voiceState.supported) window.speechSynthesis.addEventListener("voiceschanged", refreshVoices);
window.addEventListener("pointerdown", () => {
  if (voiceState.supported && voiceState.enabled) window.speechSynthesis.resume();
}, { once: true });
renderVoiceControls();
window.setInterval(() => {
  if (worldView.socket?.readyState === WebSocket.OPEN && Date.now() - worldView.lastSeenAt > 15000) {
    worldView.socket.close();
  }
}, 5000);
createWorld();
if (worldView.scene) connect();
