"use strict";

// Original procedural models: smooth toy surfaces, cloth silhouettes, expressive
// faces and theatrical architecture. All meshes are generated locally in WebGL.
const CircusArt = {
  materials: new Map(), serial: 0,
  batchStatic(root) {
    // Batch scenery by material into a handful of draw calls; rigged actors
    // remain separate so their joints and expressions can animate.
    const groups=new Map();
    for(const mesh of root.getChildMeshes()) {
      let ancestor=mesh.parent,dynamic=false;
      while(ancestor&&ancestor!==root){if(ancestor.metadata?.dynamic){dynamic=true;break;}ancestor=ancestor.parent;}
      if(dynamic||mesh.metadata?.dynamic)continue;
      const key=mesh.material.uniqueId;
      if(!groups.has(key))groups.set(key,[]);
      groups.get(key).push(mesh);mesh.computeWorldMatrix(true);
      worldView.shadow?.removeShadowCaster(mesh);
    }
    for(const meshes of groups.values()) {
      const merged=BABYLON.Mesh.MergeMeshes(meshes,true,true,undefined,false,false);
      if(merged){merged.receiveShadows=true;merged.freezeWorldMatrix();}
    }
  },
  mat(color, roughness=.45, glow=0) {
    const key=`${color}:${roughness}:${glow}`;
    if(this.materials.has(key))return this.materials.get(key);
    const m=new BABYLON.StandardMaterial(`art-${key}`,worldView.scene);
    m.diffuseColor=BABYLON.Color3.FromHexString(color);
    m.specularColor=new BABYLON.Color3(.32,.3,.27).scale(1-roughness);
    m.specularPower=64; m.emissiveColor=m.diffuseColor.scale(glow);
    this.materials.set(key,m); return m;
  },
  pivot(name,parent,position=[0,0,0]) { const n=new BABYLON.TransformNode(name,worldView.scene);n.parent=parent;n.position=BABYLON.Vector3.FromArray(position);return n; },
  mesh(kind,name,parent,options,p,color,roughness=.45) {
    const m=BABYLON.MeshBuilder[kind](`${name}-${this.serial++}`,options,worldView.scene);
    m.parent=parent;m.position=BABYLON.Vector3.FromArray(p);m.material=this.mat(color,roughness);m.receiveShadows=true;
    if(worldView.shadow)worldView.shadow.addShadowCaster(m);return m;
  },
  ball(name,parent,p,scale,color) {const m=this.mesh("CreateSphere",name,parent,{diameter:1,segments:24},p,color);m.scaling=BABYLON.Vector3.FromArray(scale);return m;},
  box(name,parent,p,size,color) {return this.mesh("CreateBox",name,parent,{width:size[0],height:size[1],depth:size[2]},p,color);},
  tube(name,parent,points,radius,color) {return this.mesh("CreateTube",name,parent,{path:points.map(p=>BABYLON.Vector3.FromArray(p)),radius,tessellation:12,cap:BABYLON.Mesh.CAP_ALL},[0,0,0],color);},
  lathe(name,parent,p,profile,color) { return this.mesh("CreateLathe",name,parent,{shape:profile.map(([x,y])=>new BABYLON.Vector3(x,y,0)),tessellation:48,cap:BABYLON.Mesh.CAP_ALL},p,color); },
  text(name,parent,p,text,width,height,color="#fff0bb",background="#56244a") {
    const m=this.mesh("CreatePlane",name,parent,{width,height,sideOrientation:BABYLON.Mesh.DOUBLESIDE},p,color);
    m.rotation.y=Math.PI;
    m.scaling.x=-1;
    const t=new BABYLON.DynamicTexture(`${name}-lettering`,{width:1024,height:256},worldView.scene,false);
    const c=t.getContext(); c.fillStyle=background;c.fillRect(0,0,1024,256);c.strokeStyle=color;c.lineWidth=7;c.strokeRect(12,12,1000,232);
    c.font=`bold ${text.length>24?45:65}px Georgia`;c.textAlign="center";c.textBaseline="middle";c.fillStyle=color;c.fillText(text,512,132,950);t.update();
    const mat=new BABYLON.StandardMaterial(`${name}-letters`,worldView.scene);mat.diffuseTexture=t;mat.emissiveColor=new BABYLON.Color3(.12,.12,.12);mat.specularColor=BABYLON.Color3.Black();m.material=mat;return m;
  },
  obstacle(root,x,z,w,d) { const p=root?root.position:BABYLON.Vector3.Zero();worldView.navigation.addObstacle(p.x+x,p.z+z,w,d); },
  glove(parent,p,color="#fff5df",size=.32) {
    const root=this.pivot("glove",parent,p);this.ball("palm",root,[0,0,0],[size,size*1.2,size*.65],color);
    for(let i=0;i<4;i++)this.ball("finger",root,[(i-1.5)*size*.2,-size*.43,0],[size*.24,size*.6,size*.27],color);
    this.ball("thumb",root,[size*.5,-size*.02,0],[size*.36,size*.65,size*.3],color).rotation.z=-.6;return root;
  },
  eye(parent,x,y,z,iris,scale=1) {
    const eye=this.pivot("eye",parent,[x,y,z]);
    this.ball("eye-white",eye,[0,0,0],[.47*scale,.59*scale,.21],"#fff6dd");
    this.ball("iris",eye,[0,-.015,-.11],[.22*scale,.29*scale,.08],iris);
    this.ball("pupil",eye,[0,-.015,-.153],[.085*scale,.2*scale,.035],"#201632");
    this.ball("catchlight",eye,[-.045,.055,-.176],[.07,.08,.023],"#ffffff");return eye;
  },
  character(character,index) {
    const id=character.id,root=this.pivot(`character-${id}`,null),body=this.pivot(`${id}-body`,root),head=this.pivot(`${id}-head-pivot`,body,[0,3.25,0]);
    const eyes=[],brows=[],knees=[],feet=[],ears=[];
    const leftArm=this.pivot(`${id}-shoulder-left`,body,[-.63,2.6,0]);
    const rightArm=this.pivot(`${id}-shoulder-right`,body,[.63,2.6,0]);
    const leftLeg=this.pivot(`${id}-hip-left`,body,[-.28,1.55,0]);
    const rightLeg=this.pivot(`${id}-hip-right`,body,[.28,1.55,0]);
    const skin="#f9e8cf",ink="#24162b",red="#df2943",blue="#273eb5",gold="#f3b92b",purple="#8b59b4";
    const limb=(joint,color,length,leg=false)=>{
      this.ball("upper-limb",joint,[0,-length*.22,0],[leg?.31:.25,length*.55,.3],color);
      const bend=this.pivot("articulated-joint",joint,[0,-length*.48,0]);
      this.ball("lower-limb",bend,[0,-length*.24,0],[leg?.29:.23,length*.56,.28],color);
      if(leg){const foot=this.ball("rounded-shoe",bend,[0,-length*.49,-.17],[.5,.3,.78],color);feet.push(foot);knees.push(bend);}
      else this.glove(bend,[0,-length*.5,0],id==="jax"?"#ffe473":skin,.3);
      return bend;
    };
    if(id==="pomni") {
      this.ball("jester-bodice",body,[0,2.14,0],[1.08,1.32,.78],blue);
      this.ball("red-bodice-half",body,[-.25,2.15,-.12],[.62,1.2,.64],red);
      for(let i=0;i<8;i++){const a=i*Math.PI/4;this.ball("ruff",body,[Math.cos(a)*.45,2.83,Math.sin(a)*.36],[.37,.18,.35],skin);}
      for(let i=0;i<2;i++)this.ball("costume-button",body,[0,2.15-i*.33,-.43],[.16,.16,.1],gold);
      this.ball("face",head,[0,.1,0],[1.32,1.2,1],skin);
      this.ball("brown-bob",head,[0,.3,.22],[1.48,1.23,.96],"#542533");
      [-1,1].forEach(side=>{this.ball("side-hair",head,[side*.59,-.04,-.03],[.32,.77,.45],"#542533");this.ball("blush",head,[side*.47,-.16,-.425],[.17,.08,.05],"#ed9a91");});
      eyes.push(this.eye(head,-.29,.16,-.47,red,1.12),this.eye(head,.29,.16,-.47,blue,1.12));
      for(const side of [-1,1]) {
        const horn=this.mesh("CreateTube","curved-jester-hat",head,{path:[[side*.28,.56,.1],[side*.45,1.09,.13],[side*.78,1.35,.1],[side*1.02,1.1,.04]].map(p=>BABYLON.Vector3.FromArray(p)),radiusFunction:i=>[.34,.29,.19,.035][i],tessellation:24,cap:BABYLON.Mesh.CAP_ALL},[0,0,0],side<0?red:blue);
        ears.push(horn);this.ball("hat-bell",head,[side*1.02,1.07,.04],[.23,.23,.23],gold);
      }
      limb(leftArm,blue,1.18);limb(rightArm,red,1.18);limb(leftLeg,red,1.4,true);limb(rightLeg,blue,1.4,true);
    } else if(id==="ragatha") {
      this.lathe("cloth-dress",body,[0,.65,0],[[.72,0],[.86,.12],[.68,.7],[.43,1.6],[.39,1.98],[0,2.12]],"#6174cb");
      this.ball("apron",body,[0,1.65,-.4],[.76,1.5,.12],"#b9b8ef");
      this.box("dress-patch",body,[.44,1.04,-.54],[.26,.3,.03],"#e3a2b5");
      for(let i=0;i<8;i++)this.ball("hem-stitch",body,[-.56+i*.16,.79,-.51],[.04,.08,.035],skin);
      this.ball("rag-doll-head",head,[0,.05,0],[1.28,1.22,1],skin);
      for(let i=0;i<25;i++){const a=i/24*Math.PI;const x=Math.cos(a)*.66;this.tube("yarn-lock",head,[[x,.48,.12],[x*1.18,.14,.13],[x*1.2,-.42,.18],[x*1.09,-.7,.08]],.055,"#c84637");}
      for(let i=0;i<9;i++)this.tube("yarn-fringe",head,[[-.58+i*.14,.47,-.2],[-.43+i*.1,.62,-.46],[-.38+i*.1,.27,-.48]],.053,"#c84637");
      eyes.push(this.eye(head,.29,.12,-.48,blue,.83));
      const button=this.mesh("CreateCylinder","button-eye",head,{diameter:.4,height:.09,tessellation:32},[-.3,.12,-.51],"#312957");button.rotation.x=Math.PI/2;
      for(const dx of [-.07,.07])for(const dy of [-.07,.07])this.ball("button-hole",head,[-.3+dx,.12+dy,-.567],[.048,.048,.023],skin);
      this.tube("stitched-smile",head,[[-.31,-.26,-.43],[0,-.35,-.5],[.32,-.23,-.44]],.021,"#7e4143");
      limb(leftArm,skin,1.15);limb(rightArm,skin,1.15);limb(leftLeg,skin,1.35,true);limb(rightLeg,skin,1.35,true);
      feet.forEach(f=>f.material=this.mat("#4a283e"));
    } else if(id==="jax") {
      head.position.y=4.2;leftArm.position.y=3;rightArm.position.y=3;leftLeg.position.y=1.9;rightLeg.position.y=1.9;
      this.ball("rabbit-body",body,[0,2.8,0],[.96,1.7,.7],purple);
      this.lathe("pink-overalls",body,[0,1.7,0],[[.4,0],[.58,.17],[.47,.8],[.45,1.25],[.38,1.4]],"#da789f");
      for(const side of [-1,1]){this.box("overall-strap",body,[side*.32,3.15,-.3],[.14,.65,.12],"#df86ad");this.ball("overall-button",body,[side*.32,2.94,-.39],[.17,.17,.08],gold);}
      this.ball("rabbit-head",head,[0,0,0],[1.35,1.25,1.0],purple);
      for(const side of [-1,1]) {const ear=this.pivot("rabbit-ear-joint",head,[side*.34,.48,.1]);this.ball("long-ear",ear,[side*.05,.9,0],[.4,2.15,.3],purple);this.ball("ear-inset",ear,[side*.05,1,-.13],[.19,1.5,.06],"#603791");ears.push(ear);}
      eyes.push(this.eye(head,-.3,.12,-.48,"#d59c33",.83),this.eye(head,.3,.12,-.48,"#d59c33",.83));
      this.ball("grin-background",head,[0,-.32,-.44],[.94,.4,.22],"#fff0bd");
      for(let i=0;i<7;i++)this.tube("grin-divider",head,[[-.33+i*.11,-.19,-.548],[-.33+i*.11,-.42,-.537]],.009,"#78584b");
      limb(leftArm,purple,1.7);limb(rightArm,purple,1.7);limb(leftLeg,"#da789f",1.78,true);limb(rightLeg,"#da789f",1.78,true);
    } else if(id==="gangle") {
      head.position.y=3.45;
      const points=[];for(let i=0;i<=65;i++){const t=i/65;points.push([Math.sin(t*Math.PI*6)*.52,1.1+t*1.7,Math.cos(t*Math.PI*6)*.23]);}
      this.tube("spiral-ribbon-body",body,points,.065,"#cf263b");
      this.ball("porcelain-mask",head,[0,0,0],[1.22,1.3,.31],"#fff4df");
      eyes.push(this.eye(head,-.27,.15,-.2,ink,.67),this.eye(head,.27,.15,-.2,ink,.67));
      for(const joint of [leftArm,rightArm]) {this.tube("ribbon-arm",joint,[[0,0,0],[.13,-.4,0],[-.16,-.8,0],[0,-1.2,0]],.055,red);this.tube("ribbon-finger",joint,[[0,-1.2,0],[.22,-1.28,0],[.28,-1.12,0]],.043,red);}
      for(const joint of [leftLeg,rightLeg])this.tube("ribbon-leg",joint,[[0,0,0],[.12,-.55,0],[-.05,-1.2,0],[.22,-1.45,-.18]],.065,red);
    } else if(id==="kinger") {
      head.position.y=3.05;
      this.lathe("chess-king",body,[0,.12,0],[[.85,0],[.92,.15],[.78,.34],[.52,.49],[.47,1.55],[.7,1.72],[.55,1.92],[.36,2.4],[.5,2.65],[.57,2.9]],"#e8c991");
      this.lathe("royal-robe",body,[0,.3,.16],[[.92,0],[.95,.25],[.76,1.2],[.56,2.15]],"#63337c");
      for(let i=0;i<18;i++){const a=i/18*Math.PI*2;this.ball("fur-hem",body,[Math.cos(a)*.9,.44,Math.sin(a)*.9+.16],[.28,.28,.24],skin);}
      this.ball("king-head",head,[0,.1,0],[1.16,1.4,.92],"#edd4a5");
      this.lathe("chess-crown",head,[0,.56,0],[[.6,0],[.64,.17],[.42,.27],[.38,.55]],"#edcd92");
      this.box("king-cross-vertical",head,[0,1.4,0],[.21,.8,.22],"#edd4a5");this.box("king-cross-horizontal",head,[0,1.44,0],[.65,.21,.22],"#edd4a5");
      eyes.push(this.eye(head,-.31,.08,-.42,"#15131b",1),this.eye(head,.31,.08,-.42,"#15131b",1));
      this.glove(leftArm,[-.18,-.65,0],skin,.45);this.glove(rightArm,[.18,-.65,0],skin,.45);
    } else {
      head.position.y=3.45;
      this.mesh("CreatePolyhedron","asymmetric-torso",body,{type:2,size:.72},[0,2.15,0],"#f4c83d");
      this.mesh("CreateCylinder","triangle-head",head,{diameter:1.46,height:.3,tessellation:3},[0,0,0],"#ef6796").rotation.x=Math.PI/2;
      eyes.push(this.eye(head,-.29,.12,-.23,"#2e234a",1),this.eye(head,.3,.14,-.23,"#2e234a",.65));
      this.tube("curved-antenna",head,[[.35,.45,0],[.5,.9,0],[.84,.84,0],[.78,.6,0]],.09,"#6ad1bb");
      this.mesh("CreateCylinder","head-spike",head,{diameterTop:0,diameterBottom:.37,height:.95,tessellation:24},[-.38,.74,0],"#987ac6").rotation.z=-.35;
      limb(leftArm,"#59b69b",1.24);this.tube("coiled-arm",rightArm,Array.from({length:45},(_,i)=>[Math.sin(i*.55)*.13,-i*.026,Math.cos(i*.55)*.13]),.065,"#e95d3d");this.glove(rightArm,[0,-1.2,0],"#efc333",.35);
      limb(leftLeg,"#4478bd",1.4,true);limb(rightLeg,"#dd473a",1.4,true);
    }
    const mouth=this.pivot("expression-mouth",head,[0,-.31,id==="gangle"?-.2:-.51]);
    if(id!=="jax"&&id!=="ragatha")this.ball("mouth",mouth,[0,0,0],[.25,.075,.04],ink);
    for(const side of [-1,1])brows.push(this.tube("eyebrow",head,[[side*.15,.48,-.43],[side*.3,.51,-.48],[side*.44,.46,-.4]],.018,ink));
    const location=worldView.locations.get(character.location_id),offset=new BABYLON.Vector3(Math.cos(index*2.4)*3.4,0,Math.sin(index*2.4)*3.4);
    if(character.spatial?.position)offset.set(character.spatial.position.x,0,character.spatial.position.z);
    const at=(location?.root.position||BABYLON.Vector3.Zero()).add(offset);
    const group=location?.location.adventure_id||"hub",safe=worldView.navigation.nearest(at,group);
    root.position=new BABYLON.Vector3(safe?.x??at.x,0,safe?.z??at.z);root.rotation.y=Math.PI;
    worldView.characters.set(id,{root,body,head,leftArm,rightArm,leftLeg,rightLeg,knees,feet,ears,eyes,brows,mouth,heads:[head],
      color:CHARACTER_COLORS[id],locationId:character.location_id,offset,movement:null,expression:"curiosity",stepPhase:index,
      movingUntil:0,talkingUntil:0,gestureUntil:0,gesture:"",idleUntil:performance.now()+2500+index*700,portalToken:0,
      height:id==="jax"?6.8:5,group,speed:id==="kinger"?2.7:id==="jax"?4.8:3.7,
      activity:character.spatial?.activity||"observing",activityPhase:character.spatial?.phase||"idle",activityPlan:character.spatial?.plan||[]});
  },
  animate(view,now,dt,speed) {
    const blend=1-Math.exp(-dt*9),walk=Math.min(1,speed/3),phase=view.stepPhase;
    const talk=now<view.talkingUntil||view.activity==="talk"||view.activity==="lie",gesture=now<view.gestureUntil?view.gesture:view.activity;
    const ease=(obj,key,value)=>obj[key]+=(value-obj[key])*blend;
    const stride=Math.sin(phase)*.48*walk;
    ease(view.leftLeg.rotation,"x",stride);ease(view.rightLeg.rotation,"x",-stride);
    view.knees.forEach((k,i)=>ease(k.rotation,"x",Math.max(0,Math.sin(phase+i*Math.PI))*.65*walk));
    ease(view.leftArm.rotation,"x",-stride*.72);ease(view.rightArm.rotation,"x",stride*.72);
    const reach=["helped","help","item_used","item_picked_up","inspected","inspecting","searched","searching","collecting","using","placing"].includes(gesture);
    ease(view.rightArm.rotation,"x",reach?-.85:talk?-.3:-stride*.72);
    ease(view.rightArm.rotation,"z",talk?-.3+Math.sin(now*.006)*.14:0);
    ease(view.leftArm.rotation,"z",view.expression==="fear"?.28:0);
    ease(view.body.rotation,"z",["slept","sleeping","resting"].includes(gesture)?.18:Math.sin(phase)*.015*walk);
    ease(view.body.rotation,"x",["searched","searching","collecting","item_picked_up"].includes(gesture)?.18:0);
    const eyeTarget=(view.expression==="fear"?1.14:view.expression==="anger"?.65:1)*(now%(3300+view.root.uniqueId*11)<125?.09:1);
    view.eyes.forEach(eye=>ease(eye.scaling,"y",eyeTarget));
    const headTilt=view.expression==="curiosity"?.08:0,browAngle=view.expression==="anger"?.16:0,armPosture=view.expression==="fear"?.2:0;
    ease(view.head.rotation,"z",headTilt+Math.sin(now*.0014+view.root.uniqueId)*.025);
    view.brows.forEach((b,i)=>ease(b.rotation,"z",browAngle*(i?1:-1)));
    ease(view.mouth.scaling,"y",talk?1+Math.abs(Math.sin(now*.016))*3:view.expression==="fear"?2.3:1);
    view.ears.forEach((ear,i)=>{if(ear instanceof BABYLON.TransformNode && !(ear instanceof BABYLON.Mesh))ease(ear.rotation,"z",Math.sin(phase+i)*.065*walk);});
    view.body.position.y=Math.abs(Math.cos(phase))*.035*walk+Math.sin(now*.002+view.root.uniqueId)*.012;
  },
  environment() {
    const root=this.pivot("grand-circus-interior",null),nav=worldView.navigation;
    const red="#ac1533",gold="#ecc04b",cream="#ffecd0",blue="#2734a3";
    // Tall pleated curtains frame a rectangular hall, leaving a real broad opening
    // onto the grounds. Open-front theatrical architecture keeps the camera clear.
    for(const side of [-1,1]) {
      for(let j=0;j<24;j++) {
        const z=-30+j*2.7;
        this.mesh("CreateCylinder","velvet-curtain-fold",root,{diameter:2.8,height:12,tessellation:16},[side*35,6,z],j%2?red:"#df2847");
      }
      nav.addObstacle(side*35,1,1.4,64);
      for(let j=0;j<5;j++) {
        const z=-27+j*13;this.lathe("gilded-column",root,[side*33,0,z],[[.75,0],[.8,.25],[.4,.5],[.32,10.8],[.7,11],[.7,11.5]],gold);
        this.ball("column-finial",root,[side*33,12,z],[.8,.8,.8],cream);
      }
    }
    for(let i=0;i<25;i++)this.mesh("CreateCylinder","back-curtain",root,{diameter:2.9,height:12,tessellation:16},[-33+i*2.7,6,-32],i%2?red:"#d32d46");
    nav.addObstacle(0,-32,68,1.5);
    for(let i=0;i<5;i++) {
      const z=-29+i*14;
      this.tube("arched-roof-rib",root,[[-34,12,z],[-26,20,z],[-13,25,z],[0,27,z],[13,25,z],[26,20,z],[34,12,z]],.12,gold);
    }
    for(const z of [-27,26])for(let i=0;i<46;i++) {
      const x=-32+i*1.42,bulb=this.ball("festoon-bulb",root,[x,10.8-Math.sin(i/45*Math.PI)*1.6,z],[.23,.23,.23],gold);
      bulb.material=this.mat("#ffeaa0",.15,.8);
    }
    this.text("circus-marquee",root,[0,10,-30.3],"THE AMAZING DIGITAL CIRCUS",24,3.4);
    this.lathe("ring-stage",root,[0,.02,-17],[[6,0],[6,.25],[5.95,.45]],red);nav.addObstacle(0,-17,12,12);
    for(let i=0;i<50;i++){const a=i/50*Math.PI*2;this.ball("ring-footlight",root,[Math.cos(a)*6,.6,-17+Math.sin(a)*6],[.16,.16,.16],gold).material=this.mat("#ffd25d",.15,.7);}
    for(const x of [-13,13]) {
      this.mesh("CreateTorus","ring-trim",root,{diameter:12,thickness:.16,tessellation:72},[x,.05,0],gold);
      // Flat inlaid rings are walkable, unlike raised scenery.
      this.mesh("CreateCylinder","ring-inlay",root,{diameter:11.8,height:.035,tessellation:64},[x,.005,0],x<0?"#98333e":"#2e4899");
    }
    for(const x of [-27,27])for(let tier=0;tier<3;tier++) {
      this.box("audience-tier",root,[x,.45+tier*.45,-17+tier*1.5],[8,.85+tier*.9,1.2],blue);
      for(let seat=0;seat<7;seat++)this.ball("velvet-seat",root,[x-3+seat,1+tier*.9,-17+tier*1.5],[.8,.22,.8],red);
    }
    nav.addObstacle(-27,-15.5,8,5);nav.addObstacle(27,-15.5,8,5);
    this.tube("trapeze-left",root,[[-6,21,-3],[-6,12,-3]],.045,cream);this.tube("trapeze-right",root,[[0,21,-3],[0,12,-3]],.045,cream);this.tube("trapeze-bar",root,[[-6,12,-3],[0,12,-3]],.12,gold);
    // Caine has a complete ringmaster body and a tooth-lined jaw.
    const caine=this.pivot("director-caine",null,[0,8.5,-18]),jaw=this.pivot("caine-jaw",caine);
    this.ball("mouth-cavity",jaw,[0,0,0],[2.25,1.5,.65],"#371026");
    this.tube("upper-gum",jaw,[[-1,.1,0],[-.65,.66,0],[0,.78,0],[.65,.66,0],[1,.1,0]],.17,red);
    this.tube("lower-gum",jaw,[[-1,.1,0],[-.7,-.47,0],[0,-.62,0],[.7,-.47,0],[1,.1,0]],.17,red);
    for(let i=0;i<9;i++){const x=-.84+i*.21;this.ball("upper-tooth",jaw,[x,.42-Math.abs(x)*.19,-.21],[.24,.43,.23],cream);this.ball("lower-tooth",jaw,[x,-.37+Math.abs(x)*.15,-.21],[.24,.32,.23],cream);}
    this.eye(caine,-.48,1,-.1,"#39a6cf",1.05);this.eye(caine,.48,1,-.1,"#4da06a",1.05);
    this.lathe("caine-top-hat",caine,[0,1.49,.1],[[1.2,0],[1.2,.16],[.72,.2],[.77,1.48],[0,1.49]],"#26172f");
    this.lathe("hat-ribbon",caine,[0,1.75,.1],[[.78,0],[.78,.26]],red);
    this.lathe("caine-tailcoat",caine,[0,-2.32,.12],[[.55,0],[.72,.15],[.45,.8],[.65,1.12],[.4,1.6]],"#bd1839");
    this.ball("waistcoat",caine,[0,-1.12,-.28],[.57,.88,.1],cream);
    for(const side of [-1,1]){this.ball("bow-tie",caine,[side*.16,-.74,-.4],[.32,.21,.1],inkColor());this.tube("caine-sleeve",caine,[[side*.54,-1.05,.1],[side*.92,-1.44,0],[side*1.22,-.7,-.1]],.16,red);this.glove(caine,[side*1.23,-.64,-.1],cream,.39);this.ball("caine-trouser",caine,[side*.24,-2.75,.12],[.37,1.12,.37],"#312038");this.ball("caine-shoe",caine,[side*.25,-3.3,-.12],[.45,.26,.8],"#211a2b");}
    worldView.caine=caine;
    // Sculpted trees and cloud banks give the grounds depth beyond the tent.
    for(let i=0;i<26;i++) {
      const side=i%2?-1:1,x=side*(43+(i%3)*2),z=20+Math.floor(i/2)*6;
      this.lathe("topiary-trunk",root,[x,0,z],[[.42,0],[.32,2.8]],"#704437");
      this.ball("topiary-crown",root,[x,4,z],[3.5,4.6,3.5],i%3?"#28a572":"#80bf62");nav.addObstacle(x,z,1,1);
    }
    this.batchStatic(root);
  },
  location(location) {
    const root=this.pivot(`location-${location.id}`,null);root.position=pointFor(location.id,location);
    const cream="#fff0c9",gold="#e8b83b",red="#cf2948",blue="#4264b2";
    const id=location.id,group=location.adventure_id||"hub";
    worldView.navigation.addArea(root.position.x,root.position.z,14,group);
    const furniture=(name,p,size,color)=>{this.box(name,root,p,size,color);this.obstacle(root,p[0],p[2],size[0],size[2]);};
    if(id==="bedroom_hall") {
      furniture("hall-back",[0,3.5,5],[18,7,.4],"#dab4d1");
      for(let i=0;i<6;i++) {
        const x=-7.5+i*3;
        this.box("door-frame",root,[x,2.2,4.6],[2.6,4.6,.25],gold);this.box("bedroom-door",root,[x,2.1,4.4],[2.25,4.1,.22],i%2?"#674799":"#bd486a");
        this.ball("door-portrait",root,[x,3,4.23],[.76,.82,.12],["#e53547","#6884d3","#a974ce","#efcdbb","#c9a36c","#f8d34a"][i]);
        this.ball("brass-door-knob",root,[x+.75,1.9,4.15],[.18,.18,.18],gold);
        this.text("bedroom-name",root,[x,1.1,4.22],["POMNI","RAGATHA","JAX","GANGLE","KINGER","ZOOBLE"][i],1.8,.45);
      }
      this.text("hall-sign",root,[0,6,4.6],"HOME SWEET HOME",10,1.1);
    } else if(id==="dining_hall") {
      furniture("banquet-table",[0,1.8,1],[12,.32,3.2],"#793941");
      for(let i=-5;i<=5;i+=2)for(const side of [-1,1]) {
        furniture("chair-seat",[i,.85,side*2.8+1],[1,.25,1],blue);
        this.box("chair-back",root,[i,1.6,side*3.25+1],[1,1.55,.18],blue);
        this.mesh("CreateCylinder","gold-plate",root,{diameter:.8,height:.04,tessellation:32},[i,2.01,side*.93+1],gold);
        this.lathe("teacup",root,[i+.35,2.01,side*.8+1],[[.1,0],[.17,.25],[.2,.28]],cream);
      }
      this.lathe("tiered-cake",root,[0,1.97,1],[[1,0],[1,.7],[.72,.72],[.72,1.3],[.42,1.32],[.42,1.8]],"#e681ae");
      for(let i=0;i<12;i++){const a=i/12*Math.PI*2;this.ball("cake-icing",root,[Math.cos(a)*.95,2.66,1+Math.sin(a)*.95],[.28,.16,.28],cream);}
      this.text("dining-sign",root,[0,5,4],"A TASTE OF NOTHING",10,1.1);
    } else if(id==="backstage") {
      for(let i=0;i<6;i++){const x=-8+i*3; furniture("striped-prop-trunk",[x,1.1,4+(i%2)],[2.3,2.2,2],i%2?red:blue);this.box("trunk-band",root,[x,1.1,2.97+(i%2)],[.25,2.22,.04],gold);}
      this.tube("ladder-rail",root,[[6,0,0],[6,6,3]],.12,gold);this.tube("ladder-rail",root,[[7.5,0,0],[7.5,6,3]],.12,gold);
      for(let i=0;i<9;i++)this.tube("ladder-rung",root,[[6,.4+i*.6,.2+i*.3],[7.5,.4+i*.6,.2+i*.3]],.08,gold);
      this.text("backstage-sign",root,[0,5.4,5],"BACKSTAGE • MIND THE PROPS",13,1.2);
    } else if(id==="main_tent") {
      // Keep the center open for unconstrained local movement and conversations.
      for(const x of [-7,7]){this.lathe("balloon-weight",root,[x,0,5],[[.3,0],[.3,.22]],gold);for(let i=0;i<3;i++){this.tube("balloon-string",root,[[x,.2,5],[x+(i-1)*.6,3.7+i*.3,5]],.009,cream);this.ball("balloon",root,[x+(i-1)*.6,4.1+i*.3,5],[.75,1,.75],[red,blue,gold][i]);}}
    } else if(id==="center_stage") {
      this.text("stage-plaque",root,[0,1,-6.1],"CAINE PRESENTS",6,.7);
    } else if(id==="circus_grounds") {
      furniture("fountain-basin",[0,.55,0],[5,1.1,5],"#77c8d0");
      this.lathe("fountain",root,[0,1.1,0],[[1.8,0],[1.8,.18],[.3,.3],[.25,2],[1.1,2.2],[1.1,2.4]],gold);
      this.ball("water-orb",root,[0,4,0],[1.5,1.5,1.5],"#7adeee");
      this.text("grounds-sign",root,[0,7,4],"THE GROUNDS",12,1.4);
    } else if(id==="rides_promenade"||id==="moon_carnival") {
      this.tube("wheel-support",root,[[-4,0,5],[0,9,5],[4,0,5]],.32,cream);
      const wheel=this.pivot("ferris-wheel",root,[0,9,5]);
      wheel.metadata={dynamic:true};worldView.animatedProps.push({node:wheel,kind:"wheel"});
      this.mesh("CreateTorus","wheel-rim",wheel,{diameter:14,thickness:.22,tessellation:72},[0,0,0],gold).rotation.x=Math.PI/2;
      for(let i=0;i<12;i++){const a=i/12*Math.PI*2;this.tube("wheel-spoke",wheel,[[0,0,0],[Math.cos(a)*7,Math.sin(a)*7,0]],.07,cream);this.ball("gondola",wheel,[Math.cos(a)*7,Math.sin(a)*7,-.1],[1.15,1.3,1.1],i%2?red:blue);}
      this.obstacle(root,0,5,10,4);
      for(const x of [-9,9]){furniture("ticket-booth",[x,1.5,0],[3,3,3],blue);this.lathe("booth-roof",root,[x,3,0],[[2,0],[0,1.8]],red);}
    } else if(id==="digital_lake") {
      const lake=this.mesh("CreateCylinder","lake",root,{diameter:24,height:.08,tessellation:72},[0,0,3],"#349ecc");lake.scaling.z=.7;this.obstacle(root,0,3,22,14);
      for(let i=0;i<4;i++){const boat=this.ball("toy-boat",root,[-5+i*3,.4,3+Math.sin(i)*3],[2.1,.65,1],i%2?red:gold);}
      this.box("dock",root,[-11,.3,-4],[3,.35,6],"#b78358");
    } else if(id==="grand_theater") {
      furniture("theater-back",[0,5,5],[17,10,1],"#3b2461");
      for(const x of [-7,7]){furniture("theater-wing",[x,3.5,1],[3,7,5],red);this.lathe("theater-column",root,[x,0,-2],[[.6,0],[.35,.4],[.35,7],[.65,7.2]],gold);}
      this.text("theater-sign",root,[0,8,4.2],"THE GRAND THEATER",14,1.6);
    } else if(id==="portal_gallery"||id==="adventure_portal"||id==="mirror_maze") {
      const count=id==="portal_gallery"?5:1;
      for(let i=0;i<count;i++){const x=(i-(count-1)/2)*4.6;for(let j=0;j<3;j++){const ring=this.mesh("CreateTorus","portal-frame",root,{diameter:4.4-j*.32,thickness:.18,tessellation:64},[x,3.1,3],j%2?gold:"#885fe3");ring.rotation.x=Math.PI/2;ring.metadata={dynamic:true};worldView.portalRings.push(ring);}this.ball("portal-surface",root,[x,3.1,3.1],[3.6,4.4,.1],"#342061");this.obstacle(root,x,3,4,.3);}
      this.text("portal-title",root,[0,6,3],id==="mirror_maze"?"THE MIRROR MAZE":"WHERE SHALL WE GO TODAY?",15,1.2);
    } else if(id==="void_overlook") {
      for(let i=0;i<10;i++){this.lathe("fence-post",root,[-9+i*2,0,5],[[.12,0],[.12,1.7],[.2,1.8]],cream);}
      this.tube("overlook-rail",root,[[-10,1.5,5],[10,1.5,5]],.08,gold);this.obstacle(root,0,5,20,.2);
    } else if(location.world_theme||id==="candy_kingdom") {
      const theme=location.world_theme||"candy_kingdom";
      const palette={glitch_midway:["#b93651",gold,blue],moon_funfair:["#322665","#8fcada","#c3c1ed"],candy_kingdom:["#ce7b9b",cream,"#a1dba7"],clockwork_sky:["#587b9b",gold,"#b5dddd"],storybook_sea:["#266da2",cream,red],neon_city:["#251944","#ea3cb0","#41c9d4"]}[theme];
      this.mesh("CreateCylinder","pocket-island",root,{diameter:28,height:.6,tessellation:64},[0,-.31,0],palette[0]);
      this.lathe("island-underside",root,[0,-5,0],[[0,0],[7,2],[14,4.6]],palette[0]);
      for(let i=0;i<7;i++) {
        const a=i/7*Math.PI*2,x=Math.cos(a)*9,z=Math.sin(a)*9;
        if(theme==="candy_kingdom") {this.lathe("candy-tower",root,[x,0,z],[[1,0],[1,4],[1.4,4.1],[0,6]],palette[1]);for(let j=0;j<5;j++)this.mesh("CreateTorus","candy-stripe",root,{diameter:2.05,thickness:.12,tessellation:32},[x,.6+j*.7,z],red);}
        else if(theme==="neon_city") {const height=4+i%3*2;this.box("neon-tower",root,[x,height/2,z],[2,height,2],palette[0]);for(let j=0;j<5;j++)this.box("neon-window",root,[x,.7+j*1.05,z-1.03],[1.7,.22,.035],palette[i%2+1]).material=this.mat(palette[i%2+1],.15,.6);}
        else if(theme==="clockwork_sky") {this.lathe("brass-machine",root,[x,0,z],[[1,0],[1,2],[.5,2.2],[.5,3.5]],palette[1]);this.mesh("CreateTorus","machine-gear",root,{diameter:2.4,thickness:.25,tessellation:12},[x,3,z],palette[2]).rotation.x=Math.PI/2;}
        else if(theme==="storybook_sea") {this.box("storybook-stack",root,[x,1,z],[2,2,2.8],i%2?palette[1]:palette[2]);this.lathe("paper-sail",root,[x,2,z],[[1.5,0],[0,3]],cream);}
        else {this.box("carnival-booth",root,[x,1.5,z],[2.4,3,2.4],palette[1]);this.lathe("striped-roof",root,[x,3,z],[[1.8,0],[0,1.8]],palette[2]);}
        this.obstacle(root,x,z,2.7,2.7);
      }
      this.text("world-title",root,[0,6,6],location.name.toUpperCase(),16,1.4,palette[1],palette[0]);
      if(location.zone_index===2){this.mesh("CreateTorus","quest-core",root,{diameter:4,thickness:.35,tessellation:48},[0,3,3],palette[1]).rotation.x=Math.PI/2;this.obstacle(root,0,3,4,1);}
    }
    const label=node("div","location-label",location.name);ui.labels.appendChild(label);
    worldView.locations.set(id,{root,label,location,anchor:new BABYLON.Vector3(0,7,0)});
    this.batchStatic(root);
  },
};
function inkColor(){return "#24162b";}
