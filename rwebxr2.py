# RoverWEBXR.py  -- fixed global handling in api_command
# Based on your uploaded file. See original upload for reference. :contentReference[oaicite:1]{index=1}

import RPi.GPIO as GPIO
import time
import threading
import subprocess
from flask import Flask, render_template_string, request, jsonify

# --------------------------
# GPIO CONFIG (BOARD MODE)
# --------------------------
GPIO.setmode(GPIO.BOARD)

IN1 = 29
IN2 = 31
IN3 = 35
IN4 = 37
ENA = 33
ENB = 32

TRIG = 16
ECHO = 18

# Setup motor pins
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)
GPIO.setup(ENA, GPIO.OUT)
GPIO.setup(ENB, GPIO.OUT)

# Setup ultrasonics
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# PWM
pwmA = GPIO.PWM(ENA, 1000)
pwmB = GPIO.PWM(ENB, 1000)
pwmA.start(70)
pwmB.start(70)

motor_lock = threading.Lock()
current_action = "stop"
current_speed = 70
running = True
last_distance = 0

# --------------------------
# ULTRASONIC FUNCTION
# --------------------------
def get_distance():
    try:
        GPIO.output(TRIG, False)
        time.sleep(0.02)

        GPIO.output(TRIG, True)
        time.sleep(0.00001)
        GPIO.output(TRIG, False)

        pulse_start = time.time()
        pulse_end = time.time()

        timeout = time.time() + 0.1  # 100ms timeout

        while GPIO.input(ECHO) == 0:
            pulse_start = time.time()
            if time.time() > timeout:
                return 999

        while GPIO.input(ECHO) == 1:
            pulse_end = time.time()
            if time.time() > timeout:
                return 999

        duration = pulse_end - pulse_start
        distance = round(duration * 17150, 2)
        return distance
    except:
        return 999

# --------------------------
# MOTOR FUNCTIONS
# --------------------------
def stop():
    global current_action
    with motor_lock:
        GPIO.output(IN1, False)
        GPIO.output(IN2, False)
        GPIO.output(IN3, False)
        GPIO.output(IN4, False)
        current_action = "stop"

def forward():
    global current_action
    with motor_lock:
        GPIO.output(IN1, False)
        GPIO.output(IN2, True)
        GPIO.output(IN3, False)
        GPIO.output(IN4, True)
        current_action = "forward"

def backward():
    global current_action
    with motor_lock:
        GPIO.output(IN1, True)
        GPIO.output(IN2, False)
        GPIO.output(IN3, True)
        GPIO.output(IN4, False)
        current_action = "backward"

def left():
    global current_action
    with motor_lock:
        GPIO.output(IN1, False)
        GPIO.output(IN2, True)
        GPIO.output(IN3, True)
        GPIO.output(IN4, False)
        current_action = "left"

def right():
    global current_action
    with motor_lock:
        GPIO.output(IN1, True)
        GPIO.output(IN2, False)
        GPIO.output(IN3, False)
        GPIO.output(IN4, True)
        current_action = "right"

def set_speed(speed):
    global current_speed
    current_speed = max(0, min(100, speed))
    pwmA.ChangeDutyCycle(current_speed)
    pwmB.ChangeDutyCycle(current_speed)

# --------------------------
# SHUTDOWN FUNCTION
# --------------------------
def safe_shutdown():
    """Safely shutdown the Raspberry Pi"""
    global running
    print("=" * 50)
    print("🔴 SAFE SHUTDOWN INITIATED")
    print("=" * 50)
    
    # Stop motors
    running = False
    stop()
    time.sleep(0.5)
    
    # Stop PWM
    pwmA.stop()
    pwmB.stop()
    
    # Cleanup GPIO
    GPIO.cleanup()
    print("✅ GPIO cleaned")
    print("💾 Syncing filesystems...")
    
    # Sync filesystems to prevent corruption
    subprocess.run(['sync'], check=False)
    time.sleep(1)
    
    print("🔌 Shutting down Raspberry Pi...")
    # Initiate shutdown
    subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=False)

# --------------------------
# CAR SAFETY THREAD (AUTO-STOP)
# --------------------------
def safety_loop():
    global running, last_distance
    while running:
        dist = get_distance()
        last_distance = dist

        # Auto-stop logic when object is too close
        if current_action == "forward" and dist < 20:
            stop()
            print("AUTO-STOP: Obstacle detected at", dist, "cm")

        time.sleep(0.1)

