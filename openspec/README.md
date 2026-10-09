# AI4S Hot 的 OpenSpec 管理

采用 OpenSpec 1.13.0 的 spec-driven 流程。结构校验、离线回归、真实浏览器、Actions、Pages HTTP 和人工质量评估分别记录；其中任何一种不替代其余证据。

## 当前状态

- `specs/`：6个已实现能力，30项要求；涵盖目录身份、分类、浏览、纠错及运行评估契约。
- `changes/archive/2026-10-09-improve-zotero-topic-classification/`：27项技术任务完成，实施和验收已归档；原5项延期量化保持未勾，不被当作完成。
- `changes/archive/2026-10-09-unify-discovery-navigation/`：9项阅读界面任务完成；独立站文案、多来源与统一推荐/最新浏览已上线，本地54/线上49项真实浏览器检查通过；外部主题服务503导致保留110条归档，实际状态见发布收据，不宣称已恢复。
- `changes/measure-topic-classification-quality/`：当前唯一活跃变更，逐项承接人工gold、冻结分组、共同输入基线、dev校准和独立holdout评分；gold=0，5项任务均未完成，等用户稍后标注。
- 生产默认v2.4，质量为`unmeasured`，不要求访客选择试用；160项Python测试、96项前端断言、76次最终原生浏览器检查通过。
- 真实runner的500参考/200公开输入、两后端冷暖预算、目录/分类故障保留、实际回滚恢复和最终健康Pages/HTTP均有证据。入口为归档变更的`evidence.md`，对应公开收据在`site/topics/evaluation/evidence/`。

## 文件职责

| 文件 | 用途 |
|---|---|
| `config.yaml` | 项目上下文和规范规则 |
| `specs/*/spec.md` | 已实现对外行为 |
| `changes/*/proposal.md`、`design.md`、`specs/` | 活跃需求及设计 |
| `changes/*/tasks.md` | 未完成工作与验收条件 |
| `changes/archive/*/evidence.md` | 历史实现和原生验收证据 |
| `roadmap.md` | 已完成路线与后续独立工作 |

## 常用命令

```bash
OPENSPEC_TELEMETRY=0 openspec list
OPENSPEC_TELEMETRY=0 openspec list --specs
OPENSPEC_TELEMETRY=0 openspec status --change measure-topic-classification-quality
OPENSPEC_TELEMETRY=0 openspec validate --all --strict
```

新行为先建立change；实施按任务推进，只有实际验收完成才勾选。实施并验收后同步主spec和归档；延期任务明确承接，不能为了归档标为完成。当前评估工具已存在，工具存在不代表人工质量测量已执行。
