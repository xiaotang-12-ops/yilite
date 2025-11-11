from pathlib import Path

html = """<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>装配说明生成器 · 批处理增强版</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1220;
      --panel: rgba(17, 25, 40, 0.82);
      --border: rgba(148, 163, 184, 0.16);
      --fg: #f8fafc;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --accent-2: #a855f7;
      font-family: \"Segoe UI\", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(900px 800px at 75% 15%, rgba(56,189,248,0.12), transparent), var(--bg);
      color: var(--fg);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      padding: 16px 24px;
      border-bottom: 1px solid var(--border);
      backdrop-filter: blur(16px);
      background: rgba(10, 17, 32, 0.85);
      display: flex;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 600; }
    .tagline { color: var(--muted); font-size: 14px; margin-top: 4px; }
    main {
      flex: 1;
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr) 360px;
      gap: 16px;
      padding: 16px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .panel h2 {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    #viewer {
      position: relative;
      border-radius: 18px;
      overflow: hidden;
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--border);
      min-height: 60vh;
    }
    canvas { display: block; }
    label span { display: block; font-size: 13px; color: var(--muted); margin-bottom: 6px; }
    input[type=file], button, textarea, input[type=range] {
      width: 100%;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border);
      color: var(--fg);
      padding: 8px 10px;
      border-radius: 12px;
      font-size: 14px;
      font-family: inherit;
    }
    button { cursor: pointer; transition: background 0.2s ease; }
    button:hover { background: rgba(56,189,248,0.16); }
    .muted { color: var(--muted); font-size: 13px; }
    .flex { display: flex; gap: 10px; }
    .flex button { flex: 1; }
    .list { flex: 1; overflow: auto; display: grid; gap: 8px; font-size: 13px; }
    .list-item {
      border: 1px solid rgba(148, 163, 184, 0.18);
      border-radius: 12px;
      padding: 10px 12px;
      background: rgba(15, 23, 42, 0.72);
      display: grid;
      gap: 6px;
    }
    .badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 999px; font-size: 12px; }
    .badge.assembly { background: rgba(56,189,248,0.18); color: #22d3ee; }
    .badge.component { background: rgba(168,85,247,0.18); color: #a855f7; }
    .btn-line { display: flex; gap: 8px; }
    .btn-line button { flex: 1; }
    .steps { flex: 1; overflow: auto; display: grid; gap: 12px; }
    .step-item {
      border-radius: 12px;
      border: 1px solid rgba(56,189,248,0.22);
      background: rgba(8, 19, 40, 0.8);
      padding: 12px 14px;
    }
    .step-item h3 { margin: 0 0 6px 0; font-size: 14px; display: flex; justify-content: space-between; align-items: center; }
    .step-item small { color: var(--muted); font-weight: 500; }
    .step-body { font-size: 13px; line-height: 1.4; color: #cbd5f5; white-space: pre-line; }
    #status {
      position: absolute;
      top: 12px;
      left: 12px;
      padding: 8px 12px;
      border-radius: 10px;
      background: rgba(15, 23, 42, 0.78);
      border: 1px solid rgba(56,189,248,0.35);
      font-size: 13px;
    }
    textarea { height: 120px; resize: vertical; }
    .log-area {
      margin-top: 12px;
      width: 100%;
      height: 140px;
      background: rgba(15, 23, 42, 0.65);
      border: 1px solid var(--border);
      border-radius: 12px;
      color: var(--muted);
      padding: 10px 12px;
      resize: vertical;
      font-size: 13px;
    }
    .log-area::placeholder { color: rgba(148,163,184,0.6); }
    @media (max-width: 1200px) { main { grid-template-columns: 1fr; } }
  </style>
  <script src=\"./vendor/pdfjs/pdf.min.js\"></script>
  <script>
    window.pdfjsLib = window.pdfjsLib || window['pdfjs-dist/build/pdf'] || window.pdfjsDistBuildPdf || window.pdfjsLibDefault || null;
    if (window.pdfjsLib) {
      window.pdfjsLib.GlobalWorkerOptions.workerSrc = './vendor/pdfjs/pdf.worker.min.js';
    } else {
      console.error('pdf.js 加载失败');
    }
  </script>
  <script type=\"importmap\">
    {
      \"imports\": {
        \"three\": \"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js\",
        \"three/examples/jsm/\": \"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/\"
      }
    }
  </script>
</head>
<body>
  <header>
    <div>
      <h1>装配说明生成器 · 批量版</h1>
      <div class=\"tagline\">批量上传 3D & CAD，自动解析 BOM，并调用大模型生成装配说明。</div>
    </div>
    <div class=\"flex\" style=\"align-items:center;\">
      <input id=\"inputApiKey\" type=\"password\" placeholder=\"DeepSeek API Key\" style=\"min-width:280px;\" />
      <button id=\"btnTestLLM\" style=\"width:140px;\">测试连通</button>
    </div>
  </header>

  <main>
    <section class=\"panel\" style=\"min-height:60vh;\">
      <h2>数据输入</h2>
      <label>
        <span>批量导入 glTF / GLB（文件名用于区分总装 vs 零件，可多选）</span>
        <input id=\"fileModels\" type=\"file\" accept=\".glb,.gltf\" multiple />
      </label>
      <div class=\"muted\">识别规则：文件名包含 <code>总图</code>/<code>assembly</code>/<code>final</code>/<code>总成</code> 视为整机，其余视为零件。</div>
      <div class=\"list\" id=\"modelList\"></div>
      <label>
        <span>模型爆炸</span>
        <input id=\"explodeSlider\" type=\"range\" min=\"0\" max=\"1\" step=\"0.01\" value=\"0\" />
      </label>
      <div class=\"btn-line\">
        <button id=\"btnClearModels\">清空模型</button>
        <button id=\"btnDownloadModelManifest\">导出模型清单</button>
      </div>

      <label>
        <span>批量导入 PDF 工程图（自动解析 BOM）</span>
        <input id=\"filePdfs\" type=\"file\" accept=\".pdf\" multiple />
      </label>
      <div class=\"btn-line\">
        <button id=\"btnDownloadBom\">下载合并 BOM (JSON)</button>
        <button id=\"btnResetBom\">清空 BOM</button>
      </div>
      <div class=\"muted\" id=\"bomSummary\">尚未解析 BOM。</div>
      <textarea id=\"log\" class=\"log-area\" readonly placeholder=\"解析日志将在此显示\"></textarea>
    </section>

    <section class=\"panel\" id=\"viewer\">
      <div id=\"status\">等待模型加载...</div>
    </section>

    <section class=\"panel\" style=\"min-height:60vh;\">
      <h2>装配步骤 & LLM</h2>
      <div class=\"muted\">基于 BOM + 3D 零件列表自动生成说明，可手动调整。</div>
      <div class=\"btn-line\">
        <button id=\"btnGenerateSteps\">根据 BOM 生成步骤</button>
        <button id=\"btnLLM\">调用 DeepSeek 大模型润色</button>
      </div>
      <div class=\"muted\" id=\"llmStatus\">大模型尚未调用。</div>
      <div class=\"steps\" id=\"stepList\"></div>
      <textarea id=\"llmOutput\" placeholder=\"大模型生成的装配说明将在此显示，可编辑。\"></textarea>
      <button id=\"btnExportHTML\">导出装配说明 (HTML)</button>
    </section>
  </main>

  <script type=\"module\">
    import * as THREE from 'three';
    import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
    import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

    const viewer = document.querySelector('#viewer');
    const pdfjsLib = window.pdfjsLib || window['pdfjs-dist/build/pdf'] || window.pdfjsDistBuildPdf || null;
    if (!pdfjsLib) { console.error('pdf.js 未加载'); }
    const modelListEl = document.querySelector('#modelList');
    const bomSummaryEl = document.querySelector('#bomSummary');
    const llmStatusEl = document.querySelector('#llmStatus');
    const stepListEl = document.querySelector('#stepList');
    const llmOutputEl = document.querySelector('#llmOutput');
    const logArea = document.querySelector('#log');
    const explodeSlider = document.querySelector('#explodeSlider');

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(viewer.clientWidth, viewer.clientHeight);
    viewer.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#0b1220');

    const camera = new THREE.PerspectiveCamera(55, viewer.clientWidth / viewer.clientHeight, 0.1, 5000);
    camera.position.set(400, 320, 520);
    scene.add(camera);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.set(0, 120, 0);

    const ambient = new THREE.AmbientLight(0xffffff, 0.4);
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.85);
    dirLight.position.set(400, 700, 500);
    scene.add(ambient, dirLight);

    const grid = new THREE.GridHelper(2000, 40, 0x22334a, 0x19273f);
    scene.add(grid);

    function initExplodeModel(root) {
      if (!root) return;
      const box = new THREE.Box3().setFromObject(root);
      const center = new THREE.Vector3();
      box.getCenter(center);
      root.updateMatrixWorld(true);
      root.traverse(obj => {
        if (!obj.isMesh) return;
        const worldPos = obj.getWorldPosition(new THREE.Vector3());
        const dir = worldPos.clone().sub(center);
        const distance = dir.length();
        obj.userData.explodeDir = distance === 0 ? new THREE.Vector3() : dir.normalize();
        obj.userData.explodeDistance = distance;
        obj.userData.originWorld = worldPos.clone();
      });
    }

    function explodeModel(root, scalar) {
      if (!root) return;
      root.traverse(obj => {
        if (!obj.isMesh || !obj.userData.originWorld) return;
        const dir = obj.userData.explodeDir || new THREE.Vector3();
        const distance = obj.userData.explodeDistance || 0;
        const originWorld = obj.userData.originWorld.clone();
        const targetWorld = originWorld.add(dir.clone().multiplyScalar(distance * scalar));
        if (obj.parent) {
          obj.position.copy(obj.parent.worldToLocal(targetWorld));
        } else {
          obj.position.copy(targetWorld);
        }
      });
    }

    const loader = new GLTFLoader();
    let currentRoot = null;
    let parts = [];
    let steps = [];
    let bomStore = [];
    const modelLibrary = [];

    if (explodeSlider) {
      explodeSlider.addEventListener('input', e => {
        const value = parseFloat(e.target.value || '0');
        explodeModel(currentRoot, value);
      });
    }

    function log(message) {
      const stamp = new Date().toLocaleTimeString();
      if (logArea) {
        logArea.value += `[${stamp}] ${message}\n`;
        logArea.scrollTop = logArea.scrollHeight;
      }
      console.info(message);
    }

    function resetScene() {
      if (currentRoot) {
        scene.remove(currentRoot);
        currentRoot.traverse(obj => {
          if (obj.geometry) obj.geometry.dispose?.();
          if (obj.material) {
            if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose?.());
            else obj.material.dispose?.();
          }
        });
      }
      currentRoot = null;
      parts = [];
      steps = [];
      stepListEl.innerHTML = '';
      status.textContent = '等待模型加载...';
      if (explodeSlider) explodeSlider.value = '0';
    }

    function traverseParts(root) {
      const result = [];
      root.traverse(obj => { if (obj.isMesh) result.push(obj); });
      return result;
    }

    function renderModelList() {
      modelListEl.innerHTML = '';
      if (!modelLibrary.length) {
        modelListEl.innerHTML = '<div class=\"muted\">尚未上传模型。</div>';
        return;
      }
      modelLibrary.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'list-item';
        div.innerHTML = `<span class=\"badge ${item.isAssembly ? 'assembly' : 'component'}\">${item.isAssembly ? '整机' : '零件'}</span><strong>${item.name}</strong>`;
        const row = document.createElement('div');
        row.className = 'btn-line';
        const btnLoad = document.createElement('button');
        btnLoad.textContent = '加载预览';
        btnLoad.addEventListener('click', () => loadModelEntry(item));
        const btnRemove = document.createElement('button');
        btnRemove.textContent = '移除';
        btnRemove.addEventListener('click', () => {
          if (item.url && item.url.startsWith('blob:')) URL.revokeObjectURL(item.url);
          modelLibrary.splice(index, 1);
          renderModelList();
          resetScene();
        });
        row.appendChild(btnLoad);
        row.appendChild(btnRemove);
        div.appendChild(row);
        modelListEl.appendChild(div);
      });
    }

    function renderStepList(list) {
      stepListEl.innerHTML = '';
      if (!list.length) {
        stepListEl.innerHTML = '<div class=\"muted\">尚未生成步骤。</div>';
        return;
      }
      list.forEach((step, idx) => {
        const div = document.createElement('div');
        div.className = 'step-item';
        div.innerHTML = `<h3>${step.title}<small>#${idx + 1}</small></h3><div class=\"step-body\">${step.description}</div>`;
        stepListEl.appendChild(div);
      });
    }

    const status = document.querySelector('#status');

    function loadModelEntry(entry) {
      if (!entry) return;
      loadModel(entry.blob || entry.url, entry.name);
    }

    function loadModel(source, label = '未知模型') {
      resetScene();
      const isBlob = source instanceof Blob;
      const url = isBlob ? URL.createObjectURL(source) : source;
      status.textContent = '正在加载模型...';
      log(`开始加载模型：${label}`);
      loader.load(url, gltf => {
        if (isBlob) URL.revokeObjectURL(url);
        currentRoot = gltf.scene;
        scene.add(gltf.scene);
        const box = new THREE.Box3().setFromObject(gltf.scene);
        const size = new THREE.Vector3();
        box.getSize(size);
        const center = new THREE.Vector3();
        box.getCenter(center);
        controls.target.copy(center);
        camera.position.copy(center.clone().add(new THREE.Vector3(size.length() * 0.8, size.length() * 0.6, size.length() * 0.8)));
        camera.near = Math.max(0.1, size.length() * 0.01);
        camera.far = size.length() * 10;
        camera.updateProjectionMatrix();
        controls.update();

        parts = traverseParts(gltf.scene);
        initExplodeModel(gltf.scene);
        explodeModel(gltf.scene, parseFloat(explodeSlider?.value || '0'));
        status.textContent = `装配体已加载，共 ${parts.length} 个网格`;
        log(`模型加载完成：${label}，共 ${parts.length} 个网格`);
      }, undefined, err => {
        if (isBlob) URL.revokeObjectURL(url);
        status.textContent = '模型加载失败';
        log(`模型加载失败：${err.message}`);
      });
    }

    document.querySelector('#fileModels').addEventListener('change', e => {
      const files = Array.from(e.target.files ?? []);
      if (!files.length) return;
      files.forEach(file => {
        const url = URL.createObjectURL(file);
        const isAssembly = /(总图|assembly|final|总成|complete)/i.test(file.name);
        modelLibrary.push({ name: file.name, url, blob: file, isAssembly });
      });
      renderModelList();
      const preferred = modelLibrary.find(item => item.isAssembly) || modelLibrary[0];
      if (preferred) loadModelEntry(preferred);
      log(`已加入 ${files.length} 个模型文件`);
      e.target.value = '';
    });

    document.querySelector('#btnClearModels').addEventListener('click', () => {
      modelLibrary.forEach(item => { if (item.url && item.url.startsWith('blob:')) URL.revokeObjectURL(item.url); });
      modelLibrary.length = 0;
      renderModelList();
      resetScene();
    });

"""

path = Path(r"e:\\装配\\prototype\\index.html")
path.write_text(html, encoding='utf-8')
