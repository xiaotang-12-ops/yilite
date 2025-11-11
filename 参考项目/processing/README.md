# Processing Pipeline

This folder contains utility scripts that prepare CAD/PDF uploads for the front-end prototype.

## ingest.py

`ingest.py` scans a directory tree for `*.pdf` and `*.dwg` files and produces structured outputs in `processing/output`:

- For each PDF it extracts plain text, heuristically parses BOM rows, and exports:
  - `<name>.json` – full extraction report.
  - `<name>_bom.json` – simplified payload (`{"items": [...]}`) that can be uploaded to the prototype UI.
- For each DWG it tries to call an external converter (configurable via the `ODA_CONVERTER` environment variable). If no converter is available it copies `model.glb` as a placeholder into `processing/output/cad/<name>/<name>_placeholder.glb`.
- `summary.json` aggregates everything for quick inspection.

### Usage

```powershell
# from repo root
env:PYTHONUTF8 = "1"  # ensure UTF-8 console output
python processing/ingest.py . --output processing/output --placeholder-glb model.glb
```

To enable real DWG translation inside `ingest.py`, configure the conversion pipeline described below first.

### Feeding the front-end

1. Run `processing/ingest.py` to generate the BOM JSON.
2. Start a static file server (e.g. `python -m http.server`) inside the project root.
3. Open `prototype/index.html` through the local server.
4. Upload the converted GLB (or placeholder) via “导入几何文件”。
5. Upload `processing/output/pdf/<name>_bom.json` via “上传 BOM / 零件列表”。
6. Click “自动生成步骤” to preview the heuristics。

## DWG → GLB (3D 模型工作流)

`processing/dwg_to_glb.py` 实现 “DWG → DXF → GLB”的批处理流程，依赖：

1. [ODA/Teigha File Converter](https://www.opendesign.com/guestfiles/teighafileconverter) – 负责 DWG→DXF。
2. Blender（需启用 DXF 导入插件：`编辑 > 首选项 > 插件 > Import-Export: AutoCAD DXF Format`）。
3. 设置环境变量（PowerShell 示例）：
   ```powershell
   setx ODA_CONVERTER "C:\Program Files\ODA\ODAFileConverter 26.8.0\ODAFileConverter.exe"
   setx BLENDER_EXE "C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"
   ```
   重新打开终端后生效。可选变量：
   `ODA_INPUT_VERSION`, `ODA_OUTPUT_VERSION`, `ODA_OUTPUT_FORMAT` (默认 DXF),
   `ODA_RECURSIVE`, `ODA_AUDIT`, `ODA_LOG`, `ODA_CMD_TEMPLATE`, `BLENDER_GLTF_TEMPLATE`。
4. 执行脚本：
   ```powershell
   python processing/dwg_to_glb.py 测试-CAD --output processing/converted --keep-dxf
   ```
   - 脚本会递归查找 `.dwg`，用 ODA 转成 `.dxf`，再调用 Blender 批量输出 `.glb`。默认会生成临时脚本 `processing/_blender_import_export.py`；也可以通过 `--blender-python` 指定自定义脚本。
   - `--keep-dxf` 可保留中间 `.dxf` 文件便于校对。

完成转换后，再运行 `processing/ingest.py` 即可直接使用生成的 GLB 数据。也可以将输出目录指向 `processing/output/cad`，让前端直接读取。

## PDF → 手册 (二维工程图工作流)

`processing/manual_from_2d.py` 将二维工程图 (PDF) 转成易读的装配说明草稿：

- 按指定 DPI 渲染 PDF 为高分辨率 PNG。
- 复用 `ingest.py` 中的规则解析 BOM，生成结构化数据。
- 产出带图片 + 自动生成步骤列表的 HTML 手册。

使用示例：

```powershell
python processing/manual_from_2d.py 测试-pdf --output processing/manual --dpi 250
```

输出结构：

```
processing/manual/
  summary.json           # 汇总信息
  产品总图/
    manual.html          # 可直接给工人查看的说明页
    bom.json             # 结构化 BOM 数据
    images/page-01.png   # 渲染出的工程图页面
    …
```

HTML 会把整页工程图作为插图，并根据 BOM 生成“步骤 N：安装 XXX”式说明，便于工艺人员二次核对后直接使用。

## Roadmap

- Swap placeholder conversion with a real DWG → glTF/STEP pipeline。
- Improve BOM parsing rules and add OCR fallback for scanned PDFs。
- Persist results to a lightweight database so multiple revisions can be tracked。