# --------------------------
# WEB UI TEMPLATE (REPLACED WITH WEBXR PAGE)
# --------------------------
# This HTML implements the WebXR remote (Option A) and uses your existing /api endpoints.
HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>WebXR RC Remote — Option A (Smooth Locomotion)</title>
  <style>
    html,body{height:100%;margin:0;overflow:hidden;font-family:system-ui,Arial;}
    #overlayHUD {
      position:absolute; left:8px; top:8px; z-index:10;
      background:rgba(0,0,0,0.35); color:#fff; padding:8px 10px; border-radius:8px;
      max-width:320px; font-size:13px;
    }
    #overlayHUD b{display:inline-block; width:70px;}
    button.small{margin:6px 4px 0 0;padding:6px 8px;border-radius:6px;border:none;cursor:pointer;}
  </style>
</head>
<body>
  <div id="overlayHUD">
    <div style="font-weight:600">RC Remote — Smooth Locomotion</div>
    <div><b>Action:</b> <span id="action">STOP</span></div>
    <div><b>Speed:</b> <span id="speed">--</span>%</div>
    <div><b>Distance:</b> <span id="distance">--</span> cm</div>
    <div style="margin-top:6px">
      <button id="btnCam" class="small">Toggle Camera</button>
      <button id="btnTest" class="small">Test API</button>
      <button id="btnStop" class="small">STOP</button>
    </div>
  </div>

<script type="module">
/* NOTE:
   This client JS is the same WebXR page code we discussed.
   It calls the Flask endpoints served by this same server:
     POST /api/command  { command: "forward"|"backward"|"left"|"right"|"stop"|"on"|"off" }
     POST /api/speed    { speed: <0-100> }
     GET  /api/status
     POST /api/shutdown
*/
import * as THREE from 'https://unpkg.com/three@0.154.0/build/three.module.js';
import { OrbitControls } from 'https://unpkg.com/three@0.154.0/examples/jsm/controls/OrbitControls.js';
import { VRButton } from 'https://unpkg.com/three@0.154.0/examples/jsm/webxr/VRButton.js';
import { XRControllerModelFactory } from 'https://unpkg.com/three@0.154.0/examples/jsm/webxr/XRControllerModelFactory.js';

const API_ROOT = window.location.origin || 'http://127.0.0.1:5000';
const API = {
  command: API_ROOT + '/api/command',
  speed:   API_ROOT + '/api/speed',
  status:  API_ROOT + '/api/status',
  shutdown: API_ROOT + '/api/shutdown'
};

async function sendCommand(action){
  try{
    await fetch(API.command, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({command:action})});
    document.getElementById('action').textContent = action.toUpperCase();
  }catch(e){ console.warn('sendCommand failed', e); }
}
async function setSpeed(value){
  try{
    await fetch(API.speed, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({speed:value})});
    document.getElementById('speed').textContent = value;
  }catch(e){ console.warn('setSpeed failed', e); }
}
async function pollStatusOnce(){
  try{
    const r = await fetch(API.status);
    if(!r.ok) return;
    const j = await r.json();
    document.getElementById('action').textContent = (j.action||'--').toUpperCase();
    document.getElementById('speed').textContent = (j.speed==null ? '--' : j.speed);
    document.getElementById('distance').textContent = (j.distance==null ? '--' : j.distance);
  }catch(e){}
}

document.getElementById('btnTest').addEventListener('click', async ()=>{ await pollStatusOnce(); alert('Polled status (check HUD).'); });
document.getElementById('btnStop').addEventListener('click', ()=> sendCommand('stop'));

let camera, scene, renderer, clock;
let playerRig;
let cube;
const raycaster = new THREE.Raycaster();
const grabState = {0:null,1:null};
let lastSentAction = 'stop';
let currentSpeed = 70;
let cameraStreamActive = false;
let videoEl = null, videoTexture = null, cameraPlane = null;

init();
animate();

