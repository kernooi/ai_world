"use strict";

// Story mechanisms are driven by the authoritative adventure snapshot. Visual
// animation never marks objectives complete or invents successful interactions.
const StoryPresentation = {
  worlds:new Map(), current:null, shotKey:null,
  build(adventure) {
    const locations=adventure.generated_location_ids.map(id=>worldView.locations.get(id));
    if(locations.some(l=>!l))return null;
    const art=CircusArt,props={cages:[],workers:[],rollers:[],vents:[],steam:[],targets:[]};
    const [dock,line,furnace]=locations.map(l=>l.root);
    const npc=(name,parent,x,z,color)=>{
      const root=art.pivot(name,parent,[x,0,z]);
      art.ball('sugar-body',root,[0,1,0],[.85,1.5,.75],color);
      art.ball('sugar-head',root,[0,2,0],[1.2,1.1,1],color);
      art.eye(root,-.23,2,-.48,'#302441',.65);art.eye(root,.23,2,-.48,'#302441',.65);
      for(const side of [-1,1]){art.ball('sugar-shoe',root,[side*.23,.2,-.15],[.32,.25,.5],'#442847');}
      art.text('npc-name',root,[0,3,0],name,3,.5);return root;
    };
    props.pip=npc('PIP',dock,-5,-6,'#7fcba4');
    props.foreman=npc('FOREMAN FUDGE',line,5,-6,'#ad684d');
    for(let i=0;i<3;i++){
      const x=-7+i*7,z=3,prison=art.pivot('worker-cage',dock,[x,0,z]);
      art.box('cage-base',prison,[0,.15,0],[3,.3,3],'#8f4660');
      const bars=art.pivot('lifting-cage',prison);
      for(const side of [-1,1])for(let j=0;j<5;j++){
        art.box('candy-bar',bars,[-1.4+j*.7,1.7,side*1.4],[.13,3.2,.13],'#fff0b4');
        art.box('candy-bar',bars,[side*1.4,1.7,-1.4+j*.7],[.13,3.2,.13],'#e15a77');
      }
      props.cages.push(bars);props.workers.push(npc(`WORKER ${i+1}`,prison,0,0,'#e6b576'));
    }
    props.truck=art.pivot('escape-delivery-truck',dock,[7,0,-5]);
    art.box('truck-cab',props.truck,[0,1.7,0],[2.5,2.7,2.5],'#5caeae');
    art.box('truck-bed',props.truck,[0,.8,3],[3,.5,4],'#a6d3b5');
    art.box('windshield',props.truck,[0,2,-1.27],[1.9,1,.08],'#93dcdf');
    for(const x of [-1.3,1.3])for(const z of [0,4])art.ball('truck-wheel',props.truck,[x,.6,z],[.5,1.1,1.1],'#322534');
    props.gate=art.pivot('escape-gate',dock,[0,0,-9]);
    art.box('escape-gate-panel',props.gate,[0,2,0],[6,3.8,.3],'#ca5a76');
    art.text('escape-sign',dock,[0,5,-9],'DELIVERY EXIT',7,1);
    art.box('caramel-vat',line,[0,.3,2],[13,.7,9],'#783854');
    props.caramel=art.box('boiling-caramel',line,[0,.74,2],[12.5,.1,8.5],'#d68036');
    art.box('conveyor-frame',line,[0,1.2,0],[3,.35,15],'#55616f');
    for(let i=0;i<15;i++){
      const roller=art.mesh('CreateCylinder','conveyor-roller',line,{diameter:.45,height:2.8,tessellation:16},[0,1.5,-6.5+i],'#ccd2c2');
      roller.rotation.z=Math.PI/2;props.rollers.push(roller);
    }
    for(let i=0;i<7;i++){
      const parcel=art.box('delivery-parcel',line,[0,2,-6+i*2],[1.5,.7,1],'#eda7bb');
      props.targets.push({mesh:parcel,offset:i*2});
    }
    for(const side of [-1,1]){
      art.box('factory-column',furnace,[side*6,4,4],[1,8,1],'#9b5574');
      art.tube('sugar-pipe',furnace,[[side*6,7,4],[side*6,8,0],[side*3,8,0],[side*3,4,0]],.3,'#dbb287');
    }
    props.furnace=art.lathe('royal-furnace',furnace,[0,0,3],[[3.8,0],[4,1],[3.5,6],[2.5,7],[2.5,9]],'#743948');
    props.core=art.ball('furnace-fire',furnace,[0,3,-.55],[4,4,.2],'#ff7d36');
    props.core.material=art.mat('#ff7033',.4,.7);
    for(let i=0;i<3;i++){
      const valve=art.mesh('CreateTorus','emergency-valve',furnace,{diameter:1.2,thickness:.17,tessellation:24},[-5+i*5,1.7,-4],'#63cbbb');
      valve.rotation.x=Math.PI/2;props.vents.push(valve);
      const steam=art.ball('vent-steam',furnace,[-5+i*5,3,-4],[.6,1.8,.6],'#ffe9d1');props.steam.push(steam);
    }
    const marker=art.pivot('active-story-interaction',null);
    art.mesh('CreateTorus','interaction-halo',marker,{diameter:2.4,thickness:.1,tessellation:32},[0,.2,0],'#78ffda');
    props.marker=marker;props.locations=locations;props.adventure=adventure;
    return props;
  },
  sync(state) {
    const adventure=state.adventures?.find(a=>a.world_theme==='candy_factory'&&a.status==='active')
      || state.adventures?.filter(a=>a.world_theme==='candy_factory').at(-1);
    if(!adventure)return;
    let props=this.worlds.get(adventure.id);
    if(!props){props=this.build(adventure);if(!props)return;this.worlds.set(adventure.id,props);}
    props.adventure=adventure;this.current=props;
    const story=adventure.story;if(!story?.title)return;
    const room=worldView.locations.get(story.location_id);
    const target=story.targets?.[0];
    props.marker.setEnabled(!story.done);
    if(room&&target)props.marker.position.set(room.root.position.x+target.x,0,room.root.position.z+target.z);
    const key=`${adventure.id}:${story.scene}`;
    if(this.shotKey!==key&&cameraDirector.enabled&&performance.now()>cameraDirector.manualUntil){
      this.shotKey=key;frameLocation(story.location_id,'medium');
    }
    const panel=document.getElementById('story-scene');
    if(panel){
      panel.hidden=false;panel.replaceChildren();
      panel.append(node('small','',`SCENE ${Math.min(5,story.scene+1)} / 5 · ${story.title}`));
      panel.append(node('h3','',story.done?(story.failed?'Emergency evacuation':'The escape'):story.objective));
      panel.append(node('p','',story.done?adventure.outcome:`${story.speaker}: “${story.dialogue}”`));
      const progress=node('progress','');progress.max=story.required;progress.value=story.progress;panel.append(progress);
      panel.append(node('small','',story.done?`${story.rescued} workers rescued`:
        `${story.progress}/${story.required} members have acted · ${story.remaining_ticks??'—'} ticks remaining`));
      if(story.branch)panel.append(node('small','',`Choice made: ${story.branch==='rescue'?'Save the worker':'Take the shortcut'}`));
    }
  },
  animate(now,dt) {
    const p=this.current;if(!p)return;const s=p.adventure.story;if(!s?.title)return;
    const blend=1-Math.exp(-dt*3),phase=s.scene;
    p.cages.forEach((c,i)=>{const free=i<(s.rescued||0);c.position.y+=((free?4:0)-c.position.y)*blend;});
    const running=phase>1||(phase===1&&s.progress>0);
    if(running&&!worldView.paused){p.rollers.forEach(r=>r.rotation.y+=dt*3);p.targets.forEach(t=>t.mesh.position.z=((now*.0018+t.offset)%14)-7);}
    const emergency=phase>=3&&!s.done;
    p.core.scaling.setAll(emergency?1+Math.sin(now*.012)*.07:.85);
    p.steam.forEach((steam,i)=>{steam.setEnabled(phase>=3);steam.scaling.y=1+Math.sin(now*.003+i)*.3;});
    p.vents.forEach((v,i)=>{if(phase>3||phase===3&&i<s.progress)v.rotation.z+=dt;});
    p.gate.position.y+=(((phase===4?s.progress/3:phase>=5&&!s.failed?1:0)*4)-p.gate.position.y)*blend;
    if(s.done&&!s.failed)p.truck.position.z+=( -13-p.truck.position.z)*dt*.25;
  }
};
