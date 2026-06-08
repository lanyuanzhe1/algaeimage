---
name: vue3-over-streamlit-decision
description: User chose Vue3+FastAPI over Streamlit for the competition platform after evaluating both options
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7ba30ed0-3357-492f-afb3-777f68798a93
---

User explicitly chose Vue3 + Element Plus + ECharts over Python + Streamlit for the competition demo platform.

**Why**:
- Competition needs both algorithm visualization (step-by-step pipeline) AND complete product feel
- Streamlit is server-rendered, limited interactivity
- Vue3 SPA provides richer UI control: drag-drop upload, animated pipeline steps, interactive charts
- The existing `core_engine/` pure Python layer stays intact regardless of frontend choice

**How to apply**:
- Never suggest Streamlit or other Python-only UI frameworks for this project
- When adding UI features, use Vue3 Composition API + Element Plus components
- Backend stays FastAPI thin layer; all heavy logic stays in core_engine/
- Related: [[echarts-registration-requirement]]
