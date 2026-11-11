import * as THREE from 'three';

const W = 1280, H = 720, FPS = 30, DURATION = 10, FRAMES = 300;
const SHOT_NAMES = [
  '01 Alpine Lake', '02 Neon Rain Alley', '03 Sahara Dunes',
  '04 Iceland Aurora', '05 Rainforest Temple',
];
window.spec = {width: W, height: H, fps: FPS, duration: DURATION, frames: FRAMES, shots: 5};
window.shotNames = SHOT_NAMES;

const renderer = new THREE.WebGLRenderer({antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance'});
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.autoClear = false;
renderer.setClearColor(0x000000, 1);
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(42, W / H, 0.1, 200);
camera.position.set(0, 0, 10);
camera.lookAt(0, 0, -20);

const overlayScene = new THREE.Scene();
const overlayCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
const overlayMat = new THREE.ShaderMaterial({
  uniforms: {uTime: {value: 0}, uVignette: {value: .26}, uGrain: {value: .014}},
  vertexShader: `varying vec2 vUv; void main(){vUv=uv; gl_Position=vec4(position.xy,0.0,1.0);}`,
  fragmentShader: `
    uniform float uTime,uVignette,uGrain; varying vec2 vUv;
    float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
    void main(){
      vec2 p=vUv-0.5; float d=length(p)*1.35;
      float vig=smoothstep(0.55,1.0,d)*uVignette;
      float g=hash(vUv*vec2(1920.0,1080.0)+uTime*17.0)*uGrain;
      gl_FragColor=vec4(vec3(0.0),clamp(vig+g,0.0,0.45));
    }`,
  transparent: true, depthTest: false, depthWrite: false, toneMapped: false,
});
overlayScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), overlayMat));

function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
const rnd = mulberry32(20261111);
const rand = (a,b)=>a+(b-a)*rnd();
const wrap = (v,a,b)=>((v-a)%(b-a)+(b-a))%(b-a)+a;
const ease = t=>t*t*(3-2*t);

function softSprite(){
  const c=document.createElement('canvas'); c.width=c.height=64;
  const x=c.getContext('2d');
  const g=x.createRadialGradient(32,32,0,32,32,32);
  g.addColorStop(0,'rgba(255,255,255,1)');
  g.addColorStop(.28,'rgba(255,255,255,.72)');
  g.addColorStop(.65,'rgba(255,255,255,.18)');
  g.addColorStop(1,'rgba(255,255,255,0)');
  x.fillStyle=g; x.fillRect(0,0,64,64);
  const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; return t;
}
const SOFT = softSprite();

function makeGlow(color, scale, opacity, pos){
  const m=new THREE.SpriteMaterial({map:SOFT,color,transparent:true,opacity,blending:THREE.AdditiveBlending,depthWrite:false,depthTest:false,toneMapped:false});
  const s=new THREE.Sprite(m); s.scale.set(scale,scale,1); s.position.copy(pos); s.renderOrder=8; return s;
}

function makeShadeSprite(color,scale,opacity,pos){
  const m=new THREE.SpriteMaterial({map:SOFT,color,transparent:true,opacity,blending:THREE.NormalBlending,depthWrite:false,depthTest:false,toneMapped:false});
  const s=new THREE.Sprite(m);s.scale.set(scale,scale,1);s.position.copy(pos);s.renderOrder=3;return s;
}

