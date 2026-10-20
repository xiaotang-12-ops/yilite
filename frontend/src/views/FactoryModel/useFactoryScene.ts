// 厂区独立静态场景：只读取GLB，不依赖装配业务；离开路由时回收GPU和请求资源。
// 按材质合并静态几何减少车辆、窗框、屋面造成的绘制调用。-codex，2026-10-08
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js'
import { createFactoryEnvironment } from './createFactoryEnvironment'
import { createFactoryTrees } from './createFactoryTrees'
import { applyFactoryMaterials } from './applyFactoryMaterials'

type ViewId = 'overview' | 'front' | 'side' | 'top' | 'entry'
const poses: Record<ViewId, { position: [number, number, number]; target: [number, number, number] }> = {
  overview: { position: [175, 105, 200], target: [0, 8, 0] },
  front: { position: [35, 28, 125], target: [0, 4, 55] },
  side: { position: [180, 70, 50], target: [15, -20, 0] },
  top: { position: [0, 205, 1], target: [0, 0, 0] },
  entry: { position: [95, 32, 135], target: [39, 2, 80] }
}

function disposeTree(root: THREE.Object3D, disposeMaterials = true) {
  const geometries = new Set<THREE.BufferGeometry>()
  const materials = new Set<THREE.Material>()
  const textures = new Set<THREE.Texture>()
  root.traverse(object => {
    if (!(object instanceof THREE.Mesh || object instanceof THREE.Line)) return
    geometries.add(object.geometry)
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) materials.add(material)
  })
  geometries.forEach(geometry => geometry.dispose())
  if (!disposeMaterials) return
  materials.forEach(material => {
    Object.values(material).forEach(value => { if (value instanceof THREE.Texture) textures.add(value) })
    material.dispose()
  })
  textures.forEach(texture => texture.dispose())
}

function mergeStaticModel(source: THREE.Group): THREE.Group {
  const batches = new Map<THREE.Material, THREE.BufferGeometry[]>()
  source.updateMatrixWorld(true)
  source.traverse(object => {
    if (!(object instanceof THREE.Mesh)) return
    // 本模型导出单材质静态mesh；遇到非预期资产直接报错，避免静默丢失构件。
    if (Array.isArray(object.material)) throw new Error('厂区模型材质结构不匹配')
    let geometry = object.geometry.clone()
    if (geometry.index) {
      const indexed = geometry
      geometry = indexed.toNonIndexed()
      indexed.dispose()
    }
    geometry.applyMatrix4(object.matrixWorld)
    Object.keys(geometry.attributes).forEach(key => {
      if (key !== 'position' && key !== 'normal') geometry.deleteAttribute(key)
    })
    if (!geometry.attributes.normal) geometry.computeVertexNormals()
    const list = batches.get(object.material) || []
    list.push(geometry)
    batches.set(object.material, list)
  })
  const result = new THREE.Group()
  try {
    batches.forEach((geometries, material) => {
      const geometry = mergeGeometries(geometries, false)
      if (!geometry) throw new Error('厂区模型几何合并失败')
      const mesh = new THREE.Mesh(geometry, material)
      mesh.castShadow = true
      mesh.receiveShadow = true
      result.add(mesh)
    })
  } catch (error) {
    disposeTree(result, false)
    throw error
  } finally {
    batches.forEach(geometries => geometries.forEach(geometry => geometry.dispose()))
  }
  disposeTree(source, false)
  return result
}

