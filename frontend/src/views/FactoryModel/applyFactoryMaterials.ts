// 静态厂房材质微表面：世界坐标纹理避免屋面/院坪像无细节的塑料板。
// 只作用于厂区自带材质，资源统一由场景卸载回收。-codex，2026-10-08
import * as THREE from 'three'

function surfaceTexture() {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 256
  const context = canvas.getContext('2d')!
  const pixels = context.createImageData(256, 256)
  let seed = 27
  for (let i = 0; i < pixels.data.length; i += 4) {
    seed = (seed * 1664525 + 1013904223) >>> 0
    const tone = 218 + (seed >>> 28)
    pixels.data[i] = pixels.data[i + 1] = pixels.data[i + 2] = tone
    pixels.data[i + 3] = 255
  }
  context.putImageData(pixels, 0, 0)
  const texture = new THREE.CanvasTexture(canvas)
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping
  texture.colorSpace = THREE.SRGBColorSpace
  texture.anisotropy = 8
  return texture
}


export function applyFactoryMaterials(root: THREE.Object3D) {
  const texture = surfaceTexture()
  root.traverse(object => {
    if (!(object instanceof THREE.Mesh) || !(object.material instanceof THREE.MeshStandardMaterial)) return
    const material = object.material
    material.envMapIntensity = .32
    if (/屋面|院坪|道路|墙板|植被地面/.test(material.name)) {
      const position = object.geometry.attributes.position
      const normal = object.geometry.attributes.normal
      const uv = new Float32Array(position.count * 2)
      for (let i = 0; i < position.count; i++) {
        const horizontal = Math.abs(normal.getY(i)) > .65
        const side = Math.abs(normal.getX(i)) > .65
        const scale = .4
        uv[i * 2] = (side ? position.getZ(i) : position.getX(i)) * scale
        uv[i * 2 + 1] = (horizontal ? position.getZ(i) : position.getY(i)) * scale
      }
      object.geometry.setAttribute('uv', new THREE.BufferAttribute(uv, 2))
      material.map = texture
      if (!/屋面|外围道路|院坪|蓝绿窗带/.test(material.name)) {
        material.bumpMap = texture
        material.bumpScale = .012
      }
    }
    if (/屋面|檐口/.test(material.name)) {
      material.metalness = .62
      material.roughness = .5
      // 细密屋面筋在全厂区阴影贴图上会自遮挡成点阵，保留投影并关闭此接收路径。
      object.receiveShadow = false
    }
    if (/光伏/.test(material.name)) object.receiveShadow = false
    if (/光伏深蓝/.test(material.name)) { material.metalness = .75; material.roughness = .19; material.color.set('#172c42') }
    if (/外围道路/.test(material.name)) { material.color.set('#657072'); material.roughness = .96 }
    if (/院坪/.test(material.name)) { material.color.set('#737778'); material.roughness = .88 }
    if (/蓝绿窗带/.test(material.name)) { material.color.set('#517981'); material.metalness = .55; material.roughness = .22; material.envMapIntensity = .8 }
    if (/墙板/.test(material.name)) { material.color.set('#d7dedb'); material.metalness = .2; material.roughness = .55; material.envMapIntensity = .6 }
    if (/货架安全黄/.test(material.name)) { material.color.set('#9c7c31'); material.metalness = .6; material.roughness = .38; material.envMapIntensity = .7 }
    // 日景灯具保留暖色质感，关闭夜景强发光，避免门卫室和道闸附近爆白。
    if (/灯具暖光|入口导向光/.test(material.name)) material.emissiveIntensity = .12
    if (/树冠|植被地面/.test(material.name)) material.color.set('#263c2c')
    material.needsUpdate = true
  })
}