function init(){
  renderer = new THREE.WebGLRenderer({antialias:true});
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.xr.enabled = true;
  document.body.appendChild(renderer.domElement);
  document.body.appendChild(VRButton.createButton(renderer));

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x8899aa);
  camera = new THREE.PerspectiveCamera(70, window.innerWidth/window.innerHeight, 0.05, 200);
  playerRig = new THREE.Group();
  playerRig.position.set(0,0,0);
  playerRig.add(camera);
  scene.add(playerRig);

  const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1.0); scene.add(hemi);
  const dir = new THREE.DirectionalLight(0xffffff, 0.6); dir.position.set(3,10,10); scene.add(dir);

  const floor = new THREE.Mesh(new THREE.PlaneGeometry(10,10), new THREE.MeshStandardMaterial({color:0x222233, roughness:0.95}));
  floor.rotation.x = -Math.PI/2; floor.receiveShadow = true; scene.add(floor);

  cube = new THREE.Mesh(new THREE.BoxGeometry(0.6,0.6,0.6), new THREE.MeshStandardMaterial({color:0x44aa88}));
  cube.position.set(0,1.2,-1); cube.userData.grabbable = true; scene.add(cube);
  for(let i=0;i<6;i++){
    const s = new THREE.Mesh(new THREE.SphereGeometry(0.08,16,12), new THREE.MeshStandardMaterial({color:new THREE.Color().setHSL(i/6,0.7,0.5)}));
    s.position.set(Math.cos(i/6*Math.PI*2)*0.9, 1.05 + (i%2)*0.2, -1 + Math.sin(i/6*Math.PI*2)*0.5);
    s.userData.grabbable = true; scene.add(s);
  }

  new OrbitControls(camera, renderer.domElement).target.set(0,1.2,-1);

  clock = new THREE.Clock();

  setupControllers();
  createCameraPlane();
  makeUIPanel();

  window.addEventListener('resize', onWindowResize);
  window.addEventListener('beforeunload', ()=> sendCommand('stop'));
  setInterval(pollStatusOnce, 600);
}

function onWindowResize(){ camera.aspect = window.innerWidth/window.innerHeight; camera.updateProjectionMatrix(); renderer.setSize(window.innerWidth, window.innerHeight); }

function createCameraPlane(){
  videoEl = document.createElement('video');
  videoEl.autoplay = true; videoEl.playsInline = true; videoEl.muted = true;
  videoTexture = new THREE.VideoTexture(videoEl);
  videoTexture.minFilter = THREE.LinearFilter; videoTexture.magFilter = THREE.LinearFilter; videoTexture.format = THREE.RGBAFormat;
  const mat = new THREE.MeshBasicMaterial({map: videoTexture, side: THREE.DoubleSide, toneMapped:false});
  cameraPlane = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 0.9), mat);
  cameraPlane.position.set(0, 1.5, -1.2);
  cameraPlane.visible = false;
  scene.add(cameraPlane);
  document.getElementById('btnCam').addEventListener('click', toggleCameraStream);
}

async function toggleCameraStream(){
  if(!cameraStreamActive){
    try{
      const stream = await navigator.mediaDevices.getUserMedia({video: { facingMode: "environment" }, audio:false});
      videoEl.srcObject = stream;
      await videoEl.play();
      cameraPlane.visible = true;
      cameraStreamActive = true;
    }catch(e){
      alert('Camera access denied or unavailable. On Quest use Oculus Browser and allow camera if supported.');
      console.warn('getUserMedia failed', e);
    }
  } else {
    const s = videoEl.srcObject;
    if(s && s.getTracks) s.getTracks().forEach(t=>t.stop());
    videoEl.srcObject = null; cameraPlane.visible = false; cameraStreamActive = false;
  }
}

function setupControllers(){
  const factory = new XRControllerModelFactory();
  for(let i=0;i<=1;i++){
    const controller = renderer.xr.getController(i);
    controller.userData.index = i;
    controller.addEventListener('selectstart', onSelectStart);
    controller.addEventListener('selectend', onSelectEnd);
    controller.addEventListener('squeezestart', onSqueezeStart);
    controller.addEventListener('squeezeend', onSqueezeEnd);
    scene.add(controller);
    const geometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,0,0), new THREE.Vector3(0,0,-1)]);
    const line = new THREE.Line(geometry, new THREE.LineBasicMaterial({}));
    line.name = 'ray'; line.scale.z = 10; controller.add(line);
    const pointer = new THREE.Mesh(new THREE.SphereGeometry(0.01,8,8), new THREE.MeshBasicMaterial({}));
    pointer.name='pointer'; pointer.visible=false; controller.add(pointer);
    const grip = renderer.xr.getControllerGrip(i);
    grip.add(factory.createControllerModel(grip));
    scene.add(grip);
  }
}

function pulse(controller, duration=30, intensity=0.6){
  const gp = controller.gamepad || (controller.inputSource && controller.inputSource.gamepad);
  if(!gp) return;
  try{
    if(gp.hapticActuators && gp.hapticActuators[0]) gp.hapticActuators[0].pulse(intensity, duration);
    else if(gp.vibrationActuator && typeof gp.vibrationActuator.playEffect === 'function') gp.vibrationActuator.playEffect('dual-rumble', {duration, strongMagnitude:intensity, weakMagnitude:intensity});
  }catch(e){}
}

