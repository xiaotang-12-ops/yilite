from pathlib import Path

path = Path(r"e:\\装配\\prototype\\index.html")
text = path.read_text(encoding='utf-8')
old = "    document.querySelector('#fileModels').addEventListener('change', e => {\n      const files = Array.from(e.target.files ?? []);\n      if (!files.length) return;\n      files.forEach(file => {\n        const url = URL.createObjectURL(file);\n        const isAssembly = /(总图|assembly|final|总成|complete)/i.test(file.name);\n        modelLibrary.push({ name: file.name, url, blob: file, isAssembly });\n      });\n      renderModelList();\n      log(`已加入 ${files.length} 个模型文件`);\n      e.target.value = '';\n    });\n"
new = "    document.querySelector('#fileModels').addEventListener('change', e => {\n      const files = Array.from(e.target.files ?? []);\n      if (!files.length) return;\n      files.forEach(file => {\n        const url = URL.createObjectURL(file);\n        const isAssembly = /(总图|assembly|final|总成|complete)/i.test(file.name);\n        modelLibrary.push({ name: file.name, url, blob: file, isAssembly });\n      });\n      renderModelList();\n      const preferred = modelLibrary.find(item => item.isAssembly) || modelLibrary[0];\n      if (preferred) {\n        loadModelEntry(preferred);\n      }\n      log(`已加入 ${files.length} 个模型文件`);\n      e.target.value = '';\n    });\n"
if old not in text:
    raise SystemExit('fileModels handler snippet not found')
path.write_text(text.replace(old, new), encoding='utf-8')
