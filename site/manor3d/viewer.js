import {
  ACESFilmicToneMapping, AnimationMixer, DirectionalLight, HemisphereLight,
  LoopOnce, MOUSE, OrthographicCamera, Raycaster, Scene, TOUCH, Vector2, Vector3,
  WebGLRenderer
} from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const panel = document.querySelector("#manor-scene");
if (panel) {
  const start = () => mountManor(panel).catch(() => {
    // The illustration and both reading links already work in this state.
  });
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        observer.disconnect();
        start();
      }
    }, { rootMargin: "140px" });
    observer.observe(panel);
  } else {
    start();
  }
}

async function mountManor(panel) {
  const canvas = panel.querySelector("canvas");
  const stage = panel.querySelector(".manor-stage");
  const markers = panel.querySelector(".manor-markers");
  const reset = panel.querySelector(".manor-reset");
  const hints = panel.querySelector("#manor-instructions");
  const links = Object.fromEntries(
    [...panel.querySelectorAll("[data-landmark]")].map(link => [link.dataset.landmark, link])
  );
  const motion = matchMedia("(prefers-reduced-motion: reduce)");
  const options = { alpha: true, antialias: true, powerPreference: "low-power" };
  const context = canvas.getContext("webgl2", options);
  if (!context) return;

  const renderer = new WebGLRenderer({ ...options, canvas, context });
  let assets;
  try {
    assets = await new GLTFLoader().loadAsync(new URL("./manor-scene.glb", import.meta.url).href);
  } catch {
    renderer.dispose();
    return;
  }

  const campus = assets.scene;
  const scholar = campus.getObjectByName("Scholar");
  const landmarks = ["Library", "Telescope"].map(name => ({
    name,
    anchor: campus.getObjectByName(name + "Hotspot"),
    marker: markers.querySelector(`[data-marker="${name}"]`)
  }));
  const mixer = new AnimationMixer(scholar ?? campus);
  const waveClip = assets.animations.find(clip => clip.name === "Wave");
  const walkClip = assets.animations.find(clip => clip.name === "Walk");
  if (!scholar || !waveClip || !walkClip || landmarks.some(({anchor}) => !anchor)) {
    renderer.dispose();
    return;
  }

  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.65));
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.32;
  const world = new Scene();
  const sunlight = new DirectionalLight("#fff1dc", 2.25);
  sunlight.position.set(-5, 10, 7);
  const fill = new DirectionalLight("#cfe5ff", 0.7);
  fill.position.set(6, 5, -5);
  world.add(campus, sunlight, fill, new HemisphereLight("#f0f7ff", "#b29671", 2.15));

  const camera = new OrthographicCamera(-6, 6, 3, -3, 0.1, 80);
  const controls = new OrbitControls(camera, canvas);
  controls.enablePan = false;
  controls.enableZoom = false;
  controls.mouseButtons = { LEFT: MOUSE.ROTATE, RIGHT: null, MIDDLE: null };
  controls.touches = { ONE: TOUCH.ROTATE, TWO: null };
  controls.minPolarAngle = 0.65;
  controls.maxPolarAngle = 1.23;
  controls.minAzimuthAngle = -0.64;
  controls.maxAzimuthAngle = 1.05;
  controls.rotateSpeed = 0.53;
  resetView();
  controls.saveState();

  const wave = mixer.clipAction(waveClip).setLoop(LoopOnce, 1);
  const walk = mixer.clipAction(walkClip);
  const home = scholar.position.clone();
  const destination = home.clone();
  const direction = new Vector3();
  const projected = new Vector3();
  const ray = new Raycaster();
  const point = new Vector2();
  const visibleTargets = new Set(["Library", "Telescope", "Scholar"]);
  let frame = 0;
  let lastFrame = 0;
  let lost = false;
  let press = null;

  function resetView() {
    camera.position.set(8.2, 9.9, 16.8);
    controls.target.set(0, 1.95, 0.25);
    controls.update();
  }

  function resize() {
    const { clientWidth: width, clientHeight: height } = stage;
    if (!width || !height) return;
    const aspect = width / height;
    const span = Math.max(7.4, 10.95 / aspect) / 2;
    camera.left = -span * aspect;
    camera.right = span * aspect;
    camera.top = span;
    camera.bottom = -span;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
  }

  function invalidate() {
    if (!lost && !frame) frame = requestAnimationFrame(draw);
  }

  function draw(now) {
    frame = 0;
    const elapsed = lastFrame ? Math.min((now - lastFrame) / 1000, 0.06) : 1 / 60;
    direction.subVectors(destination, scholar.position);
    const distance = direction.length();
    if (distance > 0) {
      const step = elapsed * 1.72;
      if (distance <= step) {
        scholar.position.copy(destination);
        walk.stop();
      } else {
        scholar.position.addScaledVector(direction, step / distance);
      }
    }
    mixer.update(elapsed);
    renderer.render(world, camera);
    for (const { anchor, marker } of landmarks) {
      anchor.getWorldPosition(projected).project(camera);
      marker.hidden = Math.abs(projected.x) > 0.9 || Math.abs(projected.y) > 0.9;
      marker.style.left = `${50 + 50 * projected.x}%`;
      marker.style.top = `${50 - 50 * projected.y}%`;
    }

    lastFrame = 0;
    if (wave.isRunning() || walk.isRunning()) {
      lastFrame = now;
      invalidate();
    }
  }

  function greet() {
    destination.copy(scholar.position);
    walk.stop();
    scholar.rotation.y = controls.getAzimuthalAngle();
    wave.reset().play();
    invalidate();
  }

  function goTo(x, z) {
    destination.set(
      Math.max(-1.2, Math.min(1.7, x)),
      home.y,
      Math.max(1.5, Math.min(2.65, z))
    );
    direction.subVectors(destination, scholar.position);
    if (direction.lengthSq() < 0.008) {
      destination.copy(scholar.position);
      walk.stop();
      return;
    }
    wave.stop();
    scholar.rotation.y = Math.atan2(direction.x, direction.z);
    if (motion.matches) scholar.position.copy(destination);
    else if (!walk.isRunning()) walk.reset().play();
    invalidate();
  }

  function pick(event) {
    const x = event.clientX;
    const y = event.clientY;
    const marker = landmarks.find(({ marker }) => {
      const rect = marker.getBoundingClientRect();
      return !marker.hidden && x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
    });
    if (marker) {
      links[marker.name].click();
      return;
    }
    const bounds = canvas.getBoundingClientRect();
    point.set(2 * (x - bounds.left) / bounds.width - 1, 1 - 2 * (y - bounds.top) / bounds.height);
    ray.setFromCamera(point, camera);
    const hit = ray.intersectObject(campus, true)[0];
    if (!hit) return;
    for (let object = hit.object; object && object !== campus; object = object.parent) {
      if (visibleTargets.has(object.name)) {
        links[object.name].click();
        return;
      }
    }
    if (hit.point.y <= home.y + 0.08 && hit.point.z >= 1.32) {
      goTo(hit.point.x, hit.point.z);
    }
  }

  controls.addEventListener("change", invalidate);
  reset.addEventListener("click", () => controls.reset());
  links.Scholar.addEventListener("click", greet);
  canvas.addEventListener("pointerdown", event => {
    if (event.isPrimary && event.button === 0) press = { x: event.clientX, y: event.clientY };
    else press = null;
  });
  canvas.addEventListener("pointermove", event => {
    if (press && Math.hypot(event.clientX - press.x, event.clientY - press.y) >= 7) press = null;
  });
  canvas.addEventListener("pointercancel", () => { press = null; });
  canvas.addEventListener("pointerup", event => {
    if (press && Math.hypot(event.clientX - press.x, event.clientY - press.y) < 7) pick(event);
    press = null;
  });
  const keyMoves = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  canvas.addEventListener("keydown", event => {
    if (!Object.hasOwn(keyMoves, event.key)) return;
    event.preventDefault();
    const [x, z] = keyMoves[event.key];
    goTo(scholar.position.x + 0.37 * x, scholar.position.z + 0.37 * z);
  });
  const observer = new ResizeObserver(() => {
    resize();
    invalidate();
  });
  canvas.addEventListener("webglcontextlost", () => {
    lost = true;
    cancelAnimationFrame(frame);
    observer.disconnect();
    controls.dispose();
    delete panel.dataset.ready;
    canvas.tabIndex = -1;
    canvas.setAttribute("aria-hidden", "true");
    for (const element of [markers, links.Scholar, hints, reset]) element.hidden = true;
  }, { once: true });

  resize();
  draw(performance.now());
  observer.observe(stage);
  panel.dataset.ready = "";
  canvas.tabIndex = 0;
  canvas.removeAttribute("aria-hidden");
  for (const element of [markers, links.Scholar, hints, reset]) element.hidden = false;
  if (!motion.matches) {
    wave.play();
    invalidate();
  }
}