function onSelectStart(event){
  const controller = event.target;
  tryInteractOrGrab(controller);
  pulse(controller, 30, 0.6);
}
function onSelectEnd(event){
  const controller = event.target;
  releaseGrab(controller);
  pulse(controller, 20, 0.6);
}
function onSqueezeStart(event){
  const controller = event.target;
  tryGrab(controller);
  if(controller.userData.index === 1){
    currentSpeed = Math.max(10, currentSpeed - 10);
    setSpeed(currentSpeed);
    pulse(controller, 25, 0.5);
  }
}
function onSqueezeEnd(event){
  const controller = event.target;
  releaseGrab(controller);
}

function tryGrab(controller){
  const origin = new THREE.Vector3(); controller.getWorldPosition(origin);
  const dir = new THREE.Vector3(0,0,-1).applyQuaternion(controller.quaternion).normalize();
  raycaster.set(origin, dir);
  const hits = raycaster.intersectObjects(scene.children, true).filter(i=>i.object.userData && i.object.userData.grabbable);
  if(hits.length>0){
    const obj = hits[0].object;
    controller.userData.prevParent = obj.parent;
    controller.attach(obj);
    grabState[controller.userData.index] = obj;
  }
}
function releaseGrab(controller){
  const grabbed = grabState[controller.userData.index];
  if(!grabbed) return;
  const worldPos = new THREE.Vector3(), worldQuat = new THREE.Quaternion(), worldScale = new THREE.Vector3();
  grabbed.getWorldPosition(worldPos); grabbed.getWorldQuaternion(worldQuat); grabbed.getWorldScale(worldScale);
  scene.add(grabbed);
  grabbed.position.copy(worldPos); grabbed.quaternion.copy(worldQuat); grabbed.scale.copy(worldScale);
  grabState[controller.userData.index] = null;
}

function tryInteractOrGrab(controller){
  const origin = new THREE.Vector3(); controller.getWorldPosition(origin);
  const dir = new THREE.Vector3(0,0,-1).applyQuaternion(controller.quaternion).normalize();
  raycaster.set(origin, dir);
  const hits = raycaster.intersectObjects(scene.children, true);
  if(hits.length>0){
    const first = hits[0].object;
    if(first.userData && first.userData.uiAction){
      handleUIAction(first.userData.uiAction);
      return;
    }
  }
  tryGrab(controller);
}

function handleUIAction(action){
  switch(action){
    case 'toggleCamera': toggleCameraStream(); break;
    case 'enterARVR': toggleXRMode(); break;
    case 'speedLow': currentSpeed = 30; setSpeed(currentSpeed); break;
    case 'speedMed': currentSpeed = 70; setSpeed(currentSpeed); break;
    case 'speedHigh': currentSpeed = 100; setSpeed(currentSpeed); break;
    case 'stop': sendCommand('stop'); break;
    case 'togglePower': togglePower(); break;
    default: console.log('ui action', action);
  }
}
function togglePower(){
  const cur = (document.getElementById('action').textContent || '').toLowerCase();
  if(cur === 'on') sendCommand('off'); else sendCommand('on');
}
function toggleXRMode(){
  const session = renderer.xr.getSession && renderer.xr.getSession();
  if(session) session.end();
  else alert('Press the Enter VR button to start VR. For AR passthrough we show camera plane.');
}

const hoverList = [];
function updateHover(controller){
  const origin = new THREE.Vector3(); controller.getWorldPosition(origin);
  const dir = new THREE.Vector3(0,0,-1).applyQuaternion(controller.quaternion).normalize();
  raycaster.set(origin, dir);
  const hits = raycaster.intersectObjects(scene.children, true).filter(i => i.object.userData && i.object.userData.grabbable || (i.object.userData && i.object.userData.uiAction));
  const pointer = controller.getObjectByName('pointer');
  if(pointer){
    if(hits.length>0){
      pointer.visible = true;
      pointer.position.copy(controller.worldToLocal(hits[0].point.clone()));
      const target = hits[0].object;
      if(!hoverList.includes(target)) hoverList.push(target);
      if(target.scale) target.scale.setScalar(1.05);
    } else {
      pointer.visible = false;
    }
  }
}
function clearHover(){ while(hoverList.length){ const o = hoverList.pop(); if(o && o.scale) o.scale.setScalar(1.0); } }

