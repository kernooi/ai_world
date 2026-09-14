"use strict";

// Sculpted asset loading is independent of the actor's authoritative movement
// root. A failed download leaves the working procedural character in place.
const ImportedCharacters = {
  async loadCaine() {
    const view=worldView.caine;
    if(!view)return;
    let container,holder;
    const fallbackMeshes=view.getChildMeshes().slice();
    try {
      container=await BABYLON.SceneLoader.LoadAssetContainerAsync('/assets/','caine.glb',worldView.scene);
      if(worldView.caine!==view||view.isDisposed()){container.dispose();return;}
      holder=new BABYLON.TransformNode('caine-sculpted-model',worldView.scene);
      for(const root of container.rootNodes)root.parent=holder;
      container.addAllToScene();
      for(const mesh of container.meshes)mesh.computeWorldMatrix(true);
      const bounds=holder.getHierarchyBoundingVectors(true),height=bounds.max.y-bounds.min.y;
      if(!Number.isFinite(height)||height<=0)throw new Error('Caine model has invalid bounds');
      const scale=7.25/height;
      // Match the imported Blender model to the cast's local -Z forward axis.
      holder.scaling.setAll(scale);holder.rotation.y=Math.PI;
      holder.position.set(-(bounds.max.x+bounds.min.x)*.5*scale,-(bounds.max.y+bounds.min.y)*.5*scale,
        -(bounds.max.z+bounds.min.z)*.5*scale);
      holder.parent=view;
      const clips=new Map();
      for(const group of container.animationGroups){
        const name=['Idle','Fly','Talk','CheckUp'].find(key=>group.name.endsWith(key));
        if(name){clips.set(name,group);group.start(true);group.setWeightForAllAnimatables(name==='Idle'?1:0);}
        else group.stop();
      }
      if(!clips.has('Idle')||!clips.has('Fly')||!clips.has('CheckUp'))throw new Error('Caine animation clips are missing');
      for(const mesh of container.meshes){
        mesh.receiveShadows=true;
        if(mesh.getTotalVertices()>0)worldView.shadow?.addShadowCaster(mesh);
      }
      fallbackMeshes.forEach(mesh=>mesh.setEnabled(false));
      worldView.caineModel={container,holder,clips,weights:{Idle:1,Fly:0,Talk:0,CheckUp:0}};
    }catch(error){
      container?.dispose();holder?.dispose();
      console.warn('Sculpted Caine could not load; procedural model retained.',error);
      showNotice('Caine\u2019s detailed model could not load. Refresh to retry.');
    }
  },
  animateCaine(now,dt,moving,checking,talking) {
    const model=worldView.caineModel;if(!model)return;
    const active=moving?'Fly':talking?'Talk':checking?'CheckUp':'Idle';
    const blend=1-Math.exp(-dt*7);
    for(const [name,clip] of model.clips){
      model.weights[name]+=((name===active?1:0)-model.weights[name])*blend;
      clip.setWeightForAllAnimatables(model.weights[name]);
      clip.speedRatio=worldView.paused?0:name==='Fly'?1.15:1;
    }
  },
  async loadPomni(view) {
    let container,holder;
    try {
      container = await BABYLON.SceneLoader.LoadAssetContainerAsync('/assets/', 'pomni.glb', worldView.scene);
      if (worldView.characters.get('pomni') !== view || view.root.isDisposed()) {
        container.dispose(); return;
      }
      holder = new BABYLON.TransformNode('pomni-sculpted-model', worldView.scene);
      for (const root of container.rootNodes) root.parent = holder;
      container.addAllToScene();
      for (const mesh of container.meshes) mesh.computeWorldMatrix(true);
      const bounds = holder.getHierarchyBoundingVectors(true);
      const height = bounds.max.y - bounds.min.y;
      if (!Number.isFinite(height) || height <= 0) throw new Error('Pomni model has invalid bounds');
      const scale = 4.8 / height;
      holder.scaling.setAll(scale);
      holder.rotation.y=Math.PI;
      holder.position.set(-(bounds.max.x+bounds.min.x)*.5*scale, -bounds.min.y*scale, -(bounds.max.z+bounds.min.z)*.5*scale);
      holder.parent = view.root;
      const clips = new Map();
      for (const group of container.animationGroups) {
        const name = ['Idle','Walk','Talk','Reach'].find(key=>group.name.endsWith(key));
        if(name){clips.set(name,group);group.start(true);group.setWeightForAllAnimatables(name==='Idle'?1:0);}
        else group.stop();
      }
      if(!clips.has('Idle') || !clips.has('Walk')) throw new Error('Pomni animation clips are missing');
      for(const mesh of container.meshes){
        mesh.receiveShadows=true;
        if(mesh.getTotalVertices()>0) worldView.shadow?.addShadowCaster(mesh);
        if(mesh.material instanceof BABYLON.PBRMaterial){
          mesh.material.environmentIntensity=.6;
          mesh.material.directIntensity=1.1;
        }
      }
      const morphs = new Map();
      for(const mesh of container.meshes){
        const manager=mesh.morphTargetManager;if(!manager)continue;
        for(let i=0;i<manager.numTargets;i++){
          const target=manager.getTarget(i);
          if(!morphs.has(target.name))morphs.set(target.name,[]);
          morphs.get(target.name).push(target);
        }
      }
      const eyelids=container.transformNodes.filter(node=>/^Eyelid_(Top|Bk)\.[LR]$/.test(node.name))
        .map(node=>({node,rest:node.rotationQuaternion.clone(),angle:node.name.includes('Top')?.95:-.7}));
      view.body.setEnabled(false);
      view.importedModel={container,holder,clips,morphs,eyelids,weights:{Idle:1,Walk:0,Talk:0,Reach:0}};
      view.height=4.8;
    } catch(error) {
      container?.dispose();
      holder?.dispose();
      console.warn('Sculpted Pomni could not load; procedural model retained.',error);
      showNotice('Pomni’s detailed model could not load. Refresh to retry.');
    }
  },
  animate(view,now,dt,speed) {
    const model=view.importedModel,blend=1-Math.exp(-dt*8);
    const moving=speed>.2;
    const speaking=now<view.talkingUntil || (!moving && ['talk','lie'].includes(view.activity));
    const reaching=!moving && (now<view.gestureUntil && ['helped','item_used','item_picked_up','inspected'].includes(view.gesture)
      || view.activityPhase==='acting' && ['help','using','collecting','inspecting','searching'].includes(view.activity));
    const active=moving?'Walk':speaking?'Talk':reaching?'Reach':'Idle';
    for(const [name,clip] of model.clips){
      model.weights[name]+=((name===active?1:0)-model.weights[name])*blend;
      clip.setWeightForAllAnimatables(model.weights[name]);
      clip.speedRatio=worldView.paused?0:name==='Walk'?Math.max(.35,Math.min(1.8,speed/3.7)):1;
    }
    const setMorph=(name,value)=>{
      for(const target of model.morphs.get(name)||[])target.influence+=(value-target.influence)*blend;
    };
    setMorph('Ah',speaking?.08+Math.abs(Math.sin(now*.013))*.32:0);
    setMorph('Oh',speaking?Math.max(0,Math.sin(now*.009))*.18:0);
    const blinkPhase=now%4700,blink=blinkPhase<190?Math.sin(blinkPhase/190*Math.PI):0;
    for(const lid of model.eyelids){
      lid.node.rotationQuaternion=lid.rest.multiply(BABYLON.Quaternion.RotationAxis(BABYLON.Axis.X,lid.angle*blink));
    }
    for(const side of ['L','R']){
      setMorph(`Smile.${side}`,view.expression==='happiness'?.2:0);
      setMorph(`Sad.${side}`,view.expression==='fear'?.15:0);
      setMorph(`Stare.${side}`,view.expression==='fear'?.15:0);
    }
  }
};