function makeParticles({count,color,size,opacity,box,mode='mist',speed=1}){
  const arr=new Float32Array(count*3), base=new Float32Array(count*3), phase=new Float32Array(count);
  for(let i=0;i<count;i++){
    const x=rand(box.x[0],box.x[1]), y=rand(box.y[0],box.y[1]), z=rand(box.z[0],box.z[1]);
    base[i*3]=x;base[i*3+1]=y;base[i*3+2]=z;arr[i*3]=x;arr[i*3+1]=y;arr[i*3+2]=z;phase[i]=rand(0,Math.PI*2);
  }
  const geo=new THREE.BufferGeometry(); geo.setAttribute('position',new THREE.BufferAttribute(arr,3));
  const mat=new THREE.PointsMaterial({map:SOFT,color,size,sizeAttenuation:true,transparent:true,opacity,depthWrite:false,blending:THREE.AdditiveBlending,toneMapped:false});
  const pts=new THREE.Points(geo,mat); pts.frustumCulled=false; pts.renderOrder=5;
  function update(uTime){
    const p=geo.attributes.position.array;
    for(let i=0;i<count;i++){
      const ph=phase[i], bx=base[i*3], by=base[i*3+1], bz=base[i*3+2];
      if(mode==='sand'){
        p[i*3]=wrap(bx+uTime*speed*(.55+.45*Math.sin(ph)),box.x[0],box.x[1]);
        p[i*3+1]=by+Math.sin(uTime*1.4+ph)*.12;
        p[i*3+2]=bz;
      }else if(mode==='dust'){
        p[i*3]=bx+Math.sin(uTime*.55+ph)*.45;
        p[i*3+1]=by+Math.sin(uTime*.28+ph*1.7)*.30;
        p[i*3+2]=bz+Math.cos(uTime*.42+ph)*.25;
      }else if(mode==='stars'){
        p[i*3]=bx;p[i*3+1]=by;p[i*3+2]=bz;
      }else{
        p[i*3]=bx+Math.sin(uTime*.22+ph)*1.15;
        p[i*3+1]=by+Math.sin(uTime*.13+ph*1.3)*.28;
        p[i*3+2]=bz+Math.cos(uTime*.19+ph)*.55;
      }
    }
    geo.attributes.position.needsUpdate=true;
    if(mode==='stars') mat.opacity=opacity*(.72+.28*Math.sin(uTime*1.7));
  }
  return {points:pts,update,mat};
}

