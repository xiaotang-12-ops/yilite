// 同场景建筑曲面、琥珀光带与浅色地面；相机旋转时遵循真实透视。
// 环境几何由场景统一回收，PMREM单独释放；动效不移动模型和阴影灯。-codex，2026-10-09
import * as THREE from 'three'
import { Sky } from 'three/examples/jsm/objects/Sky.js'
import { Reflector } from 'three/examples/jsm/objects/Reflector.js'

/** 内向单面曲幕；从外侧观察时近侧背面剔除，远侧曲幕仍与厂区共享透视。 */
function curvedBand(radius: number, lower: (angle: number) => number, upper: (angle: number) => number) {
  const positions: number[] = [], uvs: number[] = [], indices: number[] = []
  const segments = 192
  for (let i = 0; i <= segments; i++) {
    const angle = i / segments * Math.PI * 2
    for (const y of [lower(angle), upper(angle)]) {
      positions.push(Math.sin(angle) * radius, y, Math.cos(angle) * radius)
      uvs.push(i / segments, y === lower(angle) ? 0 : 1)
    }
    if (i < segments) {
      const n = i * 2
      indices.push(n, n + 1, n + 2, n + 1, n + 3, n + 2)
    }
  }
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2))
  geometry.setIndex(indices)
  geometry.computeVertexNormals()
  return geometry
}

