/* Linguist-X v95 — one-click static Gate → Guide Me lens.
 * Geolocation + absolute device orientation produce a straight-line BEARING to a
 * surveyed public Ashburn Metro station reference. This is NOT indoor wayfinding,
 * optical localization, AR spatial anchoring, a verified pedestrian route, or a
 * provider-integrated gate locator. No camera frames or coordinates leave the browser.
 * Future indoor routing must use licensed airport geometry and localization evidence.
 */
(()=>{
 'use strict';
 const app=document.getElementById('app');
 const live=document.getElementById('live');
 const gate=document.getElementById('lxGateAccess');
 if(!app||!live||!gate)return;
 const DESTINATION=Object.freeze({name:'Ashburn Metro',lat:39.00497,lon:-77.4912});
 const $=(selector,within=document)=>within.querySelector(selector);
 const reduced=()=>app.classList.contains('less-motion')||window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
 const clamp=(value,low,high)=>Math.min(high,Math.max(low,value));
 const mod360=angle=>((angle%360)+360)%360;
 const signedAngle=angle=>((angle+540)%360)-180;
 function geoBearing(lat1,lon1,lat2,lon2){
  const radians=degrees=>degrees*Math.PI/180;
  const a=radians(lat1),b=radians(lat2),dl=radians(lon2-lon1);
  return mod360(Math.atan2(Math.sin(dl)*Math.cos(b),Math.cos(a)*Math.sin(b)-Math.sin(a)*Math.cos(b)*Math.cos(dl))*180/Math.PI);
 }
 function geoDistance(lat1,lon1,lat2,lon2){
  const radians=degrees=>degrees*Math.PI/180;
  const dLat=radians(lat2-lat1),dLon=radians(lon2-lon1);
  const h=Math.sin(dLat/2)**2+Math.cos(radians(lat1))*Math.cos(radians(lat2))*Math.sin(dLon/2)**2;
  return 6371000*2*Math.asin(Math.min(1,Math.sqrt(h)));
 }
function compassHeading(event,screenAngle=0){
  // True-north heading on Safari, otherwise a north-referenced absolute yaw.
  // A relative alpha alone has an arbitrary origin: it must never steer a map arrow.
  const frame=Number.isFinite(screenAngle)?screenAngle:0;
  if(Number.isFinite(event.webkitCompassHeading)){
   if(Number.isFinite(event.webkitCompassAccuracy)&&event.webkitCompassAccuracy>30)return null;
   return mod360(event.webkitCompassHeading+frame);
  }
  if((event.absolute===true||event.type==='deviceorientationabsolute')&&Number.isFinite(event.alpha)){
   if(Number.isFinite(event.beta)&&Math.abs(event.beta)>155)return null;
   return mod360(360-event.alpha+frame);
  }
  return null;
 }
 const COPY={
  en:{openGate:'Open Guide Me from your gate',gate:'CURRENT GATE',action:'Guide Me',cardNote:'Ashburn Metro · reference destination',close:'Close',back:'Back to Live',lens:'Guide Me',prototype:'DEMO',dest:'REFERENCE DESTINATION',station:'Ashburn Metro',test:'From Gate {gate} · reference point only',distance:'Straight-line distance',calibrate:'Finding your position',calibrateSub:'Allow location and orientation to see the bearing.',waiting:'Finding your direction',waitingSub:'Point the phone ahead and gently turn it to calibrate.',poor:'Location is too approximate',poorSub:'Move toward a clearer area or use the preview. No route is being calculated.',ahead:'Target ahead',behind:'Target behind you',left:'Target to your left',right:'Target to your right',aim:'Point toward the center arrow. Use airport signs for walking directions.',near:'Near the reference point',nearSub:'Precise entrance and walking route are not available.',missing:'Direction unavailable',missingSub:'This device cannot supply a reliable compass heading here.',blocked:'Location unavailable',blockedSub:'Check browser permissions and try again, or preview the lens.',distanceUnknown:'Waiting for GPS',preview:'Explore the lens in demo mode',previewTag:'SIMULATED',previewCopy:'Demo only · turn the virtual heading.',previewTurn:'Rotate view',cameraOff:'Camera off · sky view',cameraOn:'Camera view',disclaimer:'Straight-line bearing only · Not an airport walking route',previewDisclaimer:'Simulated position and heading · Not navigation',accuracy:'Approx. ±{meters} m',privacy:'Camera and position stay on your device',help:'Test destination: Ashburn Metro station, Virginia.'},
  fr:{openGate:'Ouvrir le guidage depuis votre porte',gate:'VOTRE PORTE',action:'Guide-moi',cardNote:'Essayez la vue avec une station de référence.',close:'Fermer',back:'Retour au direct',lens:'Guide-moi',prototype:'APERÇU',dest:'DESTINATION DE TEST',station:'Métro Ashburn',test:'Porte {gate} · essai, pas un itinéraire de porte',distance:'Distance à vol d’oiseau',calibrate:'Recherche de position',calibrateSub:'Autorisez la position et l’orientation.',waiting:'Recherche de direction',waitingSub:'Tenez le téléphone devant vous et tournez-le doucement.',poor:'Position trop approximative',poorSub:'Cherchez un endroit dégagé ou ouvrez l’aperçu.',ahead:'Objectif devant vous',behind:'Objectif derrière vous',left:'Objectif à gauche',right:'Objectif à droite',aim:'Suivez la flèche visuelle ; utilisez la signalétique pour marcher.',near:'Près du point de référence',nearSub:'L’entrée et le chemin exacts ne sont pas fournis.',missing:'Direction indisponible',missingSub:'Aucune orientation fiable sur cet appareil.',blocked:'Position indisponible',blockedSub:'Vérifiez les autorisations, ou ouvrez l’aperçu.',distanceUnknown:'GPS en attente',preview:'Voir l’aperçu',previewTag:'SIMULÉ',previewCopy:'Essai · faites tourner l’orientation virtuelle.',previewTurn:'Tourner la vue',cameraOff:'Caméra indisponible · aperçu',cameraOn:'Vue caméra',disclaimer:'Direction directe uniquement · Pas un itinéraire piéton',previewDisclaimer:'Position simulée · Pas de navigation',accuracy:'Env. ±{meters} m',privacy:'Caméra et position restent sur votre appareil',help:'Destination test : station de métro Ashburn, Virginie.'},
  es:{openGate:'Abrir indicaciones desde tu puerta',gate:'TU PUERTA',action:'Guíame',cardNote:'Prueba la vista con una estación de referencia.',close:'Cerrar',back:'Volver al directo',lens:'Guíame',prototype:'VISTA PREVIA',dest:'DESTINO DE PRUEBA',station:'Metro Ashburn',test:'Puerta {gate} · prueba, no ruta de embarque',distance:'Distancia en línea recta',calibrate:'Buscando ubicación',calibrateSub:'Permite ubicación y orientación.',waiting:'Buscando dirección',waitingSub:'Apunta el móvil al frente y gíralo suavemente.',poor:'Ubicación imprecisa',poorSub:'Busca una zona despejada o abre la vista previa.',ahead:'Destino delante',behind:'Destino detrás',left:'Destino a la izquierda',right:'Destino a la derecha',aim:'Usa la flecha y las señales para caminar.',near:'Cerca del punto de referencia',nearSub:'No hay ruta ni entrada exactas.',missing:'Dirección no disponible',missingSub:'Este dispositivo no ofrece brújula fiable.',blocked:'Ubicación no disponible',blockedSub:'Comprueba los permisos o abre la vista previa.',distanceUnknown:'Esperando GPS',preview:'Ver vista previa',previewTag:'SIMULADO',previewCopy:'Prueba · gira la orientación virtual.',previewTurn:'Girar vista',cameraOff:'Cámara no disponible · vista previa',cameraOn:'Vista de cámara',disclaimer:'Rumbo directo · No es una ruta peatonal',previewDisclaimer:'Posición simulada · No navegar',accuracy:'Aprox. ±{meters} m',privacy:'La cámara y la ubicación permanecen en tu dispositivo',help:'Destino de prueba: estación Ashburn Metro, Virginia.'},
  zh:{openGate:'从登机口打开方向指引',gate:'您的登机口',action:'指引我',cardNote:'以地铁站为参考体验新视图。',close:'关闭',back:'返回实时页',lens:'指引我',prototype:'预览',dest:'测试目的地',station:'阿什本地铁站',test:'登机口 {gate} · 仅为测试，不是登机口路线',distance:'直线距离',calibrate:'正在确定位置',calibrateSub:'请允许定位和方向传感器。',waiting:'正在确定方向',waitingSub:'将手机朝前并轻轻转动。',poor:'定位不够精确',poorSub:'请到开阔处或使用预览。',ahead:'目标在前方',behind:'目标在身后',left:'目标在左侧',right:'目标在右侧',aim:'参考中央箭头；实际行走请遵循指示牌。',near:'已接近参考点',nearSub:'尚无准确入口或步行路线。',missing:'方向不可用',missingSub:'此设备无法提供可靠方向。',blocked:'定位不可用',blockedSub:'检查浏览器权限或打开预览。',distanceUnknown:'等待定位',preview:'查看设计预览',previewTag:'模拟',previewCopy:'仅为演示 · 可旋转模拟方向。',previewTurn:'旋转视角',cameraOff:'相机不可用 · 预览',cameraOn:'相机视图',disclaimer:'仅显示直线方位 · 非机场步行路线',previewDisclaimer:'模拟位置与方向 · 请勿用于导航',accuracy:'约 ±{meters} 米',privacy:'相机及位置信息仅留在本机',help:'测试目的地：弗吉尼亚州阿什本地铁站。'},
  ar:{openGate:'فتح الإرشادات من بوابتك',gate:'بوابتك',action:'أرشدني',cardNote:'جرّب العدسة مع محطة مرجعية.',close:'إغلاق',back:'العودة إلى البث',lens:'أرشدني',prototype:'معاينة',dest:'وجهة اختبار',station:'محطة أشبرن',test:'البوابة {gate} · اختبار وليست طريقاً للبوابة',distance:'المسافة المباشرة',calibrate:'جارٍ تحديد موقعك',calibrateSub:'اسمح بالوصول للموقع واتجاه الجهاز.',waiting:'جارٍ تحديد الاتجاه',waitingSub:'وجّه هاتفك للأمام وأدره برفق.',poor:'الموقع غير دقيق',poorSub:'انتقل لمكان أوضح أو افتح المعاينة.',ahead:'الهدف أمامك',behind:'الهدف خلفك',left:'الهدف على يسارك',right:'الهدف على يمينك',aim:'استخدم السهم واتبع لافتات المطار للمشي.',near:'أنت قرب النقطة المرجعية',nearSub:'لا تتوفر طريق المشي أو المدخل الدقيق.',missing:'الاتجاه غير متاح',missingSub:'لا يوفر الجهاز اتجاهاً موثوقاً هنا.',blocked:'الموقع غير متاح',blockedSub:'تحقق من الأذونات أو افتح المعاينة.',distanceUnknown:'بانتظار GPS',preview:'معاينة التصميم',previewTag:'محاكاة',previewCopy:'تجربة فقط · غيّر الاتجاه الافتراضي.',previewTurn:'تدوير المنظر',cameraOff:'الكاميرا غير متاحة · معاينة',cameraOn:'عرض الكاميرا',disclaimer:'اتجاه مباشر فقط · ليس مساراً للمشي',previewDisclaimer:'موقع واتجاه افتراضيان · ليس للملاحة',accuracy:'تقريباً ±{meters} م',privacy:'تبقى الكاميرا والموقع على جهازك',help:'وجهة الاختبار: محطة مترو أشبرن، فيرجينيا.'},
  pt:{openGate:'Abrir orientação a partir da sua porta',gate:'A SUA PORTA',action:'Guia-me',cardNote:'Experimente a lente com uma estação de referência.',close:'Fechar',back:'Voltar ao direto',lens:'Guia-me',prototype:'PRÉ-VISUALIZAÇÃO',dest:'DESTINO DE TESTE',station:'Metro Ashburn',test:'Porta {gate} · teste, não é uma rota para a porta',distance:'Distância em linha reta',calibrate:'A localizar',calibrateSub:'Permita a localização e a orientação.',waiting:'A procurar a direção',waitingSub:'Aponte o telemóvel para a frente e rode-o devagar.',poor:'Posição pouco precisa',poorSub:'Vá para uma zona aberta ou veja a pré-visualização.',ahead:'Objetivo em frente',behind:'Objetivo atrás de si',left:'Objetivo à esquerda',right:'Objetivo à direita',aim:'Siga a seta visual e as placas para caminhar.',near:'Perto do ponto de referência',nearSub:'Não há entrada nem rota a pé precisas.',missing:'Direção indisponível',missingSub:'Este dispositivo não tem bússola fiável.',blocked:'Localização indisponível',blockedSub:'Verifique as permissões ou abra a pré-visualização.',distanceUnknown:'À espera do GPS',preview:'Ver pré-visualização',previewTag:'SIMULADO',previewCopy:'Demonstração · rode o rumo virtual.',previewTurn:'Rodar vista',cameraOff:'Câmara indisponível · pré-visualização',cameraOn:'Vista da câmara',disclaimer:'Rumo direto · Não é um percurso pedonal',previewDisclaimer:'Posição simulada · Não navegar',accuracy:'Aprox. ±{meters} m',privacy:'A câmara e a posição ficam no seu dispositivo',help:'Destino teste: estação de metro Ashburn, Virgínia.'}
 };
 function lang(){const l=(document.documentElement.lang||'en').toLowerCase();return l.startsWith('fr')?'fr':l.startsWith('es')?'es':l.startsWith('zh')?'zh':l.startsWith('ar')?'ar':l.startsWith('pt')?'pt':'en';}
 const tr=(key,vars={})=>(COPY[lang()]||COPY.en)[key].replace(/\{(\w+)\}/g,(_,name)=>String(vars[name]??''));
 const icon={
  back:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m14 5-7 7 7 7"/></svg>',
  arrow:'<svg viewBox="0 0 160 160" fill="none" aria-hidden="true"><defs><linearGradient id="lxLensArrowFill" x1="28" y1="9" x2="131" y2="135" gradientUnits="userSpaceOnUse"><stop stop-color="#397fb3"/><stop offset=".49" stop-color="#1d517e"/><stop offset="1" stop-color="#173652"/></linearGradient></defs><path d="M80 10 137 114c3 6-2 12-9 10l-48-20-48 20c-7 2-12-4-9-10L80 10Z" fill="url(#lxLensArrowFill)" stroke="#f9fdff" stroke-opacity=".95" stroke-width="2"/><path d="M80 20v78" stroke="#B8E8F9" stroke-opacity=".58" stroke-width="2.5" stroke-linecap="round"/></svg>',
  navigate:'<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M20.5 2.1 2.8 9.5a1 1 0 0 0 .06 1.87l6.4 2.31 2.3 6.41a1 1 0 0 0 1.88.04l7.98-17.07a.83.83 0 0 0-1.02-.96Z" fill="currentColor"/><path d="m9.4 13.5 10.2-10" stroke="#dcebf9" stroke-width=".9" opacity=".6"/></svg>',
  metro:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="6" y="3.5" width="12" height="13" rx="4" fill="currentColor" fill-opacity=".08"/><path d="M7 9h10"/><path d="M9.2 19 12 16.5 14.8 19"/><path d="M8.5 14.5h.01"/><path d="M15.5 14.5h.01"/></svg>',
  phone:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="8" y="2.5" width="8" height="19" rx="2.3"/><path d="M11.3 18.2h1.4"/></svg>'
 };
 let lens=null,previousFocus=null,opened=false,activeSession=0;
 let cameraStream=null,locationWatch=null,orientationListener=null,timeoutId=0,heartbeatId=0;
 let lastPosition=null,heading=null,headingAt=0,locationError='',headingError='';
 let preview=false,previewHeading=0,morph=null;
 const guideAction=document.getElementById('lxGateGuideAction');
 // Fit the visible translation to its REAL rendered space. Normal labels keep
 // their original CSS size; only a label that would crowd an edge gets smaller.
 // This supports all languages, text changes, font loading and screen rotation.
 const gateHeading=document.getElementById('gateHeading');
 const gateActionLabel=guideAction?.querySelector('.lx-gate-guide-label');
 let textFitFrame=0;
 function fitGateLabel(node,property,inset,minSize){
  if(!node)return;
  node.style.removeProperty(property);
  const bounds=node.getBoundingClientRect();
  if(bounds.width<1||!node.textContent?.trim())return;
  const free=Math.max(1,node.clientWidth-inset);
  const span=document.createRange();
  span.selectNodeContents(node);
  const measured=span.getBoundingClientRect().width;
  if(measured<=free+.1)return;
  const normal=Number.parseFloat(window.getComputedStyle(node).fontSize);
  if(!Number.isFinite(normal)||normal<=0)return;
  let next=Math.max(minSize,normal*free/measured);
  node.style.setProperty(property,next.toFixed(2)+'px');
  // Fractional glyph metrics and letter spacing may need a final small correction.
  for(let i=0;i<4&&span.getBoundingClientRect().width>free+.3&&next>minSize;i++){
   next=Math.max(minSize,next*.975);
   node.style.setProperty(property,next.toFixed(2)+'px');
  }
 }
 function fitGateCopy(){
  textFitFrame=0;
  fitGateLabel(gateHeading,'--lx-gate-heading-fit',24,6.4);
  fitGateLabel(gateActionLabel,'--lx-gate-action-fit',2,9.0);
 }
 function scheduleGateCopyFit(){
  if(textFitFrame)cancelAnimationFrame(textFitFrame);
  textFitFrame=requestAnimationFrame(fitGateCopy);
 }
 const refs=()=>({gate:$('#gate')?.textContent?.trim()||'—'});
 const flightAtmosphere=()=>{const photo=$('#flightWeatherBg');const value=photo?window.getComputedStyle(photo).backgroundImage:'';return value&&value!=='none'?value:"url('/weather/cloudy.webp')";};
 function formatDistance(meters){
  if(!Number.isFinite(meters))return '—';
  if(meters<305)return Math.max(10,Math.round(meters*3.28084/10)*10)+' ft';
  if(meters<16093)return (meters/1609.344).toFixed(meters<1609?1:1)+' mi';
  return (meters/1000).toFixed(meters<10000?1:0)+' km';
 }
 function reportError(){return 'blocked';}
 function stopSensors(){
  if(locationWatch!==null&&navigator.geolocation){navigator.geolocation.clearWatch(locationWatch);locationWatch=null;}
  if(orientationListener){window.removeEventListener('deviceorientation',orientationListener);window.removeEventListener('deviceorientationabsolute',orientationListener);orientationListener=null;}
  if(cameraStream){for(const t of cameraStream.getTracks())t.stop();cameraStream=null;}
  const vid=$('.lx-wayfinder-video',lens);
  if(vid){vid.pause();vid.srcObject=null;}
  if(lens)lens.classList.remove('has-camera');
  clearTimeout(timeoutId);clearInterval(heartbeatId);timeoutId=0;heartbeatId=0;
 }
 const readRect=node=>{const r=node.getBoundingClientRect(),a=app.getBoundingClientRect();return {left:r.left-a.left,top:r.top-a.top,width:r.width,height:r.height,right:r.right-a.left,bottom:r.bottom-a.top};};
 const keyframes=(from,to)=>[Object.fromEntries(Object.entries(from).map(([k,v])=>[k,typeof v==='number'?v+'px':v])),Object.fromEntries(Object.entries(to).map(([k,v])=>[k,typeof v==='number'?v+'px':v]))];
 function paintCopy(){
  // Static HTML owns the card. This routine translates its existing action and
  // accommodates live gate updates; it never creates controls or a tooltip.
  gate.dataset.gateLength=String(refs().gate.replace(/\s/g,'').length);
  gate.setAttribute('aria-label',tr('gate')+': '+refs().gate);
  if(guideAction){
   $('.lx-gate-guide-label',guideAction).textContent=tr('action');
   guideAction.setAttribute('aria-label',tr('action')+' · '+refs().gate);
  }
  if(lens){
   $('.lx-wayfinder-back',lens).setAttribute('aria-label',tr('back'));
   $('.lx-wayfinder-title b',lens).textContent=tr('lens');
   $('.lx-wayfinder-title small',lens).textContent=tr('station');
   $('.lx-wayfinder-title em',lens).textContent=tr('test',refs());
   $('.lx-wayfinder-disclaimer',lens).textContent=tr('disclaimer');
   repaintGuidance();
  }
 }
 function openLens(){
  if(opened)return;
  const from=readRect(gate);
  opened=true;activeSession++;preview=false;previewHeading=0;heading=null;headingAt=0;lastPosition=null;locationError='';headingError='';
  const token=activeSession;
  let permissionPromise;
  try{permissionPromise=typeof DeviceOrientationEvent!=='undefined'&&typeof DeviceOrientationEvent.requestPermission==='function'?DeviceOrientationEvent.requestPermission():Promise.resolve('granted');}
  catch{permissionPromise=Promise.resolve('denied');}
  lens=document.createElement('section');lens.className='lx-wayfinder-lens';lens.id='lxGuideLens';lens.setAttribute('role','dialog');lens.setAttribute('aria-modal','true');lens.setAttribute('aria-label',tr('lens'));lens.dataset.guidance='waiting';
  lens.innerHTML='<div class="lx-wayfinder-scene" aria-hidden="true"></div><div class="lx-wayfinder-ambient" aria-hidden="true"></div><video class="lx-wayfinder-video" autoplay muted playsinline aria-label="Camera preview"></video><div class="lx-wayfinder-top"><button class="lx-wayfinder-back" type="button">'+icon.back+'</button><div class="lx-wayfinder-header"><div class="lx-wayfinder-title"><b></b><small></small><em></em></div><div class="lx-wayfinder-mode" aria-hidden="true">'+icon.metro+'</div></div></div><div class="lx-wayfinder-center"><div class="lx-wayfinder-dial" aria-hidden="true"><div class="lx-wayfinder-crosshair"></div><div class="lx-wayfinder-compass-rose"><span class="lx-wayfinder-cardinal n">N</span><span class="lx-wayfinder-cardinal e">E</span><span class="lx-wayfinder-cardinal s">S</span><span class="lx-wayfinder-cardinal w">W</span></div><div class="lx-wayfinder-arrow" id="lxLensArrow">'+icon.arrow+'</div><div class="lx-wayfinder-distance-card"><strong class="lx-wayfinder-distance-value">—</strong><span class="lx-wayfinder-distance-state"></span></div></div></div><div class="lx-wayfinder-bottom"><div class="lx-wayfinder-helper"><span class="lx-wayfinder-helper-icon" aria-hidden="true">'+icon.phone+'</span><span class="lx-wayfinder-helper-text"></span></div><div class="lx-wayfinder-meta"><span class="lx-wayfinder-sensor-chip"></span><p class="lx-wayfinder-disclaimer"></p></div></div>';
  lens.style.setProperty('--lx-wayfinder-scene',flightAtmosphere());
  if(reduced())lens.classList.add('no-motion');
  app.append(lens);
  const video=$('.lx-wayfinder-video',lens);
  $('.lx-wayfinder-back',lens).addEventListener('click',closeLens);
  paintCopy();
  if(!reduced()&&typeof lens.animate==='function'){
   morph=document.createElement('div');morph.className='lx-wayfinder-morph';Object.assign(morph.style,{left:from.left+'px',top:from.top+'px',width:from.width+'px',height:from.height+'px',borderRadius:'28px'});app.append(morph);
   const a=morph.animate(keyframes(from,{left:0,top:0,width:app.clientWidth,height:app.clientHeight}),{duration:520,easing:'cubic-bezier(.18,.79,.23,1)',fill:'forwards'});
   a.onfinish=()=>{morph?.remove();morph=null;};setTimeout(()=>{morph?.remove();morph=null;},650);
   lens.animate([{opacity:0},{opacity:0,offset:.18},{opacity:1}],{duration:530,easing:'ease-out'});
  }
  live.inert=true;
  $('.lx-wayfinder-back',lens).focus({preventScroll:true});
  const sensorReady=Promise.resolve(permissionPromise).then(result=>{
   if(activeSession!==token||!opened)return;
   if(result==='granted')listenOrientation();else{headingError='missing';repaintGuidance();}
  }).catch(()=>{headingError='missing';repaintGuidance();});
  startCameraPreview(token,video);
  startLocationWatch(token);
  sensorReady.catch(()=>{});
  timeoutId=setTimeout(()=>{if(opened&&heading===null){headingError='missing';repaintGuidance();}},4800);
  heartbeatId=setInterval(()=>{if(opened)repaintGuidance();},1200);
 }
 async function startCameraPreview(token,video){
  try{
   if(!navigator.mediaDevices?.getUserMedia)throw Error('camera unsupported');
   const capture=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:'environment'}}});
   if(token!==activeSession||!opened||preview){capture.getTracks().forEach(t=>t.stop());return;}
   cameraStream=capture;video.srcObject=capture;
   await video.play().catch(()=>{});
   if(token===activeSession&&opened&&!preview){lens.classList.add('has-camera');repaintGuidance();}
  }catch{if(token===activeSession&&opened){lens.classList.remove('has-camera');repaintGuidance();}}
 }
 function startLocationWatch(token){
  if(!navigator.geolocation){locationError='blocked';repaintGuidance();return;}
  try{
   locationWatch=navigator.geolocation.watchPosition(pos=>{
    if(!opened||token!==activeSession||preview)return;
    const {latitude,longitude,accuracy}=pos.coords;
    if(!Number.isFinite(latitude)||!Number.isFinite(longitude)||!Number.isFinite(accuracy))return;
    lastPosition={lat:latitude,lon:longitude,accuracy:Math.max(0,accuracy),timestamp:Date.now()};
    locationError='';repaintGuidance();
   },error=>{if(!opened||token!==activeSession||preview)return;locationError=reportError(error);repaintGuidance();},{enableHighAccuracy:true,maximumAge:2800,timeout:11000});
  }catch{locationError='blocked';repaintGuidance();}
 }
 function listenOrientation(){
  orientationListener=event=>{
   if(!opened)return;
   // Device beta/gamma provide subtle parallax. They cannot themselves tell us north.
   if(Number.isFinite(event.beta)||Number.isFinite(event.gamma)){
    const sx=clamp((Number(event.gamma)||0)/8,-7,7);
    const sy=clamp((Number(event.beta)||0)/12,-6,6);
    if(lens){lens.style.setProperty('--lx-tilt-shift-x',sx.toFixed(2)+'px');lens.style.setProperty('--lx-tilt-shift-y',sy.toFixed(2)+'px');}
   }
   const frame=screen.orientation?.angle??window.orientation??0;
   const value=compassHeading(event,frame);
   if(value===null)return;
   heading=value;headingAt=Date.now();headingError='';repaintGuidance();
  };
  window.addEventListener('deviceorientationabsolute',orientationListener,{passive:true});
  window.addEventListener('deviceorientation',orientationListener,{passive:true});
 }
 function repaintGuidance(){
  if(!lens)return;
  const distanceValue=$('.lx-wayfinder-distance-value',lens),distanceState=$('.lx-wayfinder-distance-state',lens);
  const helper=$('.lx-wayfinder-helper-text',lens),sensor=$('.lx-wayfinder-sensor-chip',lens),disclaimer=$('.lx-wayfinder-disclaimer',lens);
  const loc=lastPosition;
  const h=Date.now()-headingAt<5500?heading:null;
  const available=loc&&Date.now()-loc.timestamp<22000;
  const d=available?geoDistance(loc.lat,loc.lon,DESTINATION.lat,DESTINATION.lon):null;
  const farEnough=available&&d>Math.max(45,loc.accuracy*2);
  const accurate=available&&loc.accuracy<=Math.min(185,Math.max(35,d*.35));
  const confident=available&&farEnough&&accurate&&Number.isFinite(h);
  distanceValue.textContent=formatDistance(d);
  // A true compass rose turns opposite to the phone heading. Its labels stay
  // upright while the target arrow uses the bearing relative to the screen.
  const rose=$('.lx-wayfinder-compass-rose',lens);
  if(Number.isFinite(h)){
   const previous=Number(rose.dataset.angle||0);
   const next=previous+signedAngle(-h-mod360(previous));
   rose.dataset.angle=String(next);
   rose.style.setProperty('--lx-rose',next+'deg');
  }
  let title='',detail='';
  if(confident){
   const bearing=geoBearing(loc.lat,loc.lon,DESTINATION.lat,DESTINATION.lon);
   const delta=signedAngle(bearing-h);
   const arrow=$('.lx-wayfinder-arrow',lens);
   const prior=Number(arrow.dataset.angle||0);
   const next=prior+signedAngle(delta-mod360(prior));
   arrow.dataset.angle=String(next);arrow.style.setProperty('--lx-bearing',next+'deg');
   title=Math.abs(delta)<22?tr('ahead'):Math.abs(delta)>150?tr('behind'):delta<0?tr('left'):tr('right');
   detail=tr('aim');
   lens.dataset.guidance='ready';
   sensor.textContent=available?tr('accuracy',{meters:Math.round(loc.accuracy)}):tr('cameraOn');
  }else if(!available){
   title=tr('calibrate');detail=locationError?tr('blockedSub'):tr('calibrateSub');lens.dataset.guidance='waiting';sensor.textContent=lens.classList.contains('has-camera')?tr('cameraOn'):tr('cameraOff');
  }else if(!farEnough){
   title=tr('near');detail=tr('nearSub');lens.dataset.guidance='waiting';sensor.textContent=tr('accuracy',{meters:Math.round(loc.accuracy)});
  }else if(!accurate){
   title=tr('poor');detail=tr('poorSub');lens.dataset.guidance='waiting';sensor.textContent=tr('accuracy',{meters:Math.round(loc.accuracy)});
  }else{
   title=headingError?tr('missing'):tr('waiting');detail=headingError?tr('missingSub'):tr('waitingSub');lens.dataset.guidance='waiting';sensor.textContent=available?tr('accuracy',{meters:Math.round(loc.accuracy)}):(lens.classList.contains('has-camera')?tr('cameraOn'):tr('cameraOff'));
  }
  if(!Number.isFinite(d))distanceValue.textContent='—';
  distanceState.textContent=title.toUpperCase();
  $('.lx-wayfinder-arrow',lens).setAttribute('aria-hidden','true');
  helper.textContent=detail;
  disclaimer.textContent=tr('disclaimer');
 }
 function closeLens(){
  if(!opened)return;
  opened=false;activeSession++;stopSensors();
  const finished=lens;lens=null;const move=morph;morph=null;move?.remove();
  if(finished){
   if(!reduced()&&typeof finished.animate==='function'){
    const a=finished.animate([{opacity:1},{opacity:0}],{duration:290,easing:'ease-in',fill:'forwards'});
    a.onfinish=()=>finished.remove();setTimeout(()=>finished.remove(),330);
   }else finished.remove();
  }
  live.inert=false;
  (guideAction||gate).focus({preventScroll:true});
 }
 function cleanupIfDeparted(){
  if(!live.classList.contains('active')&&opened)closeLens();
 }
 // The full two-section card exists before this JavaScript executes, and
 // tapping Guide Me opens the lens immediately—no expand/reconfirm step.
 if(guideAction){
  guideAction.addEventListener('click',event=>{
   event.preventDefault();event.stopPropagation();event.stopImmediatePropagation?.();openLens();
  });
 }
 document.addEventListener('keydown',event=>{
  if(!['Escape','Tab'].includes(event.key))return;
  if(event.key==='Escape'&&opened){
   event.preventDefault();event.stopImmediatePropagation();closeLens();
  }else if(event.key==='Tab'&&opened&&lens){
   const active=[...lens.querySelectorAll('button:not([hidden])')].filter(b=>b.offsetParent!==null);
   if(!active.length)return;
   const first=active[0],last=active[active.length-1];
   if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
   else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  }
 },true);
 if(gateHeading)new MutationObserver(scheduleGateCopyFit).observe(gateHeading,{childList:true,characterData:true,subtree:true});
 if(gateActionLabel)new MutationObserver(scheduleGateCopyFit).observe(gateActionLabel,{childList:true,characterData:true,subtree:true});
 if('ResizeObserver' in window)new ResizeObserver(scheduleGateCopyFit).observe(gate);
 window.addEventListener('resize',scheduleGateCopyFit,{passive:true});
 if(document.fonts?.ready)document.fonts.ready.then(scheduleGateCopyFit);
 new MutationObserver(cleanupIfDeparted).observe(live,{attributes:true,attributeFilter:['class']});
 new MutationObserver(()=>{paintCopy();scheduleGateCopyFit();}).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 new MutationObserver(paintCopy).observe($('#gate'),{childList:true,characterData:true,subtree:true});
 paintCopy();
 scheduleGateCopyFit();
 // Pure geometry only: no access to personal sensor state or external network.
 window.LXWayfinderMath=Object.freeze({geoBearing,geoDistance,signedAngle,compassHeading});
})();