function makeReflectionPlane(plate,{y=-4.4,z=-12,width=60,height=18,opacity=.22,wave=.004,tint=[1,1,1]}={}){
  const mat=new THREE.ShaderMaterial({
    uniforms:{uPlate:{value:plate},uTime:{value:0},uOpacity:{value:opacity},uWave:{value:wave},uTint:{value:new THREE.Color(tint[0],tint[1],tint[2])}},
    vertexShader:`varying vec2 vUv; void main(){vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`
      uniform sampler2D uPlate; uniform float uTime,uOpacity,uWave; uniform vec3 uTint; varying vec2 vUv;
      void main(){
        vec2 uv=vUv;
        float r=sin(uv.y*70.0+uTime*2.1)*uWave + sin(uv.x*115.0-uTime*1.35)*uWave*.45;
        vec2 s=vec2(uv.x+r, uv.y*.5 + .012*sin(uv.x*18.0+uTime*.8));
        vec3 c=texture2D(uPlate,clamp(s,0.0,1.0)).rgb*uTint;
        float fade=smoothstep(0.0,.22,uv.y)*(1.0-smoothstep(.78,1.0,uv.y));
        gl_FragColor=vec4(c,uOpacity*fade);
      }`,
    transparent:true, depthWrite:false, side:THREE.DoubleSide, toneMapped:false,
  });
  const mesh=new THREE.Mesh(new THREE.PlaneGeometry(width,height,1,1),mat);
  mesh.rotation.x=-Math.PI/2; mesh.position.set(0,y,z); mesh.renderOrder=2;
  return {mesh,mat};
}

function makeRain(count=700){
  const arr=new Float32Array(count*6), bx=new Float32Array(count), bz=new Float32Array(count), len=new Float32Array(count), sp=new Float32Array(count), by=new Float32Array(count);
  for(let i=0;i<count;i++){
    bx[i]=rand(-14,14);by[i]=rand(-9,10);bz[i]=rand(-18,4);len[i]=rand(.35,1.1);sp[i]=rand(7,13);
    arr[i*6]=bx[i];arr[i*6+1]=by[i];arr[i*6+2]=bz[i];
    arr[i*6+3]=bx[i]+rand(-.04,.04);arr[i*6+4]=by[i]-len[i];arr[i*6+5]=bz[i];
  }
  const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(arr,3));
  const mat=new THREE.LineBasicMaterial({color:0xbfe8ff,transparent:true,opacity:.22,blending:THREE.AdditiveBlending,depthWrite:false,toneMapped:false});
  const lines=new THREE.LineSegments(geo,mat);lines.frustumCulled=false;lines.renderOrder=6;
  function update(uTime){
    const p=geo.attributes.position.array;
    for(let i=0;i<count;i++){
      const y=wrap(by[i]-uTime*sp[i],-10,10);
      p[i*6]=bx[i]+Math.sin(uTime*.7+i)*.12;p[i*6+1]=y;p[i*6+2]=bz[i];
      p[i*6+3]=bx[i]+Math.sin(uTime*.7+i)*.12-.03;p[i*6+4]=y-len[i];p[i*6+5]=bz[i];
    }
    geo.attributes.position.needsUpdate=true;
  }
  return {lines,update,mat};
}

function makePine(x,y,z,s){
  const g=new THREE.Group();
  const trunkMat=new THREE.MeshStandardMaterial({color:0x1a120c,roughness:1});
  const leafMat=new THREE.MeshStandardMaterial({color:0x08170f,roughness:1});
  const trunk=new THREE.Mesh(new THREE.CylinderGeometry(.08*s,.13*s,2*s,6),trunkMat);trunk.position.y=s;g.add(trunk);
  for(let i=0;i<3;i++){
    const cone=new THREE.Mesh(new THREE.ConeGeometry((1.15-i*.22)*s,(2.35-i*.32)*s,7),leafMat);
    cone.position.y=(1.75+i*.92)*s;g.add(cone);
  }
  g.position.set(x,y,z);return g;
}

function makeNeonSign(color,x,y,z,h,phase){
  const g=new THREE.Group();
  const signMat=new THREE.MeshBasicMaterial({color,transparent:true,opacity:.60,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide,toneMapped:false});
  const sign=new THREE.Mesh(new THREE.PlaneGeometry(.32,h),signMat);
  sign.position.set(x,y,z);sign.rotation.z=rand(-.06,.06);g.add(sign);
  const glow=makeGlow(color,2.2,.22,new THREE.Vector3(x,y,z-.2));g.add(glow);
  const light=new THREE.PointLight(color,1.25,12);light.position.set(x,y,z+1);g.add(light);
  function update(uTime){
    const f=.68+.18*Math.sin(uTime*7.0+phase)+.08*Math.sin(uTime*23.0+phase*2.1);
    sign.material.opacity=Math.max(.20,f*.82);
    glow.material.opacity=.16+.10*Math.abs(Math.sin(uTime*3.1+phase));
    light.intensity=.9+.5*Math.abs(Math.sin(uTime*5.0+phase));
  }
  return {group:g,update};
}

function makeDune(){
  const geo=new THREE.PlaneGeometry(70,34,90,45);
  const p=geo.attributes.position;
  for(let i=0;i<p.count;i++){
    const x=p.getX(i),y=p.getY(i);
    const z=Math.sin(x*.22)*1.05+Math.sin(y*.38+x*.12)*.55+Math.sin(x*.71-y*.21)*.18;
    p.setZ(i,z);
  }
  p.needsUpdate=true;geo.computeVertexNormals();
  const mat=new THREE.MeshStandardMaterial({color:0xd68a4c,roughness:1,metalness:0,side:THREE.DoubleSide});
  const mesh=new THREE.Mesh(geo,mat);mesh.rotation.x=-Math.PI/2;mesh.position.set(0,-5.2,-11);mesh.renderOrder=1;
  return mesh;
}

function makeBasalt(){
  const g=new THREE.Group();
  const mat=new THREE.MeshStandardMaterial({color:0x20252a,roughness:.95,metalness:.05});
  for(let i=0;i<9;i++){
    const h=rand(2.2,5.8),r=rand(.34,.58);
    const c=new THREE.Mesh(new THREE.CylinderGeometry(r*.88,r,h,6),mat);
    c.position.set(-10.5+i*.62,-4.8+h/2,rand(-11,-3));
    c.rotation.y=rand(0,Math.PI);g.add(c);
  }
  return g;
}

function makeFoam(color=0xdff6ff,opacityBase=.20){
  const g=new THREE.Group(),lines=[];
  for(let j=0;j<3;j++){
    const N=90,arr=new Float32Array(N*3),baseY=-4.6+j*.55,baseZ=-8+j*2;
    for(let i=0;i<N;i++){arr[i*3]=-24+48*i/(N-1);arr[i*3+1]=baseY;arr[i*3+2]=baseZ;}
    const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(arr,3));
    const mat=new THREE.LineBasicMaterial({color,transparent:true,opacity:Math.max(.03,opacityBase-j*.045),blending:THREE.AdditiveBlending,depthWrite:false,toneMapped:false});
    const line=new THREE.Line(geo,mat);line.frustumCulled=false;g.add(line);
    lines.push({geo,mat,baseY,baseZ,phase:j*1.7,opacityBase:Math.max(.03,opacityBase-j*.045)});
  }
  function update(uTime){
    for(const L of lines){
      const p=L.geo.attributes.position.array;
      for(let i=0;i<p.length/3;i++){
        p[i*3+1]=L.baseY+Math.sin(i*.35+uTime*1.1+L.phase)*.055+Math.sin(i*.11-uTime*.65)*.035;
        p[i*3+2]=L.baseZ+Math.sin(i*.18+uTime*.5)*.12;
      }
      L.geo.attributes.position.needsUpdate=true;
      L.mat.opacity=L.opacityBase*(.72+.35*Math.sin(uTime*.8+L.phase));
    }
  }
  return {group:g,update};
}

function makeAurora(){
  const mat=new THREE.ShaderMaterial({
    uniforms:{uTime:{value:0}},
    vertexShader:`varying vec2 vUv; void main(){vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`
      uniform float uTime; varying vec2 vUv;
      void main(){
        float x=vUv.x;
        float wave=sin(x*7.0+uTime*.34)*.085 + sin(x*17.0-uTime*.21)*.032 + sin(x*31.0+uTime*.13)*.012;
        float y=vUv.y-wave;
        float band=smoothstep(.10,.42,y)*(1.0-smoothstep(.60,.96,y));
        float folds=.58+.22*sin(x*19.0+uTime*.55+sin(x*6.0)*1.8)
                      +.11*sin(x*43.0-uTime*.31+sin(x*11.0)*.7)
                      +.05*sin(x*83.0+uTime*.17);
        float curtain=smoothstep(.18,.88,folds);
        float edge=.72+.28*sin(x*3.0+uTime*.19);
        vec3 col=mix(vec3(.05,.90,.52),vec3(.38,.18,.92),clamp(x*.85+.08,0.0,1.0));
        gl_FragColor=vec4(col,band*curtain*edge*.20);
      }`,
    transparent:true,depthWrite:false,depthTest:false,blending:THREE.AdditiveBlending,side:THREE.DoubleSide,toneMapped:false,
  });
  const mesh=new THREE.Mesh(new THREE.PlaneGeometry(60,20,1,1),mat);
  mesh.position.set(0,5,-25);mesh.renderOrder=-500;
  return {mesh,mat};
}

function makeTempleStones(){
  const g=new THREE.Group();
  const stone=new THREE.MeshStandardMaterial({color:0x55584b,roughness:1});
  const moss=new THREE.MeshStandardMaterial({color:0x2f5c2c,roughness:1});
  for(let i=0;i<9;i++){
    const sx=rand(.7,1.8),sy=rand(.35,.9),sz=rand(.7,1.6);
    const b=new THREE.Mesh(new THREE.BoxGeometry(sx,sy,sz),stone);
    b.position.set(rand(-9,9),-4.6+sy/2,rand(-9,-1.5));
    b.rotation.y=rand(-.5,.5);b.rotation.z=rand(-.08,.08);g.add(b);
    const m=new THREE.Mesh(new THREE.PlaneGeometry(sx*.82,sz*.72),moss);
    m.rotation.x=-Math.PI/2;m.position.set(b.position.x,b.position.y+sy/2+.012,b.position.z);m.rotation.z=b.rotation.y;g.add(m);
  }
  for(const x of [-3.6,3.6]){
    const p=new THREE.Mesh(new THREE.BoxGeometry(.75,4.4,.75),stone);
    p.position.set(x,-2.6,-12);g.add(p);
  }
  const lintel=new THREE.Mesh(new THREE.BoxGeometry(8.2,.75,.9),stone);
  lintel.position.set(0,-.35,-12);g.add(lintel);
  return g;
}

async function init(){
  const loader=new THREE.TextureLoader();
  const urls=[
    '/assets/references/v6/01_alpine_lake_16x9.jpg',
    '/assets/references/v6/02_neon_rain_alley_16x9.jpg',
    '/assets/references/v6/03_sahara_dunes_16x9.jpg',
    '/assets/references/v6/04_iceland_aurora_16x9.jpg',
    '/assets/references/v6/05_rainforest_temple_16x9.jpg',
  ];
  const textures=await Promise.all(urls.map(async u=>{
    const t=await loader.loadAsync(u);
    t.colorSpace=THREE.SRGBColorSpace;t.minFilter=THREE.LinearFilter;t.magFilter=THREE.LinearFilter;
    t.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());return t;
  }));
  const rawTextures=textures.map(t=>{const r=t.clone();r.colorSpace=THREE.NoColorSpace;r.needsUpdate=true;return r;});

  // The generated references are the actual scene backplates. A gentle
  // scene-specific UV shimmer keeps the photographic plate alive between
  // camera moves without inventing a second, stylized image.
  const bgMat=new THREE.ShaderMaterial({
    uniforms:{uMap:{value:rawTextures[0]},uTime:{value:0},uWarp:{value:.0008}},
    vertexShader:`varying vec2 vUv; void main(){vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`
      uniform sampler2D uMap; uniform float uTime,uWarp; varying vec2 vUv;
      void main(){
        vec2 uv=vUv;
        float shimmer=sin(uv.y*72.0+uTime*.85)*uWarp + sin(uv.x*118.0-uTime*.61)*uWarp*.42;
        float breathe=sin(uv.x*9.0+uTime*.23)*uWarp*.35;
        vec2 sample2=clamp(vec2(uv.x+shimmer,uv.y+breathe),vec2(0.001),vec2(0.999));
        vec3 rgb=texture2D(uMap,sample2).rgb;
        gl_FragColor=vec4(rgb,1.0);
      }`,
    side:THREE.DoubleSide, depthTest:false, depthWrite:false, toneMapped:false,
  });
  const bg=new THREE.Mesh(new THREE.PlaneGeometry(100,56.25),bgMat);
  bg.position.z=-50;bg.frustumCulled=false;bg.renderOrder=-1000;scene.add(bg);

  const ambient=new THREE.AmbientLight(0xffffff,.55);scene.add(ambient);
  const hemi=new THREE.HemisphereLight(0xffffff,0x223344,.38);scene.add(hemi);
  const dir=new THREE.DirectionalLight(0xffffff,1.3);dir.position.set(5,8,4);scene.add(dir);
  dir.target.position.set(0,0,-12);scene.add(dir.target);

  const groups=[];

  // 01 Alpine lake: rippled reflection, low drifting mist, warm sun bloom.
  {
    const g=new THREE.Group();
    const ref=makeReflectionPlane(rawTextures[0],{y:-4.4,z:-12,opacity:.23,wave:.0035,tint:[.94,1.0,1.06]});
    g.add(ref.mesh);
    const mist=makeParticles({count:170,color:0xdce8f0,size:.58,opacity:.09,box:{x:[-20,20],y:[-3,.8],z:[-18,0]},mode:'mist'});
    g.add(mist.points);
    const sun=makeGlow(0xffd39a,5.5,.22,new THREE.Vector3(7,4,-18));g.add(sun);
    g.add(makeShadeSprite(0x07120c,8,.20,new THREE.Vector3(-10,-4.2,-2)));
    g.add(makeShadeSprite(0x07120c,7,.17,new THREE.Vector3(10,-4.4,-3)));
    g.userData.update=uTime=>{
      ref.mat.uniforms.uTime.value=uTime;mist.update(uTime);
      sun.material.opacity=.19+.05*Math.sin(uTime*.7);
    };
    groups.push(g);
  }

  // 02 Neon rain alley: falling rain, steam, flickering neon and wet reflections.
  {
    const g=new THREE.Group();
    const ref=makeReflectionPlane(rawTextures[1],{y:-4.5,z:-10,opacity:.30,wave:.006,tint:[1.0,1.12,1.28]});
    g.add(ref.mesh);
    const rain=makeRain(720);g.add(rain.lines);
    const steam=makeParticles({count:110,color:0xc8d4ff,size:1.2,opacity:.08,box:{x:[-8,8],y:[-4,2],z:[-12,2]},mode:'mist'});
    g.add(steam.points);
    const signs=[
      makeNeonSign(0x28e0ff,-5.2,1.2,-10,3.2,.4),
      makeNeonSign(0xff2fa0,5.0,1.6,-11,3.8,1.8),
      makeNeonSign(0xffb347,-3.8,2.6,-14,2.2,3.1),
      makeNeonSign(0x8a5cff,4.2,3.0,-16,2.6,4.6),
    ];
    signs.forEach(s=>g.add(s.group));
    const puddleA=makeGlow(0x28e0ff,5.0,.09,new THREE.Vector3(-4,-4.2,-4));g.add(puddleA);
    const puddleB=makeGlow(0xff2fa0,4.6,.08,new THREE.Vector3(4,-4.3,-5));g.add(puddleB);
    g.userData.update=uTime=>{
      ref.mat.uniforms.uTime.value=uTime;rain.update(uTime);steam.update(uTime);
      signs.forEach(s=>s.update(uTime));
      puddleA.material.opacity=.07+.04*Math.sin(uTime*2.1);
      puddleB.material.opacity=.06+.04*Math.sin(uTime*2.6+1.2);
    };
    groups.push(g);
  }

  // 03 Sahara dunes: heat-shimmered plate, wind-blown sand and soft dune ripples.
  {
    const g=new THREE.Group();
    const ref=makeReflectionPlane(rawTextures[2],{y:-4.8,z:-13,opacity:.16,wave:.0065,tint:[1.06,.99,.90]});
    g.add(ref.mesh);
    const ripples=makeFoam(0xffcf8a,.10);g.add(ripples.group);
    const sand=makeParticles({count:260,color:0xffc27a,size:.10,opacity:.22,box:{x:[-20,20],y:[-2,2],z:[-16,2]},mode:'sand',speed:3.2});
    g.add(sand.points);
    const sun=makeGlow(0xffc06a,7.0,.30,new THREE.Vector3(6,4,-18));g.add(sun);
    g.userData.update=uTime=>{
      ref.mat.uniforms.uTime.value=uTime;ripples.update(uTime);sand.update(uTime);
      sun.material.opacity=.26+.06*Math.sin(uTime*.55);
    };
    groups.push(g);
  }

  // 04 Iceland aurora: animated aurora curtain, stars, basalt columns, surf foam.
  {
    const g=new THREE.Group();
    const aur=makeAurora();g.add(aur.mesh);
    const stars=makeParticles({count:520,color:0xffffff,size:.13,opacity:.72,box:{x:[-28,28],y:[2,15],z:[-34,-26]},mode:'stars'});
    g.add(stars.points);
    const foam=makeFoam();g.add(foam.group);
    g.add(makeShadeSprite(0x050a10,8,.18,new THREE.Vector3(-10,-4.2,-2)));
    g.add(makeShadeSprite(0x050a10,7,.14,new THREE.Vector3(10,-4.4,-3)));
    const ref=makeReflectionPlane(rawTextures[3],{y:-4.6,z:-11,opacity:.20,wave:.005,tint:[.90,1.04,1.18]});
    g.add(ref.mesh);
    g.userData.update=uTime=>{
      aur.mat.uniforms.uTime.value=uTime;stars.update(uTime);foam.update(uTime);
      ref.mat.uniforms.uTime.value=uTime;
    };
    groups.push(g);
  }

  // 05 Rainforest temple: floating dust and soft foreground canopy shadows.
  {
    const g=new THREE.Group();
    const ref=makeReflectionPlane(rawTextures[4],{y:-4.7,z:-12,opacity:.05,wave:.004,tint:[1.04,1.02,.92]});
    g.add(ref.mesh);
    const dust=makeParticles({count:260,color:0xffe3ad,size:.14,opacity:.24,box:{x:[-12,12],y:[-2,5],z:[-16,2]},mode:'dust'});
    g.add(dust.points);
    const glowA=makeGlow(0xffdda0,5,.16,new THREE.Vector3(-4,4,-14));g.add(glowA);
    const glowB=makeGlow(0xd8ffb0,3.5,.10,new THREE.Vector3(5,2,-10));g.add(glowB);
    g.add(makeShadeSprite(0x081a0a,9,.24,new THREE.Vector3(-10,-3.5,-2)));
    g.add(makeShadeSprite(0x081a0a,8,.21,new THREE.Vector3(10,-3.8,-3)));
    g.add(makeShadeSprite(0x0b1f0c,7,.16,new THREE.Vector3(-8,4,-4)));
    g.userData.update=uTime=>{
      ref.mat.uniforms.uTime.value=uTime;dust.update(uTime);
      glowA.material.opacity=.13+.04*Math.sin(uTime*.6);
      glowB.material.opacity=.08+.03*Math.sin(uTime*.9+1.4);
    };
    groups.push(g);
  }

  groups.forEach(g=>{g.visible=false;scene.add(g);});

  const settings=[
    {ambient:0x9fb8c8,ai:.55,hemiSky:0xbfd8e8,hemiGround:0x243322,directional:0xffd6a0,di:1.7,exposure:1.00,vignette:.23,grain:.012,warp:.0008},
    {ambient:0x3a4660,ai:.32,hemiSky:0x546a9a,hemiGround:0x10121c,directional:0x8aa6ff,di:.55,exposure:1.08,vignette:.34,grain:.020,warp:.0013},
    {ambient:0xffd0a0,ai:.62,hemiSky:0xffd8a0,hemiGround:0x6b3a22,directional:0xffb066,di:2.0,exposure:1.02,vignette:.24,grain:.013,warp:.0028},
    {ambient:0x4a5a78,ai:.30,hemiSky:0x294b6e,hemiGround:0x0a1018,directional:0x8fd8c0,di:.75,exposure:1.05,vignette:.30,grain:.018,warp:.0006},
    {ambient:0xa8b88a,ai:.48,hemiSky:0xb8d09a,hemiGround:0x1d2a16,directional:0xffe0a0,di:1.45,exposure:1.00,vignette:.27,grain:.015,warp:.0009},
  ];

  const motions=[
    t=>{const e=ease(t);camera.position.set(.45*Math.sin(t*Math.PI),.12*Math.sin(t*2.1),10-3.8*e);camera.lookAt(1.1*e,.1,-20);camera.rotation.z=.006*Math.sin(t*3);},
    t=>{const e=ease(t);camera.position.set(.55*Math.sin(t*2.2),.10*Math.sin(t*1.7),10-5.2*e);camera.lookAt(.3*Math.sin(t*1.3),-.2,-20);camera.rotation.z=.012*Math.sin(t*2.5);},
    t=>{const e=ease(t);camera.position.set(-1.2+2.4*e,.08*Math.sin(t*1.8),10-2.2*e);camera.lookAt(-1.0+2.0*e,.2,-20);camera.rotation.z=-.008*Math.sin(t*2);},
    t=>{const e=ease(t);camera.position.set(-.8+1.6*e,-.3+.9*e,10-1.8*e);camera.lookAt(-.5+1.0*e,.6+1.1*e,-22);camera.rotation.z=.009*Math.sin(t*1.6);},
    t=>{const e=ease(t);camera.position.set(.25*Math.sin(t*2.4),.10*Math.sin(t*1.9),10-4.4*e);camera.lookAt(.2*Math.sin(t*1.2),.15,-20);camera.rotation.z=.005*Math.sin(t*2.8);},
  ];

  let active=0;
  function renderFrame(t){
    const uTime=t*DURATION;
    motions[active](t);
    const u=groups[active].userData.update;
    if(u)u(uTime);
    bgMat.uniforms.uTime.value=uTime;
    overlayMat.uniforms.uTime.value=uTime;
    renderer.clear(true,true,true);
    renderer.render(scene,camera);
    renderer.clearDepth();
    renderer.render(overlayScene,overlayCamera);
    renderer.getContext().finish();
  }
  function renderAt(t){
    renderFrame(t);
    return renderer.domElement.toDataURL('image/jpeg',.90);
  }
  function setShot(i){
    active=Math.max(0,Math.min(groups.length-1,i|0));
    groups.forEach((g,k)=>{g.visible=(k===active);});
    bgMat.uniforms.uMap.value=rawTextures[active];
    const s=settings[active];
    ambient.color.setHex(s.ambient);ambient.intensity=s.ai;
    hemi.color.setHex(s.hemiSky);hemi.groundColor.setHex(s.hemiGround);
    dir.color.setHex(s.directional);dir.intensity=s.di;
    renderer.toneMappingExposure=s.exposure;
    overlayMat.uniforms.uVignette.value=s.vignette;
    overlayMat.uniforms.uGrain.value=s.grain;
    bgMat.uniforms.uWarp.value=s.warp;
    renderFrame(0);
    return SHOT_NAMES[active];
  }
  window.setShot=setShot;
  window.setTime=t=>{renderFrame(t);return true;};
  window.renderAt=renderAt;
  setShot(0);
  window.ready=true;
}

init().catch(e=>{window.error=e.stack||String(e);console.error('FIVE WORLDS INIT ERROR',e);});
