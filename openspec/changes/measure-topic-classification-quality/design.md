## Context

动机见[proposal](proposal.md)。2026-10-09用户选择直接采用v2并稍后人工标注；本change承接原change的8.1–8.5，不改变生产发布标准。现有工具已支持离线标注、身份分组、公共预测、指标与fail-closed质量收据；工具存在不代表真实gold或质量验收完成。

现有冻结数据位于`site/topics/evaluation/`：

| 项目 | 冻结值 |
|---|---|
| 来源 | `d49956853ecf5e74232d330dc4f889dab01b7dba:data/index.json` |
| baseline输入SHA256 | `e863f6bad2cda36d6702b6efb2c07ca2898af42d860cab6c8dce95d305aca422` |
| baseline生成时间 | `2026-10-09T05:23:56.835960+00:00` |
| annotation dataset canonical SHA256 | `ce538bfd834905c7f00d102babec0476d656e057f9e172c265764d0a9b1af38e` |
| 候选数 | 106条已审查dev + 122条未见holdout候选 = 228；人工gold=0 |
| split seed | `20261009` |

`baseline-input.json`、`annotation-dataset.json`与`dataset-manifest.json`是对应资产。以上hash锁定当前未标注候选，不是未来确认gold的hash；标注冻结后须另保存完整dataset及gold hash，保留来源链。不得为规划重抓或重建当前holdout。

## Goals / Non-Goals

**Goals:** 可复核的人工gold、隔离留出集、可比较v1/v2基线、仅dev校准、完整分母与独立质量结论。

**Non-Goals:** 本次不执行标注或holdout评分，不用AI标签替代人工，不修改生产分类/模型/阈值、不把gold重新设为当前v2上线硬门槛，也不将单元测试、浏览器或runtime通过称作质量通过。

## Decisions

### 人工确认与候选分开

使用`review_annotation.py`生成本地HTML或JSON审查产物，用户稍后安排人员阅读公开材料、独立复核，冲突由维护者定稿。每条保留reviewer、ISO reviewed_at和公开证据理由。AI只能提候选，未经确认不进入gold。相比自动填全标签，这会增加等待，但避免用分类器自证精度。`prepare_annotation.py`仅用于受控准备/替换，不覆写已审查标签。

标注研究范围、四研究维度、content_kind、domain_facets、状态、可接受完整标签集、broad_only/拒判理由。`fine_applicable=false`只允许research+broad_only且有明确父类；非研究及必须拒判者fine_applicable=true、gold空集。insufficient_evidence、taxonomy_gap和required_abstain不能带研究gold标签。四通用领域限定materials/chemistry/life_sciences/general_ai，对应web命名空间由现有adapter规范化。

### 固定组与评估隔离

现有106条已审查输入及全部audit/定义/强制回归同源组强制dev；保留dev≥88历史目标，但106条不得随机移入holdout。真实公开池总量≥148且holdout≥60，两条件加全部106 dev意味着至少166条，当前228候选数量足够但gold/支持未确认。holdout每个研究root≥10阳性、非研究/组织动态≥20；支持不足补未见公开材料，不用来源查询推断标签。

按DOI、显式arXiv、规范URL及标题别名分组，转载/版本同组。预测前排除私有参考、exact和manual override中的holdout身份；私有库仅在本地内存或0600临时文件，不进外部LLM、日志、公共archive/artifact/cache。泄漏检查0违规才接受测量。冻结配置前分类作者只读dev与预定支持汇总，不读holdout标题/逐条错误；若错误用于调参，旧holdout转dev并收集新未见holdout。

### 同输入比较与dev校准

`predict_evaluation.py`两backend统一使用稳定taxonomy及完整私有身份corpus，先排除holdout，再分别重跑v1算法/v2；不直接比较旧archive的不同输入标签。exact-seen另报，不进unseen主指标。先保存冻结v1质量与耗时，再仅dev比较lexical/semantic/fusion的分维阈值、分差和置信度，记录选择依据、代码/catalog/definition/threshold/override/model revision和配置hash。默认生产采用与量化实验互不自动影响。

### 评分与门槛

fine只取显式最具体标签并移除展示祖先；可接受替代完整集合在gold冻结，按集合F1最大、并列按ID字典序确定，与v1使用同规则。细类gold只预测父类计FN且父类非fine TP；根指标按ancestor closure每条每根一次。research+broad_only排除fine分母，单报父类匹配和过度细分。non_research/required_abstain的研究预测计FP，研究拒判计FN。

| 后续目标 | 分母/规则 |
|---|---|
| root precision≥95% | 全holdout预测根标签 |
| fine micro P≥90%、R≥75%、F1≥80% | fine_applicable unseen，含非研究/必须拒判负例 |
| 相对v1 F1≥5pp提升 | 同固定split；v1≥95%时保持且修复强制反例 |
| 支持root F1下降≤5pp | 有足够支持的各root分别比较 |
| 非研究误入≤5% | gold非研究/组织动态，至少20条 |
| eligible coverage≥70% | 足证据且目录可表达的gold研究条目 |
| content_kind macro F1≥90% | 内容性质独立支持/混淆矩阵 |
| domain_facets micro F1≥85% | 通用领域独立支持/混淆矩阵 |
| broad_only过度细分≤5% | 人工只能判定父类样本，另报支持和父类匹配 |

支持≥5类做macro F1；更低支持全部报告；空分母N/A。scope/status/content_kind/domain独立混淆矩阵，taxonomy_gap不能混作non_research；分别报告目录缺口、证据不足、域外分母。precision/recall CI按item group bootstrap，固定seed。所有目标是未来验收目标，不能宣称当前已达90%。

### 收据闭环

`run_evaluation.py`输出公开汇总report，不向分类作者输出holdout错误。独立确认收据绑定dataset hash；private_exclusionverified同时绑定normalized predictions SHA256、防止另次预测借用收据。保存有效分母、支持、P/R/F1/CI、拒判/失败分布、基线diff、耗时及全部版本hash。缺gold、支持、排除证明或版本时质量门禁fail-closed并保持unmeasured/N/A，不影响2026-10-09已授权默认v2技术发布。技术/runtime/浏览/原生Pages回滚收据由原change验收，本change引用其版本，不替代真实质量。

## Risks / Trade-offs

- [人工gold尚未安排] → 所有承接任务未勾，等待用户稍后人工确认，不自动填gold。
- [某类支持不足] → 补独立未见公开样本，空分母N/A，不能删弱类或宣称全目录通过。
- [留出错误污染规则] → 独立评估隔离，污染后换holdout并记录新来源/hash。
- [两个active change同名能力] → 原change的classification-evaluation已同步main；本change只ADDED五个不同名的细化要求，不替换或覆盖当前发布契约，实施后归档时再核对。

## Migration Plan

原change8.1–8.5保留未勾并逐项链接本change1.1–1.5。本次只建立承接；以后按人工gold→分组冻结→v1→dev校准→独立holdout顺序执行并交付证据。测量配置与生产配置分开，失败保留原冻结输入/报告；任何生产调整另经可回滚技术发布，不由本change评分自动部署。