function makeUIPanel(){
  const w = 0.6, h = 0.36;
  const canvas = document.createElement('canvas');
  canvas.width = 1024; canvas.height = 600;
  const ctx = canvas.getContext('2d');
  function redraw(){
    ctx.fillStyle = '#0b1220'; ctx.fillRect(0,0,canvas.width,canvas.height);
    ctx.fillStyle = 'white'; ctx.font = '36px sans-serif'; ctx.fillText('RC Telemetry', 36, 64);
    ctx.font = '22px sans-serif'; ctx.fillStyle = '#bbbbbb';
    ctx.fillText('Action: ' + (document.getElementById('action').textContent || '--'), 36, 120);
    ctx.fillText('Speed: ' + (document.getElementById('speed').textContent || '--') , 36, 160);
    ctx.fillText('Distance: ' + (document.getElementById('distance').textContent || '--') + ' cm', 36, 200);
    ctx.fillStyle = '#335577'; ctx.fillRect(36, 240, 220, 60); ctx.fillStyle='white'; ctx.fillText('Toggle Camera', 52, 282);
    ctx.fillStyle = '#335577'; ctx.fillRect(280, 240, 120, 60); ctx.fillStyle='white'; ctx.fillText('STOP', 300, 282);
    ctx.fillStyle = '#335577'; ctx.fillRect(420, 240, 120, 60); ctx.fillStyle='white'; ctx.fillText('AR/VR', 440, 282);
    ctx.fillStyle = '#446633'; ctx.fillRect(36, 320, 120, 48); ctx.fillStyle='white'; ctx.fillText('Low', 64, 354);
    ctx.fillStyle = '#446633'; ctx.fillRect(168, 320, 120, 48); ctx.fillStyle='white'; ctx.fillText('Med', 200, 354);
    ctx.fillStyle = '#446633'; ctx.fillRect(300, 320, 120, 48); ctx.fillStyle='white'; ctx.fillText('High', 332, 354);
  }
  redraw();
  const texture = new THREE.CanvasTexture(canvas);
  const mat = new THREE.MeshBasicMaterial({map:texture, side:THREE.DoubleSide});
  const panel = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
  panel.position.set(0.9, 1.4, -0.8);
  panel.userData.ui = true;
  function makeHit(x,y,ww,hh, actionName){
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(ww/w * w, hh/h * h), new THREE.MeshBasicMaterial({visible:false}));
    const cx = (x + ww/2 - canvas.width/2) / canvas.width * w;
    const cy = -(y + hh/2 - canvas.height/2) / canvas.height * h;
    mesh.position.set(cx, cy, 0.01);
    mesh.userData.uiAction = actionName;
    panel.add(mesh);
  }
  makeHit(36, 240, 220, 60, 'toggleCamera');
  makeHit(280, 240, 120, 60, 'stop');
  makeHit(420, 240, 120, 60, 'enterARVR');
  makeHit(36, 320, 120, 48, 'speedLow');
  makeHit(168, 320, 120, 48, 'speedMed');
  makeHit(300, 320, 120, 48, 'speedHigh');
  setInterval(()=>{ redraw(); texture.needsUpdate = true; }, 600);
  scene.add(panel);
}

