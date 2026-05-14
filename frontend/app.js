const ws = new WebSocket(`ws://${location.host}/ws`);
const alertLog = document.getElementById('alert-log');
const videoWrapper = document.getElementById('video-wrapper');
const statusCam = document.getElementById('status-cam');
const statusBt  = document.getElementById('status-bt');
const statusGpu = document.getElementById('status-gpu');

const ALERT_ICONS = {
  human_in_fire: '⚠ Human in fire zone',
  flame:         '🔥 Flame detected',
  obstruction:   '🟡 Obstruction ahead',
};

let audioCtx = null;
let userInteracted = false;
document.addEventListener('click', () => { userInteracted = true; }, { once: true });

function beep(freq = 880, duration = 0.2) {
  if (!userInteracted) return;
  if (!audioCtx) audioCtx = new AudioContext();
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
  osc.start();
  osc.stop(audioCtx.currentTime + duration);
}

function addAlert(type, conf) {
  const li = document.createElement('li');
  li.className = `alert-${type}`;
  const text = ALERT_ICONS[type] || type;
  const time = new Date().toLocaleTimeString();
  li.textContent = `${text} (${Math.round(conf * 100)}%) — ${time}`;
  alertLog.prepend(li);

  // Cap log at 50 entries
  while (alertLog.children.length > 50) alertLog.removeChild(alertLog.lastChild);

  // Visual border effect
  videoWrapper.className = type === 'human_in_fire' ? 'alert-human' : type === 'flame' ? 'alert-fire' : '';
  if (type !== 'obstruction') beep(type === 'human_in_fire' ? 1200 : 880);
  setTimeout(() => { videoWrapper.className = ''; }, 2000);
}

function updateStatus(data) {
  setStatus(statusCam, data.camera, 'CAM');
  setStatus(statusBt,  data.bluetooth, 'BT');
  statusGpu.textContent = `MODE: ${data.gpu ? 'GPU' : 'CPU'}`;
  statusGpu.className = 'status-badge ok';
}

function setStatus(el, ok, label) {
  el.textContent = `${label}: ${ok ? 'OK' : 'OFF'}`;
  el.className = `status-badge ${ok ? 'ok' : 'fail'}`;
}

ws.onmessage = (ev) => {
  const data = JSON.parse(ev.data);
  if (data.event === 'alert') addAlert(data.type, data.conf);
  if (data.event === 'status') updateStatus(data);
};

ws.onclose = () => setStatus(statusCam, false, 'CAM');

function sendCmd(cmd) { if (ws.readyState === 1) ws.send(JSON.stringify({ cmd })); }

// Button controls
document.querySelectorAll('#dpad button').forEach(btn => {
  btn.addEventListener('mousedown', () => { btn.classList.add('pressed'); sendCmd(btn.dataset.cmd); });
  btn.addEventListener('mouseup',   () => { btn.classList.remove('pressed'); sendCmd('S'); });
  btn.addEventListener('mouseleave',() => { btn.classList.remove('pressed'); sendCmd('S'); });
});

// Keyboard controls
const KEY_MAP = { KeyW: 'F', ArrowUp: 'F', KeyS: 'B', ArrowDown: 'B',
                  KeyA: 'L', ArrowLeft: 'L', KeyD: 'R', ArrowRight: 'R', Space: 'S' };
const held = new Set();
document.addEventListener('keydown', e => {
  const cmd = KEY_MAP[e.code];
  if (cmd && !held.has(e.code)) { held.add(e.code); sendCmd(cmd); e.preventDefault(); }
});
document.addEventListener('keyup', e => {
  if (KEY_MAP[e.code]) { held.delete(e.code); sendCmd('S'); }
});
