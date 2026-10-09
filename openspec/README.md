# AI4S Hot 的 OpenSpec 管理

当前CLI基准为OpenSpec 1.13.0，使用spec-driven流程及项目内Codex skills。遵循[官方工作流](https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md)组织 proposal、design、delta specs 和任务；OpenSpec结构校验不代表功能或质量已验收。

## 当前状态

- `specs/`：3份历史已实现基线；本次新增行为尚未archive，5份delta仍在active change，不把规划状态当作生产能力。
- `changes/improve-zotero-topic-classification/`：实施、证据索引、验收计划及32项任务（含明确延期的5项量化任务）。
- 2026-10-09用户最新选择“直接采用新版”：本次默认v2发布，不新增opt-in/selector；质量为`unmeasured`，人工gold/校准/holdout量化独立延期，不阻塞发布、不伪造完成。
- 已完成148项Python测试、66项前端行为断言；1440px/390px真实Chrome的29项矩阵及本机回滚有独立收据。它们不代表分类准确率。
- 提交`72cd88d6ba746478434692c0b28e016a543cc438`已推送；最终Pages `37892904488`、CI `37892904490`及semantic shadow `37892914767`全部成功。默认v2已在线，原生回滚/恢复及HTTP读回完成；历史归档筛选兼容限制见运行手册。
- 冻结指定commit实际106条，全部dev；另122条未见候选，人工gold仍0。`roadmap.md`及change的`evidence.md`分别记录路线与证据边界。

## 文件职责

| 文件 | 用途 |
|---|---|
| `config.yaml` | 项目上下文和文件规则 |
| `specs/*/spec.md` | 已实现行为的规范基线 |
| `changes/*/proposal.md` | 问题、范围及能力变化 |
| `changes/*/design.md` | 方案、兼容、迁移与数据边界 |
| `changes/*/specs/*/spec.md` | 要实现的行为与场景 |
| `changes/*/evaluation-plan.md` | 标注分母、质量/性能/浏览验收 |
| `changes/*/tasks.md` | 执行顺序、输出、依赖与完成证据；延期量化单列 |
| `changes/*/evidence.md` | 当前收据索引及明确标注的历史验证记录 |

## 常用命令

在仓库根目录运行，以下CLI命令现已可用：

```bash
OPENSPEC_TELEMETRY=0 openspec list
OPENSPEC_TELEMETRY=0 openspec list --specs
OPENSPEC_TELEMETRY=0 openspec status --change improve-zotero-topic-classification
OPENSPEC_TELEMETRY=0 openspec validate --all --strict --no-interactive
```

新增行为先创建change并核对已实现spec；实施按任务推进。只有真实通过才能勾选，结构校验、离线测试、人工标签质量、浏览器与生产收据各自记录。完成后archive才将delta并入主spec。分类、标注、预测与性能CLI以及固定OpenSpec版本CI现已实现；各能力与生产验收边界以`tasks.md/evidence.md`为准。CLI可运行不等于真实质量或最终Pages上线已通过。

在Codex中可用项目生成的 `$openspec-propose` 规划或 `$openspec-apply-change` 实施，直接用自然语言提出同样请求也可。用户要求设计时止于设计，之后的实施以新的实施请求为准。
