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
  questObjectives: document.getElementById("quest-objectives"),
  adventureStakes: document.getElementById("adventure-stakes"),
  episodeNumber: document.getElementById("episode-number"),
  episodeTitle: document.getElementById("episode-title"),
  episodeOutcome: document.getElementById("episode-outcome"),
  worldSystems: document.getElementById("world-systems"),
  pause: document.getElementById("pause"),
  speed: document.getElementById("speed"),
  voices: document.getElementById("voices"),
  sound: document.getElementById("sound"),
  volume: document.getElementById("volume"),
  cinematic: document.getElementById("cinematic"),
  labels: document.getElementById("location-labels"),
  speech: document.getElementById("speech-layer"),
  notice: document.getElementById("notice"),
  vfxFlash: document.getElementById("vfx-flash"),
};

const LOCATION_POINTS = {
  main_tent: [0, 0, 0], center_stage: [0, 0, -17], bedroom_hall: [-23, 0, 7],
  dining_hall: [23, 0, 7], backstage: [0, 0, 21], circus_grounds: [0, 0, 48],
  rides_promenade: [-29, 0, 63], digital_lake: [30, 0, 64], portal_gallery: [0, 0, 80],
  grand_theater: [-36, 0, 38], void_overlook: [37, 0, 42],
  adventure_portal: [20, 0, -15], mirror_maze: [-20, 0, -15],
  moon_carnival: [-29, 0, -2], candy_kingdom: [29, 0, -2],
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
const worldView = { engine: null, scene: null, camera: null, sun: null, state: null, socket: null,
  navigation: new FreeNavigation(), paused: false, locations: new Map(), characters: new Map(), objects: new Map(), paths: new Set(), reconnects: 0,
  activitySpots: new Map(), animatedProps: [], caine: null, caineModel: null, caineSpatial: null,
  rain: null, locationIndex: 0, sessionId: null, lastMessageId: 0, lastSeenAt: 0,
  gloinks: [], showLights: [], portalRings: [], renderPaused: false };
const voiceState = {
  supported: "speechSynthesis" in window && "SpeechSynthesisUtterance" in window,
  enabled: localStorage.getItem("circus-voices") !== "off",
  volume: Number(localStorage.getItem("circus-volume") ?? .8),
  voices: [],
};
const cameraDirector = {
  enabled: localStorage.getItem("circus-cinematic") !== "off",
  manualUntil: 0, followId: null, followUntil: 0, lastShotAt: 0,
};
const soundState = {
  enabled: localStorage.getItem("circus-sound") !== "off",
  context: null, master: null, ambient: [], started: false,
};
const performanceState = { lastCheck: 0, quality: 1 };

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

function pointFor(id, location = null) {
  if (LOCATION_POINTS[id]) return BABYLON.Vector3.FromArray(LOCATION_POINTS[id]);
  if (location?.pocket_world_number) {
    const worldNumber = Number(location.pocket_world_number);
    const zoneIndex = Number(location.zone_index || 0);
    const angle = worldNumber * 2.39996;
    const ring = 112 + Math.floor((worldNumber - 1) / 6) * 62;
    const outward = new BABYLON.Vector3(Math.cos(angle), 0, Math.sin(angle));
    const tangent = new BABYLON.Vector3(-Math.sin(angle), 0, Math.cos(angle));
    return outward.scale(ring + zoneIndex * 13).add(tangent.scale((zoneIndex - 1) * 7));
  }
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

  const camera = new BABYLON.ArcRotateCamera("observer", Math.PI / 2.25, 1.2, 52, new BABYLON.Vector3(0, 4, -9), scene);
  camera.attachControl(ui.canvas, true);
  camera.lowerRadiusLimit = 7;
  camera.upperRadiusLimit = 190;
  camera.lowerBetaLimit = 0.48;
  camera.upperBetaLimit = 1.42;
  camera.wheelDeltaPercentage = 0.015;
  camera.panningSensibility = 90;
  worldView.camera = camera;

  const hemi = new BABYLON.HemisphericLight("sky-light", new BABYLON.Vector3(0.2, 1, -0.5), scene);
  hemi.intensity = .72;
  hemi.groundColor = new BABYLON.Color3(0.2, 0.08, 0.23);
  const sun = new BABYLON.DirectionalLight("sun", new BABYLON.Vector3(-0.5, -1, 0.3), scene);
  sun.position = new BABYLON.Vector3(20, 35, -20);
  sun.intensity = 1.25;
  worldView.sun = sun;
  [[-15,12,-8,"#ff4964"],[15,12,-8,"#55d9ef"],[0,16,14,"#ffe06a"]].forEach(([x,y,z,color], index) => {
    const light = new BABYLON.SpotLight(`show-light-${index}`, new BABYLON.Vector3(x,y,z), new BABYLON.Vector3(-x,-y,-z).normalize(), Math.PI/2.8, 9, scene);
    light.diffuse = BABYLON.Color3.FromHexString(color); light.intensity = .7; worldView.showLights.push(light);
  });

  const ground = BABYLON.MeshBuilder.CreateBox("circus-floor", { width: 70, depth: 68, height: .25 }, scene);
  ground.position.y = -.13;
  const floorMat = new BABYLON.PBRMaterial("checker-floor", scene);
  const floorTexture = new BABYLON.DynamicTexture("checker-pattern", { width: 1024, height: 1024 }, scene, false);
  const floorContext = floorTexture.getContext();
  const tile = 64;
  for (let row = 0; row < 16; row++) for (let col = 0; col < 16; col++) {
    floorContext.fillStyle = (row + col) % 2 ? "#e9cb83" : "#b52c44";
    floorContext.fillRect(col * tile, row * tile, tile, tile);
  }
  floorTexture.update();
  floorMat.albedoTexture = floorTexture; floorMat.emissiveColor = new BABYLON.Color3(.08,.045,.03); floorMat.roughness = .88; floorMat.metallic = 0;
  ground.material = floorMat;
  ground.receiveShadows = true;

  const campus = BABYLON.MeshBuilder.CreateGround("circus-campus", { width: 112, height: 142, subdivisions: 2 }, scene);
  campus.position = new BABYLON.Vector3(0, -.3, 38);
  const campusMat = new BABYLON.PBRMaterial("campus-mat", scene);
  campusMat.albedoColor = BABYLON.Color3.FromHexString("#4aa988"); campusMat.roughness = .93;
  campus.material = campusMat; campus.receiveShadows = true;
  for (let i=0; i<18; i++) {
    const light = BABYLON.MeshBuilder.CreateSphere(`grounds-lantern-${i}`, { diameter: .42, segments: 8 }, scene);
    light.position = new BABYLON.Vector3((i%2 ? -1 : 1) * (7 + (i%3)*6), 1.1, 25 + Math.floor(i/2)*6);
    light.material = material(`grounds-lantern-mat-${i}`, i%3 ? "#ffe46b" : "#72e7ef", .16);
  }

  const shadow = new BABYLON.ShadowGenerator(1024, sun);
  shadow.usePercentageCloserFiltering = true;
  shadow.blurKernel = 16;
  worldView.shadow = shadow;

  createCircusInterior();
  createRain();
  scene.onBeforeRenderObservable.add(animateWorld);
  worldView.engine.runRenderLoop(() => { if (!worldView.renderPaused) scene.render(); });
  window.addEventListener("resize", () => worldView.engine.resize());
  document.addEventListener("visibilitychange", () => { worldView.renderPaused = document.hidden; });
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

function createCircusInterior() { CircusArt.environment(); ImportedCharacters.loadCaine(); }

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
  if (!worldView.locations.has(location.id)) CircusArt.location(location);
}

function syncPaths(locations) {
  // Connectivity is semantic; no prescribed tracks are drawn.
}

function createCharacter(character, index) {
  CircusArt.character(character, index);
  if(character.id === "pomni") ImportedCharacters.loadPomni(worldView.characters.get(character.id));
}

function spatialPoint(location, point) {
  return {x:location.root.position.x+Number(point?.x||0),z:location.root.position.z+Number(point?.z||0)};
}

function navigationTarget(view, location) {
  const group=location.location.adventure_id||"hub";
  for(let attempt=0;attempt<25;attempt++){
    const angle=Math.random()*Math.PI*2,radius=2+Math.random()*6;
    const p={x:location.root.position.x+Math.cos(angle)*radius,z:location.root.position.z+Math.sin(angle)*radius};
    if(worldView.navigation.clear(p.x,p.z,group))return p;
  }
  return worldView.navigation.nearest(location.root.position,group);
}

function moveCharacter(view, locationId, spatial=null) {
  const location=worldView.locations.get(locationId);if(!location)return;
  const group=location.location.adventure_id||"hub";
  const requested=spatial?.target?spatialPoint(location,spatial.target):navigationTarget(view,location);
  const target=requested&&worldView.navigation.nearest(requested,group);if(!target)return;
  const token=++view.portalToken;
  if(group!==view.group){
    view.movement=null;view.portalUntil=performance.now()+850;
    window.setTimeout(()=>{
      if(token!==view.portalToken)return;
      const reported=spatial?.position?spatialPoint(location,spatial.position):target;
      const entry=worldView.navigation.nearest(reported,group)||target;
      view.root.position.set(entry.x,0,entry.z);view.group=group;
      const path=worldView.navigation.route(view.root.position,target,group);
      view.movement=path.length?{path,index:1,velocity:BABYLON.Vector3.Zero(),blocked:0}:null;
    },400);
    glitchFlash();
  } else {
    view.portalUntil=0;
    const path=worldView.navigation.route(view.root.position,target,group);
    view.movement=path.length?{path,index:1,velocity:view.movement?.velocity||BABYLON.Vector3.Zero(),blocked:0}:null;
  }
  view.locationId=locationId;view.idleUntil=performance.now()+5000+Math.random()*5000;
}

function syncSpatialCharacter(view,character) {
  const spatial=character.spatial;if(!spatial)return;
  view.spatialControlled=true;
  view.activity=spatial.activity;view.activityPhase=spatial.phase;view.activityPlan=spatial.plan||[];view.activityTargetId=spatial.target_id;
  const target=spatial.target||spatial.position;
  const key=`${spatial.location_id}:${spatial.revision}:${Number(target.x).toFixed(2)}:${Number(target.z).toFixed(2)}`;
  if(view.spatialKey!==key){view.spatialKey=key;moveCharacter(view,character.location_id,spatial);}
}

const CAINE_CHECK_LINES = [
  target => `${target}! Your routine check-in has arrived. Continue being delightfully unpredictable!`,
  target => `A quick wellness inspection, ${target}. Limbs accounted for, spirits measurable, excellent!`,
  target => `${target}, your ringmaster is checking in. Any adventure-related existential inconveniences?`,
  target => `Just making my rounds, ${target}! Everything sufficiently spectacular over here?`,
  target => `${target}! This is a completely ordinary, non-invasive morale check. Smile if applicable!`,
  target => `Status check, ${target}: present, active, and not abstracted. Splendid!`,
];

function syncCaine(spatial) {
  if(!spatial||!worldView.caine)return;
  const location=worldView.locations.get(spatial.location_id);if(!location)return;
  const point=spatialPoint(location,spatial.position);
  const prior=worldView.caineSpatial;
  const changedRoom=prior&&prior.locationId!==spatial.location_id;
  worldView.caineSpatial={
    locationId:spatial.location_id,targetId:spatial.target_id,phase:spatial.phase,
    destination:new BABYLON.Vector3(point.x,6,point.z),portalUntil:changedRoom?performance.now()+700:prior?.portalUntil||0,
    talkingUntil:prior?.talkingUntil||0,lastCheckCount:prior?.lastCheckCount??-1,
  };
  if(!prior)worldView.caine.position.set(point.x,6,point.z);
  if(changedRoom){
    const token=spatial.revision;
    worldView.caineSpatial.portalToken=token;
    window.setTimeout(()=>{
      if(worldView.caineSpatial?.portalToken!==token)return;
      worldView.caine.position.copyFrom(worldView.caineSpatial.destination);
    },350);
    glitchFlash();
  }
  if(spatial.phase==='checking'&&worldView.caineSpatial.lastCheckCount!==spatial.check_count){
    worldView.caineSpatial.lastCheckCount=spatial.check_count;
    const person=worldView.state?.characters.find(item=>item.id===spatial.target_id);
    if(person){
      const line=CAINE_CHECK_LINES[spatial.check_count%CAINE_CHECK_LINES.length](person.name);
      worldView.caineSpatial.talkingUntil=performance.now()+Math.max(2200,line.length*48);
      showSpeech('caine',line);speak('caine',line);
    }
  }
}

function updateCharacterSteering(view, deltaSeconds) {
  const now=performance.now();
  if(view.portalUntil>now){const t=1-(view.portalUntil-now)/850;view.root.scaling.setAll(Math.max(.06,Math.abs(t*2-1)));return 0;}
  view.root.scaling.setAll(1);
  if(!view.movement){
    const partner=view.activityTargetId&&worldView.characters.get(view.activityTargetId);
    if(partner&&partner.group===view.group){
      const dx=partner.root.position.x-view.root.position.x,dz=partner.root.position.z-view.root.position.z;
      const facing=Math.atan2(-dx,-dz),turn=Math.atan2(Math.sin(facing-view.root.rotation.y),Math.cos(facing-view.root.rotation.y));
      view.root.rotation.y+=turn*(1-Math.exp(-deltaSeconds*6));
    }
    if(!view.spatialControlled&&now>view.idleUntil&&now>view.gestureUntil&&!worldView.paused&&now>view.talkingUntil)moveCharacter(view,view.locationId);
    return 0;
  }
  if(worldView.paused)return 0;
  const move=view.movement,waypoint=move.path[move.index];
  if(!waypoint){view.movement=null;return 0;}
  const delta=new BABYLON.Vector3(waypoint.x-view.root.position.x,0,waypoint.z-view.root.position.z);
  const distance=delta.length(),last=move.index===move.path.length-1;
  if(distance<(last?.18:.08)){
    if(last){view.movement=null;view.idleUntil=now+3000+Math.random()*5500;return 0;}
    move.index++;return move.velocity.length();
  }
  const desired=delta.normalize().scale(view.speed*Math.min(1,distance/(last?1.3:.55)));
  const separationRadius=1.35;
  for(const other of worldView.characters.values()){
    if(other===view||other.group!==view.group)continue;
    const away=view.root.position.subtract(other.root.position);away.y=0;const gap=away.length();
    if(gap>.01&&gap<separationRadius)desired.addInPlace(away.scale((separationRadius-gap)/gap*2));
  }
  move.velocity=BABYLON.Vector3.Lerp(move.velocity,desired,1-Math.exp(-deltaSeconds*7));
  const step=move.velocity.scale(deltaSeconds),p=view.root.position;
  let candidate={x:p.x+step.x,z:p.z+step.z};
  if(!worldView.navigation.line(p,candidate,view.group)){
    // At tight corners, discard inertial sideways drift and follow the clear
    // route tangent. Sliding along a wall can otherwise stall forever.
    const tangent=delta.scale(Math.min(distance,view.speed*deltaSeconds));
    candidate={x:p.x+tangent.x,z:p.z+tangent.z};
    move.velocity=tangent.scale(1/Math.max(.001,deltaSeconds));
    if(!worldView.navigation.line(p,candidate,view.group)){
      move.velocity.scaleInPlace(.2);move.blocked+=deltaSeconds;
      if(move.blocked>.8){
        const path=worldView.navigation.route(p,move.path[move.path.length-1],view.group);
        view.movement=path.length?{path,index:1,velocity:BABYLON.Vector3.Zero(),blocked:0}:null;
      }
      return 0;
    }
  }
  const actual=Math.hypot(candidate.x-p.x,candidate.z-p.z)/Math.max(.001,deltaSeconds);
  move.blocked=0;
  p.x=candidate.x;p.z=candidate.z;
  const targetRotation=Math.atan2(-move.velocity.x,-move.velocity.z);
  const turn=Math.atan2(Math.sin(targetRotation-view.root.rotation.y),Math.cos(targetRotation-view.root.rotation.y));
  view.root.rotation.y+=turn*(1-Math.exp(-deltaSeconds*8));
  return actual;
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

function syncGloinks(population) {
  const visibleCount = Math.min(12, Math.max(0, Number(population) || 0));
  while (worldView.gloinks.length > visibleCount) worldView.gloinks.pop().dispose();
  while (worldView.gloinks.length < visibleCount) {
    const index = worldView.gloinks.length;
    const gloink = new BABYLON.TransformNode(`gloink-${index}`,worldView.scene);
    const body = BABYLON.MeshBuilder.CreatePolyhedron(`gloink-body-${index}`, { type: 2, size: .55 }, worldView.scene);
    body.parent=gloink;body.material = material(`gloink-mat-${index}`, index % 2 ? "#65dce1" : "#e8d04c", .28);
    for(const side of [-1,1]){
      const eye=BABYLON.MeshBuilder.CreateSphere(`gloink-eye-${index}-${side}`,{diameter:.18,segments:8},worldView.scene);
      eye.parent=gloink;eye.position.set(side*.17,.15,-.43);eye.material=material(`gloink-eye-mat-${index}-${side}`,"#fff4cf",.4);
      const foot=BABYLON.MeshBuilder.CreateSphere(`gloink-foot-${index}-${side}`,{diameter:.2,segments:8},worldView.scene);
      foot.parent=gloink;foot.position.set(side*.28,-.47,0);foot.material=material(`gloink-foot-mat-${index}-${side}`,"#482654",.5);
    }
    gloink.metadata = { home: new BABYLON.Vector3(-5 + (index%6)*1.8, .62, 12 + Math.floor(index/6)*1.8), phase: index * .83 };
    gloink.position.copyFrom(gloink.metadata.home);
    worldView.shadow.addShadowCaster(body);
    worldView.gloinks.push(gloink);
  }
}

function syncActivitySpots(living) {
  for(const spot of living?.activity_spots||[]){
    let view=worldView.activitySpots.get(spot.id);
    if(!view){
      const location=worldView.locations.get(spot.location_id);if(!location)continue;
      const root=new BABYLON.TransformNode(`activity-${spot.id}`,worldView.scene);
      root.position.set(location.root.position.x+spot.x,.08,location.root.position.z+spot.z);
      const ring=BABYLON.MeshBuilder.CreateTorus(`activity-ring-${spot.id}`,{diameter:1.25,thickness:.045,tessellation:24},worldView.scene);
      ring.parent=root;ring.material=CircusArt.mat(spot.kind==="danger"?"#ef4965":spot.kind==="rest"?"#6bd6bc":"#ffd05b",.4,.35);
      const orb=BABYLON.MeshBuilder.CreateSphere(`activity-orb-${spot.id}`,{diameter:.13,segments:8},worldView.scene);
      orb.parent=root;orb.position.y=.12;orb.material=ring.material;
      view={root,ring,orb,occupied:0,phase:Math.random()*6.28};worldView.activitySpots.set(spot.id,view);
    }
    view.occupied=Number(spot.occupied)||0;
  }
}

function updateSystemLighting(systems) {
  if (!systems || !worldView.scene) return;
  const stability = Number(systems.digital_stability ?? 1);
  worldView.scene.imageProcessingConfiguration.contrast = 1.02 + stability * .14;
  worldView.showLights.forEach((light, index) => {
    light.intensity = .45 + Number(systems.audience_excitement ?? .4) * .5 + index * .04;
  });
}

function applyState(state) {
  worldView.state = state;
  state.locations.forEach(buildLocation);
  syncPaths(state.locations);
  state.characters.forEach((character, index) => {
    if (!worldView.characters.has(character.id)) createCharacter(character, index);
    const view = worldView.characters.get(character.id);
    if(character.spatial)syncSpatialCharacter(view,character);
    else if (view.locationId !== character.location_id) moveCharacter(view, character.location_id);
    view.expression = character.dominant_emotion || "curiosity";
  });
  syncCaine(state.living_world?.director);
  syncObjects(state.objects || []);
  syncGloinks(state.systems?.gloink_population || 0);
  syncActivitySpots(state.living_world);
  updateSystemLighting(state.systems);
  updateWeather(state.weather, state.time.is_night);
  renderDashboard(state);
  StoryPresentation.sync(state);
}

function updateWeather(weather, isNight) {
  if (!worldView.scene) return;
  const palette = isNight ? [0.035, .07, .11] : weather === "storm" ? [.18,.24,.27] : weather === "fog" ? [.54,.6,.58] : [.56,.72,.72];
  worldView.scene.clearColor = new BABYLON.Color4(...palette, 1);
  worldView.scene.fogColor = new BABYLON.Color3(...palette);
  worldView.scene.fogDensity = weather === "fog" ? .026 : weather === "storm" ? .011 : .005;
  worldView.sun.intensity = isNight ? .65 : weather === "storm" ? .85 : 1.3;
  worldView.rain.emitRate = weather === "storm" ? 850 : weather === "rain" ? 450 : 0;
}

function animateWorld() {
  const now = performance.now();
  const deltaSeconds = Math.min(.05, (worldView.engine?.getDeltaTime() || 16) / 1000);
  animateCaine(now,deltaSeconds);
  StoryPresentation.animate(now,deltaSeconds);
  for(const view of worldView.characters.values()){
    const speed=updateCharacterSteering(view,deltaSeconds);
    view.stepPhase+=speed*deltaSeconds*2.4;
    if(view.importedModel) ImportedCharacters.animate(view,now,deltaSeconds,speed);
    else CircusArt.animate(view,now,deltaSeconds,speed);
  }
  for (const object of worldView.objects.values()) object.mesh.rotation.y += .008;
  worldView.gloinks.forEach((gloink, index) => {
    const phase = now * .0012 + gloink.metadata.phase;
    gloink.position.x = gloink.metadata.home.x + Math.sin(phase) * 1.25;
    gloink.position.z = gloink.metadata.home.z + Math.cos(phase * .77) * .8;
    gloink.position.y = .62 + Math.abs(Math.sin(phase * 2.4)) * .42;
    gloink.rotation.y += .018 + index * .0002;
  });
  worldView.portalRings.forEach((ring, index) => { ring.rotation.z += (index % 2 ? -.004 : .004) * (index + 1); });
  worldView.animatedProps.forEach(prop=>{if(prop.kind==="wheel")prop.node.rotation.z-=deltaSeconds*.22;else prop.node.rotation.y+=deltaSeconds*.25;});
  worldView.activitySpots.forEach(view=>{
    const pulse=1+Math.sin(now*.003+view.phase)*.12;
    view.root.scaling.setAll(view.occupied?pulse:1);view.root.setEnabled(view.occupied>0);
  });
  worldView.showLights.forEach((light, index) => { light.direction.x = Math.sin(now*.00035 + index*2) * .35; });
  if (now - performanceState.lastCheck > 3000 && worldView.engine) {
    const fps = worldView.engine.getFps();
    const nextQuality = fps < 20 ? 2 : fps < 34 ? 1.6 : fps < 48 ? 1.25 : fps > 57 ? 1 : performanceState.quality;
    worldView.scene.shadowsEnabled = fps >= 25;
    if (nextQuality !== performanceState.quality) {
      performanceState.quality = nextQuality;
      worldView.engine.setHardwareScalingLevel(nextQuality);
    }
    performanceState.lastCheck = now;
  }
  updateCameraDirector(now);
  positionOverlays();
}

function animateCaine(now,deltaSeconds) {
  const root=worldView.caine,state=worldView.caineSpatial;if(!root)return;
  if(!state){root.position.y=6+Math.sin(now*.0017)*.16;return;}
  const portal=state.portalUntil>now;
  if(portal){
    const t=1-(state.portalUntil-now)/700;
    root.scaling.setAll(Math.max(.06,Math.abs(t*2-1)));
    ImportedCharacters.animateCaine(now,deltaSeconds,false,false,false);return;
  }
  root.scaling.setAll(1);
  const delta=state.destination.subtract(root.position);delta.y=0;
  const distance=delta.length(),moving=!worldView.paused&&distance>.12;
  if(moving){
    const speed=Math.min(7,Math.max(1.8,distance*.9));
    const step=Math.min(distance,speed*deltaSeconds);
    const direction=delta.scale(1/Math.max(distance,.001));
    root.position.addInPlace(direction.scale(step));
    const facing=Math.atan2(-direction.x,-direction.z);
    const turn=Math.atan2(Math.sin(facing-root.rotation.y),Math.cos(facing-root.rotation.y));
    root.rotation.y+=turn*(1-Math.exp(-deltaSeconds*7));
  }else if(state.targetId){
    const target=worldView.characters.get(state.targetId)?.root;
    if(target){
      const look=target.position.subtract(root.position),facing=Math.atan2(-look.x,-look.z);
      const turn=Math.atan2(Math.sin(facing-root.rotation.y),Math.cos(facing-root.rotation.y));
      root.rotation.y+=turn*(1-Math.exp(-deltaSeconds*5));
    }
  }
  root.position.y=6+Math.sin(now*.0017)*.16;
  const talking=now<state.talkingUntil;
  ImportedCharacters.animateCaine(now,deltaSeconds,moving,state.phase==='checking',talking);
}

function updateCameraDirector(now) {
  if (!cameraDirector.enabled || now < cameraDirector.manualUntil) return;
  if (cameraDirector.followId && now < cameraDirector.followUntil) {
    const target = worldView.characters.get(cameraDirector.followId)?.root.position;
    if (target) worldView.camera.target = BABYLON.Vector3.Lerp(worldView.camera.target, target.add(new BABYLON.Vector3(0,2.5,0)), .035);
  } else if (now - cameraDirector.lastShotAt > 22000 && worldView.state) {
    const adventure = worldView.state.adventures?.find(item => item.status === "active");
    const targetId = adventure?.participants?.[0];
    if (targetId) frameCharacter(targetId, "medium");
    else frameLocation("main_tent", "wide");
  }
}

function screenPoint(position) {
  const viewport = worldView.camera.viewport.toGlobal(ui.canvas.clientWidth, ui.canvas.clientHeight);
  return BABYLON.Vector3.Project(position, BABYLON.Matrix.Identity(), worldView.scene.getTransformMatrix(), viewport);
}

function positionOverlays() {
  for (const location of worldView.locations.values()) {
    const point = screenPoint(location.root.position.add(location.anchor));
    location.label.style.left = `${point.x}px`; location.label.style.top = `${point.y}px`;
    const near=BABYLON.Vector3.Distance(location.root.position,worldView.camera.target)<35;
    location.label.style.opacity = near && point.z > 0 && point.z < 1 && point.y > 100 ? "1" : "0";
  }
  for (const bubble of ui.speech.children) {
    const view = worldView.characters.get(bubble.dataset.actor);
    const speaker = view?.root || (bubble.dataset.actor === "caine" ? worldView.caine : null);
    if (!speaker) continue;
    const point = screenPoint(speaker.position.add(new BABYLON.Vector3(0, view ? 5.8 : 2.8, 0)));
    bubble.style.visibility=point.z>0&&point.z<1&&point.y>130&&point.y<ui.canvas.clientHeight-150?"visible":"hidden";
    bubble.style.left = `${point.x}px`; bubble.style.top = `${point.y}px`;
  }
}

function renderDashboard(state) {
  ui.worldTime.textContent = state.time.label.replace(" - ", " · ");
  ui.weather.textContent = state.weather[0].toUpperCase() + state.weather.slice(1);
  ui.tick.textContent = `Tick ${state.tick}`;
  if (state.director) {
    const suffix = state.director.last_event_day === state.time.day ? "today's adventure is live" : "preparing today's adventure";
    const pacing = state.director.pacing;
    ui.director.textContent = pacing
      ? `${state.director.name} · ${pacing.arc_stage.replaceAll("_", " ")} · tension ${Math.round(pacing.tension*100)}%`
      : `${state.director.name} · ${suffix}`;
    ui.director.title = suffix;
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
    const spatial=character.spatial;
    const activeStep=spatial?.plan?.find(step=>step.status==="active")?.label;
    card.appendChild(node("p", "activity-line", `${spatial?.phase||"thinking"} · ${(spatial?.activity||"observing").replaceAll("_"," ")}`));
    card.appendChild(node("p", "intention", activeStep || (character.intention ? character.intention.description : character.goal || "Observing the world")));
    if (character.psychology) {
      const mind = node("p", "psychology-line", `${Math.round(character.psychology.reputation*100)}% reputation${character.psychology.strongest_habit ? ` · habit: ${character.psychology.strongest_habit}` : ""}`);
      mind.title = `${character.psychology.identity}\nAmbition: ${character.psychology.ambition}`;
      card.appendChild(mind);
    }
    const energy = node("div", "energy-row"); energy.appendChild(node("span", "", "Energy"));
    const track = node("div", "energy-track"); const fill = node("div", "energy-fill");
    fill.style.width = `${Math.max(0, Math.min(100, character.physical.energy / character.physical.max_energy * 100))}%`;
    track.appendChild(fill); energy.appendChild(track); energy.appendChild(node("span", "", `${character.physical.energy}/${character.physical.max_energy}`)); card.appendChild(energy);
    card.addEventListener("click", () => focusCharacter(character.id)); ui.characters.appendChild(card);
  });
  renderAdventure(state.adventures || [], state.episodes || [], state.systems || null);
}

function renderAdventure(adventures, episodes, systems) {
  if(!document.getElementById('story-scene')){
    const panel=node('div','story-scene');panel.id='story-scene';panel.hidden=true;
    ui.adventurePanel.prepend(panel);
  }
  document.getElementById('story-scene').hidden=!adventures.some(a=>a.story?.title&&a.status==='active');
  const adventure = adventures.find(item => item.status === "active") || adventures[adventures.length - 1];
  const episode = episodes.find(item => item.status === "active") || episodes[episodes.length - 1];
  ui.adventurePanel.classList.remove("hidden");
  ui.adventureTitle.textContent = adventure?.title || "The circus between adventures";
  const adventureEnded = adventure && adventure.status !== "active";
  ui.adventurePremise.textContent = adventure ? (adventureEnded ? adventure.outcome || `The adventure ${adventure.status}.` : adventure.premise) : "The cast's choices continue to change the tent.";
  ui.adventureStakes.textContent = adventure ? (adventureEnded ? `${adventure.status === "resolved" ? "Resolved" : "Expired"} by ${adventure.resolved_by || "world events"}` : `At stake: ${adventure.stakes}`) : "Caine creates one new event each world day.";
  ui.adventurePhases.replaceChildren(); const phaseIndex = adventure ? PHASES.indexOf(adventure.phase) : -1;
  PHASES.forEach((phase, index) => { const segment = node("i", `phase ${index <= phaseIndex ? "done" : ""}`); segment.title = phase; ui.adventurePhases.appendChild(segment); });
  ui.questObjectives.replaceChildren();
  for (const objective of adventure?.objectives || []) {
    const item = node("div", `quest-objective ${objective.status === "complete" ? "complete" : ""}`, objective.description);
    item.title = objective.completed_by ? `Completed by ${objective.completed_by}` : "Pending";
    ui.questObjectives.appendChild(item);
  }
  ui.episodeNumber.textContent = episode ? `Episode ${episode.number} · ${episode.status}` : "Episode waiting";
  ui.episodeTitle.textContent = episode?.title || "The next circus day has not begun";
  ui.episodeOutcome.textContent = episode?.key_outcomes?.at(-1) || episode?.premise || "Caine is preparing a premise.";
  ui.worldSystems.replaceChildren();
  if (systems) {
    const meters = [
      ["Show", String(systems.show_phase || "unknown").replaceAll("_", " ")],
      ["Stability", `${Math.round(systems.digital_stability*100)}%`],
      ["Audience", `${Math.round(systems.audience_excitement*100)}%`],
      ["Cohesion", `${Math.round(systems.cast_cohesion*100)}%`],
      ["Props", `${Math.round(systems.prop_condition*100)}%`],
      ["Gloinks", String(systems.gloink_population)],
    ];
    meters.forEach(([label, value]) => { const meter = node("div", "system-meter"); meter.append(node("span", "", label), node("b", "", value)); ui.worldSystems.appendChild(meter); });
  }
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

function startAudio() {
  if (!soundState.enabled) return;
  if (!soundState.context) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) { ui.sound.disabled = true; ui.sound.textContent = "Sound unavailable"; return; }
    soundState.context = new AudioContext();
    soundState.master = soundState.context.createGain();
    soundState.master.gain.value = .16;
    soundState.master.connect(soundState.context.destination);
  }
  soundState.context.resume();
  if (soundState.started) return;
  soundState.started = true;
  [130.81, 196, 261.63].forEach((frequency, index) => {
    const oscillator = soundState.context.createOscillator();
    const gain = soundState.context.createGain();
    oscillator.type = index === 1 ? "triangle" : "sine";
    oscillator.frequency.value = frequency;
    gain.gain.value = index === 2 ? .012 : .018;
    oscillator.connect(gain); gain.connect(soundState.master); oscillator.start();
    soundState.ambient.push({ oscillator, gain });
  });
}

