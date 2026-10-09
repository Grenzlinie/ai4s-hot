# AI4S Hot 的 OpenSpec 管理

当前CLI基准为OpenSpec 1.13.0，使用spec-driven流程及项目内Codex skills。遵循[官方工作流](https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md)组织 proposal、design、delta specs 和任务；OpenSpec结构校验不代表功能或质量已验收。

## 当前状态

- `specs/`：3份从现有实现核对的分类相关基线（同步、匹配、浏览）；不是所有项目功能都已建spec。
- `changes/improve-zotero-topic-classification/`：此次完整改进方案，含审查、架构、5份delta spec、验收计划及30项实施任务。
- 方案阶段已完成；业务实现未开始，任务全部未勾选，不提前archive。
- `roadmap.md`：里程碑、依赖和独立的运行问题。

## 文件职责

| 文件 | 用途 |
|---|---|
| `config.yaml` | 项目上下文和文件规则 |
| `specs/*/spec.md` | 已实现行为的规范基线 |
| `changes/*/proposal.md` | 问题、范围及能力变化 |
| `changes/*/design.md` | 方案、兼容、迁移与数据边界 |
| `changes/*/specs/*/spec.md` | 要实现的行为与场景 |
| `changes/*/evaluation-plan.md` | 标注分母、质量/性能/浏览验收 |
| `changes/*/tasks.md` | 执行顺序、输出、依赖与完成证据 |

## 常用命令

在仓库根目录运行，以下CLI命令现已可用：

```bash
OPENSPEC_TELEMETRY=0 openspec list
OPENSPEC_TELEMETRY=0 openspec list --specs
OPENSPEC_TELEMETRY=0 openspec status --change improve-zotero-topic-classification
OPENSPEC_TELEMETRY=0 openspec validate --all --strict --no-interactive
```

新增行为先创建change并核对已实现spec；实施按任务推进。只有真实通过才能勾选，结构校验、离线测试、人工标签质量、浏览器与生产收据各自记录。完成后archive才将delta并入主spec。新增的分类CLI、标注工具和CI均是本方案待实现输出，不要把设计中的路径当成现有命令。

在Codex中可用项目生成的 `$openspec-propose` 规划或 `$openspec-apply-change` 实施，直接用自然语言提出同样请求也可。用户要求设计时止于设计，之后的实施以新的实施请求为准。
