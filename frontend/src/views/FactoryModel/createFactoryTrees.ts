// 写实树木共用三组几何与材质，通过实例矩阵保持绿化位置、尺度和朝向。
// 不合并叶片UV，透明剪裁避免远景树冠变成实体团块。-codex，2026-10-08
import * as THREE from 'three'

export function createFactoryTrees(source: THREE.Group, placements: THREE.Matrix4[]) {
  const forest = new THREE.Group()
  source.updateMatrixWorld(true)
  source.traverse(object => {
    if (!(object instanceof THREE.Mesh)) return
    const geometry = object.geometry.clone().applyMatrix4(object.matrixWorld)
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    materials.forEach(material => {
      material.side = THREE.DoubleSide
      if (material instanceof THREE.MeshStandardMaterial && material.name.includes('leaves')) {
        // 远景叶片的mipmap会稀释遮罩，低阈值保留树冠覆盖，近景仍由原图剪裁。
        material.alphaTest = .04
        material.transparent = false
        material.depthWrite = true
        // 叶片背光透射的近似，使用原叶片颜色图作微量补光，保留纹理而非纯绿块。
        material.emissiveMap = material.map
        material.emissive.set('#c2cfa3')
        material.emissiveIntensity = .12
      }
    })
    const trees = new THREE.InstancedMesh(geometry, object.material, placements.length)
    placements.forEach((matrix, i) => trees.setMatrixAt(i, matrix))
    trees.instanceMatrix.needsUpdate = true
    trees.castShadow = true
    trees.receiveShadow = true
    forest.add(trees)
  })
  // 材质由forest接管，原始几何无需保留；统一卸载时再回收共享材质/贴图。
  const originals = new Set<THREE.BufferGeometry>()
  source.traverse(object => { if (object instanceof THREE.Mesh) originals.add(object.geometry) })
  originals.forEach(geometry => geometry.dispose())
  return forest
}