function playEventSound(kind) {
  if (!soundState.enabled || !soundState.context || !soundState.master) return;
  const now = soundState.context.currentTime;
  const oscillator = soundState.context.createOscillator();
  const gain = soundState.context.createGain();
  const important = kind.includes("adventure") || kind === "environment_changed";
  oscillator.type = kind === "action_rejected" || kind === "lied" ? "sawtooth" : "triangle";
  oscillator.frequency.setValueAtTime(important ? 392 : 523.25, now);
  oscillator.frequency.exponentialRampToValueAtTime(important ? 783.99 : 659.25, now + .18);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(important ? .22 : .08, now + .018);
  gain.gain.exponentialRampToValueAtTime(.0001, now + (important ? .55 : .22));
  oscillator.connect(gain); gain.connect(soundState.master); oscillator.start(now); oscillator.stop(now + .6);
}

function burstConfetti(locationId) {
  const origin = worldView.locations.get(locationId)?.root.position || new BABYLON.Vector3(0,5,0);
  const texture = new BABYLON.DynamicTexture("confetti-pixel", 16, worldView.scene, false);
  const context = texture.getContext(); context.fillStyle = "white"; context.fillRect(2,2,12,12); texture.hasAlpha = true; texture.update();
  const particles = new BABYLON.ParticleSystem("episode-confetti", 110, worldView.scene);
  particles.particleTexture = texture; particles.emitter = origin.add(new BABYLON.Vector3(0,4,0));
  particles.color1 = new BABYLON.Color4(1,.25,.35,1); particles.color2 = new BABYLON.Color4(.25,.85,1,1); particles.colorDead = new BABYLON.Color4(1,.85,.2,0);
  particles.minSize=.08; particles.maxSize=.28; particles.minLifeTime=.8; particles.maxLifeTime=1.8;
  particles.emitRate=0; particles.manualEmitCount=90; particles.minEmitPower=3; particles.maxEmitPower=8;
  particles.direction1=new BABYLON.Vector3(-1.8,4,-1.8); particles.direction2=new BABYLON.Vector3(1.8,7,1.8); particles.gravity=new BABYLON.Vector3(0,-8,0);
  particles.start(); window.setTimeout(() => { particles.stop(); particles.dispose(); texture.dispose(); }, 2300);
}