export function useFactoryScene() {
  const container = ref<HTMLElement | null>(null)
  const ready = ref(false)
  const error = ref('')
  const status = ref('准备场景…')
  const activeView = ref<ViewId | null>('overview')
  let renderer: THREE.WebGLRenderer | undefined
  let scene: THREE.Scene | undefined
  let camera: THREE.PerspectiveCamera | undefined
  let controls: OrbitControls | undefined
  let observer: ResizeObserver | undefined
  let environment: ReturnType<typeof createFactoryEnvironment> | undefined
  const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)')
  let transition: { started: number; fromPosition: THREE.Vector3; fromTarget: THREE.Vector3; position: THREE.Vector3; target: THREE.Vector3 } | undefined
  let destroyed = false
  let visible = !document.hidden
  let frame = 0
  let startupFrame = 0
  let needsRender = true
  let lastDraw = 0
  const request = new AbortController()

  // WebGL2用非阻塞fence等待真实首帧GPU任务；WebGL1交由下一呈现帧同步，不使用阻塞finish。
  function waitForFirstFrame() {
    return new Promise<void>((resolve, reject) => {
      const gl = renderer!.getContext() as WebGL2RenderingContext
      const fence = typeof gl.fenceSync === 'function' ? gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0) : null
      const cleanup = () => {
        request.signal.removeEventListener('abort', abort)
        if (fence) gl.deleteSync(fence)
      }
      const abort = () => { cancelAnimationFrame(startupFrame); cleanup(); reject(new Error('场景准备已取消')) }
      const poll = () => {
        if (request.signal.aborted || destroyed) { abort(); return }
        if (fence) {
          const result = gl.clientWaitSync(fence, 0, 0)
          if (result === gl.WAIT_FAILED) { cleanup(); reject(new Error('首帧绘制失败，请重试')); return }
          if (result === gl.TIMEOUT_EXPIRED) { startupFrame = requestAnimationFrame(poll); return }
        }
        cleanup()
        resolve()
      }
      request.signal.addEventListener('abort', abort, { once: true })
      gl.flush()
      startupFrame = requestAnimationFrame(poll)
    })
  }

  function render() {
    if (!renderer || !scene || !camera || destroyed || !visible || error.value) return
    if (transition && controls) {
      needsRender = true
      const progress = Math.min(1, (performance.now() - transition.started) / 850)
      const eased = progress * progress * (3 - 2 * progress)
      camera.position.lerpVectors(transition.fromPosition, transition.position, eased)
      controls.target.lerpVectors(transition.fromTarget, transition.target, eased)
      if (progress === 1) transition = undefined
    }
    if (controls?.update()) needsRender = true
    // 背景柔光与厂区共享画布；可见时限24帧，减少动态偏好时恢复按需绘制。
    if (!motionPreference.matches) needsRender = true
    if (needsRender && performance.now() - lastDraw > 1000 / 24) {
      environment?.update(motionPreference.matches ? 0 : performance.now() / 1000)
      renderer.render(scene, camera)
      lastDraw = performance.now()
      needsRender = false
    }
    frame = requestAnimationFrame(render)
  }
  function setView(id: ViewId) {
    if (!camera || !controls || !ready.value || error.value) return
    const pose = poses[id]
    // 切换前清空阻尼积累，避免预设视角受上一轮拖动惯性影响。
    controls.enableDamping = false
    controls.update()
    if (id === 'top') camera.up.set(1, 0, 0)
    else camera.up.set(0, 1, 0)
    if (frame && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      transition = { started: performance.now(), fromPosition: camera.position.clone(), fromTarget: controls.target.clone(),
        position: new THREE.Vector3(...pose.position), target: new THREE.Vector3(...pose.target) }
    } else {
      camera.position.fromArray(pose.position)
      controls.target.fromArray(pose.target)
    }
    controls.update()
    controls.enableDamping = true
    activeView.value = id
    needsRender = true
  }
  function onVisibility() {
    visible = !document.hidden
    cancelAnimationFrame(frame)
    if (visible) render()
  }
  function onContextLost(event: Event) {
    event.preventDefault()
    cancelAnimationFrame(frame)
    error.value = '图形上下文已中断，请重新加载页面。'
    ready.value = false
  }
  function onControlStart() {
    transition = undefined
    camera?.up.set(0, 1, 0)
    activeView.value = null
  }
  // 滚轮会在事件回调中立即update，下一RAF可能返回false；change必须独立标记脏帧。
  function onControlChange() { needsRender = true }
  function onMotionPreference() { needsRender = true }

  onMounted(async () => {
    const host = container.value
    if (!host) return
    try {
      scene = new THREE.Scene()
      camera = new THREE.PerspectiveCamera(40, 1, .5, 1000)
      // 环境曲幕在独立可见层；地面只反射厂区，避免近侧曲幕的背面倒影割裂地面。
      camera.layers.enable(1)
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' })
      let shaderFailed = false
      renderer.debug.onShaderError = () => { shaderFailed = true }
      // 全页画布：环境与模型在同一空间；不使用生成图片作为旋转背景。
      renderer.setClearColor(0x000000, 0)
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      renderer.outputColorSpace = THREE.SRGBColorSpace
      renderer.toneMapping = THREE.ACESFilmicToneMapping
      renderer.toneMappingExposure = .95
      environment = createFactoryEnvironment(scene, renderer)
      renderer.shadowMap.enabled = true
      renderer.shadowMap.type = THREE.PCFSoftShadowMap
      // 场景和灯光固定，相机转动不改变阴影，避免每帧重复绘制整座厂区。
      renderer.shadowMap.autoUpdate = false
      host.appendChild(renderer.domElement)
      renderer.domElement.addEventListener('webglcontextlost', onContextLost)
      controls = new OrbitControls(camera, renderer.domElement)
      controls.enableDamping = true
      controls.enablePan = false
      controls.minDistance = 195
      controls.maxDistance = 350
      controls.minPolarAngle = .38
      controls.maxPolarAngle = 1.36
      controls.rotateSpeed = .55
      controls.zoomSpeed = .65
      controls.addEventListener('start', onControlStart)
      controls.addEventListener('change', onControlChange)
      const resize = () => {
        if (!camera || !renderer) return
        const width = host.clientWidth, height = host.clientHeight
        if (!width || !height) return
        camera.aspect = width / height
        // 负向投影偏移为左侧固定数据留白，不改变围绕厂区中心的旋转轴。
        camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(15)) * Math.max(1, 1.9 / camera.aspect)))
        camera.setViewOffset(width, height, -width * .115, height * .105, width, height)
        camera.updateProjectionMatrix()
        renderer.setSize(width, height)
        needsRender = true
      }
      observer = new ResizeObserver(resize)
      observer.observe(host)
      resize()
      status.value = '载入厂房、光伏与厂区环境…'
      const manager = new THREE.LoadingManager()
      let textureFailed = false
      manager.onError = () => { textureFailed = true }
      const models = await Promise.allSettled(['yilite-factory.glb', 'yilite-tree.glb'].map(async filename => {
        const response = await fetch(`/models/${filename}`, { signal: request.signal })
        if (!response.ok) throw new Error(`模型请求失败（${response.status}）`)
        const buffer = await response.arrayBuffer()
        return new GLTFLoader(manager).parseAsync(buffer, '/models/')
      }))
      const failed = models.find(model => model.status === 'rejected')
      if (destroyed || failed || textureFailed) {
        models.forEach(model => { if (model.status === 'fulfilled') disposeTree(model.value.scene) })
        if (failed?.status === 'rejected') throw failed.reason
        if (textureFailed) throw new Error('模型纹理加载失败，请重试')
        return
      }
      const gltf = (models[0] as PromiseFulfilledResult<Awaited<ReturnType<GLTFLoader['parseAsync']>>>).value
      const tree = (models[1] as PromiseFulfilledResult<Awaited<ReturnType<GLTFLoader['parseAsync']>>>).value
      gltf.scene.updateMatrixWorld(true)
      const placements: THREE.Matrix4[] = []
      gltf.scene.traverse(object => { if (object.name.startsWith('TreePlacement')) placements.push(object.matrixWorld.clone()) })
      try {
        if (!placements.length) throw new Error('厂区模型缺少绿化位置，请检查配套资源')
        const building = mergeStaticModel(gltf.scene)
        applyFactoryMaterials(building)
        scene.add(building)
        scene.add(createFactoryTrees(tree.scene, placements))
      } catch (cause) {
        disposeTree(gltf.scene)
        disposeTree(tree.scene)
        throw cause
      }
      status.value = '准备材质、灯光与首帧画面…'
      camera.position.fromArray(poses.overview.position)
      controls.target.fromArray(poses.overview.target)
      controls.update()
      await renderer.compileAsync(scene, camera)
      if (destroyed || request.signal.aborted) return
      renderer.shadowMap.needsUpdate = true
      environment.update(0)
      renderer.render(scene, camera)
      if (shaderFailed) throw new Error('当前图形设备无法完成场景着色，请重试')
      await waitForFirstFrame()
      if (destroyed || error.value || request.signal.aborted) return
      ready.value = true
      status.value = '场景已就绪'
      document.addEventListener('visibilitychange', onVisibility)
      motionPreference.addEventListener('change', onMotionPreference)
      render()
    } catch (cause) {
      if (destroyed) return
      console.error('厂区模型加载失败', cause)
      error.value = cause instanceof Error ? cause.message : '当前电脑无法初始化三维展示。'
      ready.value = false
    }
  })

  onBeforeUnmount(() => {
    destroyed = true
    request.abort()
    cancelAnimationFrame(frame)
    cancelAnimationFrame(startupFrame)
    observer?.disconnect()
    document.removeEventListener('visibilitychange', onVisibility)
    motionPreference.removeEventListener('change', onMotionPreference)
    controls?.removeEventListener('start', onControlStart)
    controls?.removeEventListener('change', onControlChange)
    controls?.dispose()
    environment?.dispose()
    renderer?.domElement.removeEventListener('webglcontextlost', onContextLost)
    if (scene) {
      scene.traverse(object => { if (object instanceof THREE.Light) object.dispose() })
      disposeTree(scene)
      scene.traverse(object => { if (object instanceof THREE.InstancedMesh) object.dispose() })
      if (scene.background instanceof THREE.Texture) scene.background.dispose()
      scene.clear()
    }
    renderer?.dispose()
    renderer?.forceContextLoss()
    renderer?.domElement.remove()
  })

  return { container, ready, error, status, activeView, setView }
}
