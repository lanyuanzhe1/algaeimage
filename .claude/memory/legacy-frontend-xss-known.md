---
name: legacy-frontend-xss-known
description: "frontend_legacy/ contains known XSS vulnerabilities — intentionally unfixed, replaced by Vue3"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7ba30ed0-3357-492f-afb3-777f68798a93
---

Security review flagged stored XSS in `frontend_legacy/js/dashboard.js` and `frontend_legacy/js/app.js` (unescaped IDs in inline onclick handlers, incomplete HTML attribute escaper).

**Why unfixed**:
- `frontend_legacy/` is the old vanilla HTML/JS frontend, fully replaced by Vue3 (`frontend/src/`)
- Kept only as reference/backup — never served in production
- Vue3 rewrite eliminated all string-concatenation-based HTML construction

**How to apply**:
- Do not spend time fixing legacy JS security issues
- If someone asks to bring back the old frontend, redirect to Vue3 instead
- If frontend_legacy/ is no longer needed as reference, it can be deleted entirely