function glitchFlash() {
  ui.vfxFlash.classList.remove("active");
  void ui.vfxFlash.offsetWidth;
  ui.vfxFlash.classList.add("active");
}

function animateEvents(events) {
  for (const event of events) {
    if(event.data?.story_dialogue){
      const speaker=event.data.speaker;
      if(worldView.characters.has(event.actor_id)){showSpeech(event.actor_id,event.summary);speak(event.actor_id,event.summary);}
      else if(speaker==='Caine'){showSpeech('caine',event.summary);speak('caine',event.summary);}
      else showNotice(`${speaker}: ${event.summary}`);
    }
    playEventSound(event.kind);
    if ((event.kind === "spoke" || event.kind === "lied") && event.actor_id) {
      const words = event.data.message || event.summary;
      showSpeech(event.actor_id, words); speak(event.actor_id, words);
    }
    if (!event.actor_id && ["adventure_started", "situation_created", "weather_changed", "environment_changed"].includes(event.kind)) {
      showSpeech("caine", event.summary); speak("caine", event.summary);
    }
    if (event.kind.includes("adventure") && event.location_id) pulseLocation(event.location_id);
    if (event.kind === "adventure_resolved") burstConfetti(event.location_id || "center_stage");
    if (event.kind === "adventure_started" || event.kind === "environment_changed") glitchFlash();
    if (event.actor_id) animateAction(event);
  }
  directCamera(events);
}

