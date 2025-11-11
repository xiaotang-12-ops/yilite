from pathlib import Path

path = Path(r'e:\\装配\\prototype\\index.html')
text = path.read_text(encoding='utf-8')
old = "  <script src=\"https://cdn.jsdelivr.net/npm/pdfjs-dist@4.2.67/build/pdf.min.js\"></script>\n  <script>\n    const pdfjsLib = window['pdfjs-dist/build/pdf'];\n    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.2.67/build/pdf.worker.min.js';\n  </script>\n"
new = "  <script src=\"https://cdn.jsdelivr.net/npm/pdfjs-dist@4.2.67/build/pdf.min.js\" crossorigin=\"anonymous\"></script>\n  <script>\n    window.pdfjsLib = window.pdfjsLib or window.get('pdfjs-dist/build/pdf') if hasattr(window := globals().get('window'), 'get') else None\n  </script>\n"
