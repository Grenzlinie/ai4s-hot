# AI4S Hot 项目规则

本文件只补充本仓库范围的规则，用户当前明确指令优先。

## 项目事实

- 代码：`site/`；配置同步：`scripts/configure.py`；公开归档：远端 `site-data` 分支。
- Python 采集与静态前端通过 GitHub Actions / Pages 运行，不需要邮件配置。
- Zotero 分类同步不意味着网站生成的标签是用户的真实收藏分类；自动标签必须标明推断性质。
- 库内记录、collection key、参考向量、凭据不得进入公开归档或 OpenRouter 摘要请求。

## OpenSpec 工作方式

- 先读 `openspec/config.yaml`、`openspec/README.md` 和相关已实现 spec。
- 新的功能或行为变化进入 `openspec/changes/<change>/`，包含 proposal、design、delta specs、tasks。
- 设计轮只维护方案；实施轮依据 change 的任务推进，用户的实施请求决定授权范围。
- 本次活跃方案：`improve-zotero-topic-classification`。当前 v2 为影子实施，人工质量验收待完成；默认生产分类仍为 v1。任务状态以 tasks.md 与 evidence.md 为准，不能把结构校验或逻辑测试写成分类质量达标。
- 验收证据区分：OpenSpec 结构校验、离线逻辑测试、冻结标注集质量、真实浏览器、GitHub Actions 和线上读回。
- 实施完成且证据齐全后再 archive，更新 `openspec/specs`；不得提前合并未来需求为已实现行为。
- 代码变更执行相称的独立测试；只有变更、失败或未解决疑点时重复扩大检查。