function animateAction(event) {
  const view=worldView.characters.get(event.actor_id);if(!view)return;
  view.gesture=event.kind;view.gestureUntil=performance.now()+1600;
  if(["spoke","lied","helped"].includes(event.kind)){
    const other=worldView.characters.get(event.data?.target_id);
    if(other&&!view.movement){const d=other.root.position.subtract(view.root.position);if(d.length()>.1)view.root.rotation.y=Math.atan2(-d.x,-d.z);}
  }
}

function directCamera(events) {
  if (!cameraDirector.enabled || performance.now() < cameraDirector.manualUntil || !events.length) return;
  const score = event => event.importance + (event.kind.includes("adventure") ? .6 : event.kind === "spoke" ? .18 : event.kind === "weather_changed" ? .3 : 0);
  const focus = events.slice().sort((a,b) => score(b)-score(a))[0];
  if (!focus || performance.now()-cameraDirector.lastShotAt < 7000) return;
  if (focus.actor_id) {
    const targetId = focus.data?.target_id;
    if (targetId && worldView.characters.has(targetId) && ["spoke","lied","helped"].includes(focus.kind)) frameConversation(focus.actor_id, targetId);
    else frameCharacter(focus.actor_id, score(focus) > 1 ? "close" : "medium");
  } else if (["adventure_started","situation_created","weather_changed","environment_changed"].includes(focus.kind)) {
    if (focus.kind === "adventure_started" && worldView.caine) framePoint(worldView.caine.position, "close");
    else if (focus.location_id) frameLocation(focus.location_id, "wide");
  }
}