export function createFactoryEnvironment(scene: THREE.Scene, renderer: THREE.WebGLRenderer) {
  scene.background = new THREE.Color('#edf0f2')
  scene.fog = new THREE.Fog('#edf0f2', 800, 1400)
  const sky = new Sky()
  sky.scale.setScalar(1000)
  sky.material.uniforms.turbidity.value = 7
  sky.material.uniforms.rayleigh.value = 1.2
  sky.material.uniforms.sunPosition.value.set(-90, 140, 110)
  const pmrem = new THREE.PMREMGenerator(renderer)
  const reflectionScene = new THREE.Scene()
  reflectionScene.add(sky)
  for (let i = 0; i < 18; i++) {
    const angle = i * Math.PI * 2 / 18
    const hill = new THREE.Mesh(new THREE.SphereGeometry(1, 12, 8),
      new THREE.MeshBasicMaterial({ color: i % 3 === 0 ? '#405345' : '#617066' }))
    hill.scale.set(180 + i % 4 * 25, 85 + i % 5 * 17, 130)
    hill.position.set(Math.cos(angle) * 650, -65, Math.sin(angle) * 650)
    reflectionScene.add(hill)
  }
  const environment = pmrem.fromScene(reflectionScene, .04)
  scene.environment = environment.texture
  pmrem.dispose()
  reflectionScene.traverse(object => {
    if (object instanceof THREE.Mesh) {
      object.geometry.dispose()
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) material.dispose()
    }
  })
  scene.add(new THREE.HemisphereLight('#fff7ec', '#bbc9d1', 1.15))
  const sun = new THREE.DirectionalLight('#fff2dc', 2.6)
  sun.position.set(-60, 85, 140)
  sun.castShadow = true
  sun.shadow.mapSize.set(2048, 2048)
  Object.assign(sun.shadow.camera, { left: -145, right: 145, top: 145, bottom: -145, near: 1, far: 500 })
  sun.shadow.normalBias = .16
  scene.add(sun)
  const rim = new THREE.DirectionalLight('#d0e5ff', 1.1)
  rim.position.set(70, 65, -100)
  scene.add(rim)

  // 低分辨率反射叠加柔化采样，呈现建筑倒影而不是第二张静态背景图片。
  const floor = new Reflector(new THREE.PlaneGeometry(1600, 1600), {
    color: '#dce1e5', textureWidth: 768, textureHeight: 512, multisample: 0,
    shader: {
      uniforms: { color: { value: null }, tDiffuse: { value: null }, textureMatrix: { value: null } },
      vertexShader: `uniform mat4 textureMatrix; varying vec4 vUv; varying vec3 vWorld;
        #include <common>
        #include <logdepthbuf_pars_vertex>
        void main() {
          vUv = textureMatrix * vec4(position, 1.0);
          vWorld = (modelMatrix * vec4(position, 1.0)).xyz;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          #include <logdepthbuf_vertex>
        }`,
      fragmentShader: `uniform vec3 color; uniform sampler2D tDiffuse; varying vec4 vUv; varying vec3 vWorld;
        #include <logdepthbuf_pars_fragment>
        void main() {
          #include <logdepthbuf_fragment>
          vec2 uv = vUv.xy / vUv.w;
          vec3 reflection = texture2D(tDiffuse, uv).rgb * .4;
          reflection += texture2D(tDiffuse, uv + vec2(.002, .003)).rgb * .15;
          reflection += texture2D(tDiffuse, uv - vec2(.002, .003)).rgb * .15;
          reflection += texture2D(tDiffuse, uv + vec2(-.003, .002)).rgb * .15;
          reflection += texture2D(tDiffuse, uv - vec2(-.003, .002)).rgb * .15;
          vec3 surface = mix(color, reflection, .3);
          float warm = exp(-abs(length(vWorld.xz) - 150.0) / 40.0) * .22;
          gl_FragColor = vec4(mix(surface, vec3(1.0, .68, .31), warm), 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`
    }
  })
  floor.rotation.x = -Math.PI / 2
  floor.position.y = -1.75
  scene.add(floor)
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(1600, 1600),
    new THREE.ShadowMaterial({ color: '#3d4c57', opacity: .17 }))
  ground.rotation.x = -Math.PI / 2
  ground.position.y = -1.7
  ground.receiveShadow = true
  scene.add(ground)

  // 曲面的高低变化形成建筑式斜向层次，不复刻首页的旋转线条。
  const decoration = new THREE.Group()
  scene.add(decoration)
  const ribbonTop = (angle: number) => 21 + 12 * Math.sin(angle + .7) + 4 * Math.cos(angle * 2)
  const metalCanvas = document.createElement('canvas')
  metalCanvas.width = 1024
  metalCanvas.height = 32
  const metalContext = metalCanvas.getContext('2d')!
  const sheen = metalContext.createLinearGradient(0, 0, 1024, 0)
  for (const [stop, tone] of [[0, '#acb1b8'], [.12, '#ffffff'], [.23, '#737c87'], [.36, '#d9dce0'], [.49, '#ffffff'], [.62, '#717b85'], [.77, '#d4d9df'], [.91, '#ffffff'], [1, '#acb1b8']] as const) sheen.addColorStop(stop, tone)
  metalContext.fillStyle = sheen
  metalContext.fillRect(0, 0, 1024, 32)
  const metalMap = new THREE.CanvasTexture(metalCanvas)
  metalMap.colorSpace = THREE.SRGBColorSpace
  const silver = new THREE.Mesh(curvedBand(210, ribbonTop, angle => ribbonTop(angle) + 120),
    new THREE.MeshStandardMaterial({ color: '#e2e3e5', map: metalMap, metalness: .18, roughness: .37, envMapIntensity: .7 }))
  decoration.add(silver)
  const upper = new THREE.Mesh(curvedBand(225, angle => ribbonTop(angle) + 125, angle => ribbonTop(angle) + 210),
    new THREE.MeshStandardMaterial({ color: '#e0e4e8', metalness: .25, roughness: .5 }))
  decoration.add(upper)

  const amberMaterial = new THREE.MeshStandardMaterial({ color: '#bf711d', map: metalMap, emissive: '#ff9c31', emissiveIntensity: .08,
    metalness: .5, roughness: .26, envMapIntensity: .8 })
  decoration.add(new THREE.Mesh(curvedBand(209, () => -1.5, ribbonTop), amberMaterial))
  const trimMaterial = new THREE.MeshBasicMaterial({ color: '#ffe5ae' })
  decoration.add(new THREE.Mesh(curvedBand(208.8, angle => ribbonTop(angle) - .65, ribbonTop), trimMaterial))
  decoration.add(new THREE.Mesh(curvedBand(208.8, () => -.8, () => -.1), trimMaterial))

  // 柔光在宽曲面内缓慢平移；透明着色只作用于环境，保持厂区材质真实。
  const flowMaterial = new THREE.ShaderMaterial({
    uniforms: { time: { value: 0 } },
    vertexShader: `varying vec2 vUv;
      void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `varying vec2 vUv; uniform float time;
      void main() {
        float wave = pow(max(0.0, cos(vUv.x * 37.699 - time * .23)), 18.0);
        float edge = .3 + .7 * pow(abs(vUv.y * 2.0 - 1.0), 2.0);
        gl_FragColor = vec4(1.0, .81, .45, wave * edge * .34);
      }`,
    transparent: true, depthWrite: false
  })
  decoration.add(new THREE.Mesh(curvedBand(208.5, () => -1.4, ribbonTop), flowMaterial))

  // 光带与承光面共用世界方位和时间：转动相机时亮部仍对应同一段曲幕。
  const lightTime = { value: 0 }
  const edgeGlow = new THREE.ShaderMaterial({
    uniforms: { time: lightTime },
    vertexShader: `varying vec2 vUv;
      void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `varying vec2 vUv; uniform float time;
      void main() {
        float pulse = pow(max(0.0, cos(vUv.x * 37.699112 - time * .10)), 6.0);
        float softness = exp(-pow((vUv.y - .5) * 3.5, 2.0));
        gl_FragColor = vec4(1.0, .88, .61, pulse * softness * .92);
      }`,
    transparent: true, depthWrite: false
  })
  decoration.add(new THREE.Mesh(curvedBand(208.3, angle => ribbonTop(angle) - 3, angle => ribbonTop(angle) + 3), edgeGlow))
  const poolMaterial = new THREE.ShaderMaterial({
    uniforms: { time: lightTime },
    vertexShader: `varying vec3 vWorld;
      void main() { vWorld = (modelMatrix * vec4(position, 1.0)).xyz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `varying vec3 vWorld; uniform float time;
      void main() {
        float angle = atan(vWorld.x, vWorld.z);
        float pulse = pow(max(0.0, cos(angle * 6.0 - time * .10)), 3.0);
        float falloff = exp(-pow((length(vWorld.xz) - 187.0) / 25.0, 2.0));
        gl_FragColor = vec4(1.0, .76, .39, falloff * (.16 + pulse * .48));
      }`,
    transparent: true, depthWrite: false
  })
  const lightPool = new THREE.Mesh(new THREE.PlaneGeometry(500, 500), poolMaterial)
  lightPool.rotation.x = -Math.PI / 2
  lightPool.position.y = -.9
  decoration.add(lightPool)

  decoration.traverse(object => object.layers.set(1))
  for (const x of [32, 48]) {
    const lamp = new THREE.PointLight('#ffbd72', 8, 20, 2)
    lamp.position.set(x, 3.5, 82)
    scene.add(lamp)
  }
  return {
    update(seconds: number) { flowMaterial.uniforms.time.value = seconds; lightTime.value = seconds },
    dispose() { floor.dispose(); environment.dispose() }
  }
}