function getGamepadForController(i){
  const c = renderer.xr.getController(i);
  return c ? (c.gamepad || (c.inputSource && c.inputSource.gamepad)) : null;
}
function mapAxesToAction(x,y){
  const dead = 0.35;
  if(Math.abs(y) > dead){ return y < 0 ? 'forward' : 'backward'; }
  if(Math.abs(x) > dead){ return x < 0 ? 'left' : 'right'; }
  return 'stop';
}
const MOVE_SPEED = 1.6;
function pollGamepadsAndApply(dt){
  const gpL = getGamepadForController(0);
  if(gpL && gpL.axes && gpL.axes.length >= 2){
    const lx = gpL.axes.length > 2 ? gpL.axes[2] : gpL.axes[0];
    const ly = gpL.axes.length > 3 ? gpL.axes[3] : gpL.axes[1];
    const forward = -ly;
    const strafe = lx;
    const dead = 0.15;
    const f = Math.abs(forward) > dead ? forward : 0;
    const s = Math.abs(strafe) > dead ? strafe : 0;
    const euler = new THREE.Euler().setFromQuaternion(camera.quaternion, 'YXZ');
    const yaw = euler.y;
    const forwardVec = new THREE.Vector3(0,0,-1).applyAxisAngle(new THREE.Vector3(0,1,0), yaw).multiplyScalar(f * MOVE_SPEED * dt);
    const strafeVec = new THREE.Vector3(1,0,0).applyAxisAngle(new THREE.Vector3(0,1,0), yaw).multiplyScalar(s * MOVE_SPEED * dt);
    playerRig.position.add(forwardVec).add(strafeVec);
  }

  const gpR = getGamepadForController(1);
  if(gpR && gpR.axes){
    const rx = gpR.axes.length > 2 ? gpR.axes[2] : gpR.axes[0];
    const ry = gpR.axes.length > 3 ? gpR.axes[3] : gpR.axes[1];
    const action = mapAxesToAction(rx, ry);
    if(action !== lastSentAction){ sendCommand(action); lastSentAction = action; }
    if(gpR.buttons){
      if((gpR.buttons[1] && gpR.buttons[1].pressed) || (gpR.buttons[3] && gpR.buttons[3].pressed)){ sendCommand('stop'); }
      if(gpR.buttons[2] && gpR.buttons[2].pressed){ if(!gpR._lastB) { togglePower(); } gpR._lastB = true; } else { gpR._lastB = false; }
      if(gpR.buttons[0] && gpR.buttons[0].pressed){ currentSpeed = Math.min(100, currentSpeed + 0.5); setSpeed(Math.round(currentSpeed)); }
    }
  }
}

function animate(){ renderer.setAnimationLoop(render); }
function render(){
  const dt = Math.min(0.05, clock.getDelta());
  if(cube && !Object.values(grabState).includes(cube)){
    const t = clock.getElapsedTime();
    cube.rotation.x = 0.3 * Math.sin(t * 0.9);
    cube.rotation.y += 0.01;
    cube.position.y = 1.15 + Math.sin(t * 1.2) * 0.05;
  }
  clearHover();
  for(let i=0;i<=1;i++){ const c = renderer.xr.getController(i); if(c) updateHover(c); }
  pollGamepadsAndApply(dt);
  renderer.render(scene, camera);
}
</script>
</body>
</html>
"""

# --------------------------
# FLASK WEB SERVER (unchanged endpoints)
# --------------------------
app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/api/command", methods=["POST"])
def api_command():
    # FIXED: declare global once at top (required before assignments)
    global current_action
    data = request.get_json()
    cmd = data.get("command", "stop")

    # Use a single motor_lock section to keep operations atomic and thread-safe
    with motor_lock:
        if cmd == "forward":
            forward()
        elif cmd == "backward":
            backward()
        elif cmd == "left":
            left()
        elif cmd == "right":
            right()
        elif cmd == "stop":
            stop()
        elif cmd == "on":
            # user-defined 'on' — set action to on
            current_action = 'on'
        elif cmd == "off":
            current_action = 'off'
            stop()
        else:
            # unknown command -> safe fallback
            stop()

    return jsonify({"status": "ok", "action": current_action})

@app.route("/api/speed", methods=["POST"])
def api_speed():
    data = request.get_json()
    speed = data.get("speed", 70)
    set_speed(speed)
    return jsonify({"status": "ok", "speed": current_speed})

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify({
        "action": current_action,
        "speed": current_speed,
        "distance": last_distance
    })

@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    """Endpoint to safely shutdown the Raspberry Pi"""
    print("\n" + "=" * 50)
    print("🔴 SHUTDOWN REQUEST RECEIVED FROM WEB UI")
    print("=" * 50)
    
    # Run shutdown in a separate thread to allow response to be sent
    shutdown_thread = threading.Thread(target=safe_shutdown, daemon=False)
    shutdown_thread.start()
    
    return jsonify({
        "status": "shutdown_initiated",
        "message": "Raspberry Pi is shutting down safely..."
    })

# --------------------------
# MAIN ENTRY
# --------------------------
if __name__ == "__main__":
    try:
        threading.Thread(target=safety_loop, daemon=True).start()
        print("=" * 50)
        print("🚗 RC Car Controller Started!")
        print("=" * 50)
        print("Access the UI at: http://<your-pi-ip>:5000")
        print("=" * 50)
        app.run(host="0.0.0.0", port=5000, debug=False)

    except KeyboardInterrupt:
        pass

    finally:
        running = False
        stop()
        pwmA.stop()
        pwmB.stop()
        GPIO.cleanup()
        print("\n✅ EXIT: GPIO cleaned")
