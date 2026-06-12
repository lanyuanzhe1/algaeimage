---
name: feedback-docx-workflow
description: Markdown→Word 转换工作流偏好 — pandoc + OOXML XML编辑，优先于 docx-js
metadata:
  type: feedback
---

**规则**: 包含 LaTeX 公式的 Markdown 转 Word 时，优先用 pandoc（公式→OMML 原生渲染），然后解包编辑 XML 调整排版（页边距、页眉页脚、表格样式），最后重新打包。

**Why**: 用户明确指示"使用 pandoc，然后你再修改格式"。LaTeX 公式在 Word 中必须是原生 OMML 对象（可编辑），不能是图片。docx-js 无法处理 LaTeX 公式转 OMML，只适合无公式的纯文本/表格文档。

**How to apply**: 
1. `pandoc input.md -o output.docx` — 核心转换
2. `python ooxml/scripts/unpack.py output.docx unpacked/` — 解包
3. 编辑 `word/styles.xml`（表格风格）、`word/document.xml` 的 `<w:sectPr>`（页边距）、新增 `header1.xml`/`footer1.xml`（页码）
4. `python ooxml/scripts/pack.py unpacked/ output.docx` — 重新打包

docx-js 仅用于无公式的纯格式文档。