function frameConversation(firstId, secondId) {
  const first = worldView.characters.get(firstId)?.root.position;
  const second = worldView.characters.get(secondId)?.root.position;
  if (!first || !second) return;
  framePoint(BABYLON.Vector3.Center(first, second), "medium");
  cameraDirector.followId = firstId; cameraDirector.followUntil = performance.now() + 6500;
}

function frameCharacter(characterId, shot = "medium") {
  const view = worldView.characters.get(characterId); if (!view) return;
  framePoint(view.root.position, shot); cameraDirector.followId = characterId;
  cameraDirector.followUntil = performance.now() + 7000;
}

function frameLocation(locationId, shot = "wide") {
  const location = worldView.locations.get(locationId); if (location) framePoint(location.root.position, shot);
}

function framePoint(point, shot) {
  const radius = shot === "grounds" ? 110 : shot === "close" ? 13 : shot === "wide" ? 55 : 24;
  const ease = new BABYLON.CubicEase(); ease.setEasingMode(BABYLON.EasingFunction.EASINGMODE_EASEINOUT);
  BABYLON.Animation.CreateAndStartAnimation("cinematic-target", worldView.camera, "target", 30, 42, worldView.camera.target.clone(), point.clone(), BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT, ease);
  BABYLON.Animation.CreateAndStartAnimation("cinematic-radius", worldView.camera, "radius", 30, 42, worldView.camera.radius, radius, BABYLON.Animation.ANIMATIONLOOPMODE_CONSTANT, ease);
  cameraDirector.lastShotAt = performance.now();
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
  const view=worldView.characters.get(actorId);if(view){view.gesture="inspected";view.gestureUntil=performance.now()+1000;}
}

