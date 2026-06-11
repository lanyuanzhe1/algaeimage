---
name: feedback-workflow
description: 工作流偏好 — 写完代码要验证、一个PR不拆分、不要结尾总结、不要emoji
type: feedback
---

**规则**:
- 每次写完代码后必须先运行验证（测试或实际运行），再声称完成
- 关联改动应捆成一个 PR，不要拆成多个小 PR
- 回复结尾不需要总结"完成了什么"，直接进入下一个话题
- 不要使用 emoji，保持文字简洁
- 每次犯错的纠正应自动沉淀为一条 feedback 记忆或 CLAUDE.md 规则

**Why**: 用户反复纠正过这些行为——验证确保代码真能运行，不拆分PR减少review往返，不总结减少冗余文字。

**How to apply**: 每次声称任务完成前运行验证命令。涉及 git 操作时默认一个分支一个 PR。回复保持精简，无 emoji。
