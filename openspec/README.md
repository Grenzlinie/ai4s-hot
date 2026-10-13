# AI4S Hot 的 OpenSpec 管理

采用 OpenSpec 1.13.0 的 spec-driven 流程。结构校验、离线回归、真实浏览器、Actions、Pages HTTP 和人工质量评估分别记录；其中任何一种不替代其余证据。

## 当前状态

- `specs/` 记录8个已实现能力、37项要求，包括新期刊发现与期刊浏览。
- `changes/archive/2026-10-13-add-materials-journal-watch/`：10刊采集、独立多选、待确认隔离和统一分类已上线；223项Python、254项前端断言、真实本地与线上各19项浏览器检查通过。每次发布精确版本、来源partial和候选计数以该change的evidence及运行收据为准。
- `changes/add-public-content-enrichment/`：6项实施任务已完成，Bohrium预算与隐私检查见对应evidence；尚未归档，不与期刊变更混合。
- `changes/measure-topic-classification-quality/`：5项任务仍未完成，等待人工gold与独立质量测量；用户已明确取消它作为新版启用门槛。
- 2026-10-09的目录、分类和统一阅读界面历史验收保留在各自archive中；历史retention状态不代表今天的线上状态。
- 生产采用v2.4，主题及期刊相关性质量均未做独立人工准确率量化。技术回归、浏览器成功和真实采集数量不能替代质量指标。

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