function focusCharacter(characterId) {
  const view = worldView.characters.get(characterId); if (!view) return;
  cameraDirector.followId=characterId;cameraDirector.followUntil=performance.now()+60000;
  cameraDirector.manualUntil=0;
  framePoint(view.root.position.add(new BABYLON.Vector3(0,2.5,0)), "close");
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
    else if (message.type === "control_state") { worldView.paused = message.paused; ui.pause.textContent = message.paused ? "Resume" : "Pause"; ui.speed.value = String(message.speed); }
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
document.getElementById("view-hub").addEventListener("click",()=>{
  cameraDirector.followId=null;cameraDirector.manualUntil=performance.now()+60000;
  framePoint(new BABYLON.Vector3(0,2,35),"grounds");
});
document.getElementById("view-cast").addEventListener("click",()=>focusCharacter("pomni"));
document.getElementById("hide-panels").addEventListener("click",event=>{
  const hidden=document.body.classList.toggle("cinema-view");event.target.textContent=hidden?"Show panels":"Cinema view";event.target.setAttribute("aria-pressed",String(hidden));
});
ui.speed.addEventListener("change", () => sendControl("speed", Number(ui.speed.value)));
ui.voices.addEventListener("click", () => {
  voiceState.enabled = !voiceState.enabled;
  localStorage.setItem("circus-voices", voiceState.enabled ? "on" : "off");
  if (!voiceState.enabled && voiceState.supported) window.speechSynthesis.cancel();
  renderVoiceControls();
});
ui.sound.addEventListener("click", () => {
  soundState.enabled = !soundState.enabled;
  localStorage.setItem("circus-sound", soundState.enabled ? "on" : "off");
  ui.sound.textContent = soundState.enabled ? "Sound on" : "Sound off";
  if (soundState.enabled) {
    startAudio();
    if (soundState.master) soundState.master.gain.value = .16;
  } else if (soundState.master) soundState.master.gain.value = 0;
});
ui.cinematic.addEventListener("click", () => {
  cameraDirector.enabled = !cameraDirector.enabled;
  localStorage.setItem("circus-cinematic", cameraDirector.enabled ? "on" : "off");
  ui.cinematic.textContent = cameraDirector.enabled ? "Cinematic on" : "Cinematic off";
  cameraDirector.manualUntil = 0;
});
ui.cinematic.textContent = cameraDirector.enabled ? "Cinematic on" : "Cinematic off";
ui.canvas.addEventListener("pointerdown", () => { cameraDirector.manualUntil = performance.now() + 12000; });
ui.volume.addEventListener("input", () => {
  voiceState.volume = Number(ui.volume.value); localStorage.setItem("circus-volume", String(voiceState.volume));
});
refreshVoices();
ui.sound.textContent = soundState.enabled ? "Sound on" : "Sound off";
if (voiceState.supported) window.speechSynthesis.addEventListener("voiceschanged", refreshVoices);
window.addEventListener("pointerdown", () => {
  if (voiceState.supported && voiceState.enabled) window.speechSynthesis.resume();
  startAudio();
}, { once: true });
renderVoiceControls();
window.setInterval(() => {
  if (worldView.socket?.readyState === WebSocket.OPEN && Date.now() - worldView.lastSeenAt > 15000) {
    worldView.socket.close();
  }
}, 5000);
createWorld();
if (worldView.scene) connect();
