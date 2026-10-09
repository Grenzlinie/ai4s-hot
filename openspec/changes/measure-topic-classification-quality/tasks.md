## 1. Deferred independent measurement

2026-10-09用户选择直接采用新版、稍后人工标注。以下承接原change8.1–8.5，全部为后续独立量化，不阻塞默认v2技术发布；本次只建立规划，不将工具存在、候选标签或技术测试当作任务完成证据。数据、指标与分母以[design](design.md)及[spec](specs/classification-evaluation/spec.md)为准。

- [ ] 1.1 （承接原8.1 / 原1.2）用现有`review_annotation.py`生成可审查HTML/JSON，用户稍后安排公开材料阅读、人工标注与独立复核；输出确认gold及reviewer/ISO时间/公开理由/冲突定稿记录。依赖冻结候选来源；验收：至少148真实公开样本且保留全部106已审查dev、补足未见holdout要求，四维/范围/kind/domain/status/拒判完整，候选不算gold、非法fine_applicable被拒绝，记录人工确认实际数量与gold hash。
- [ ] 1.2 （承接原8.2 / 原1.3）按canonical身份及别名冻结分组split与manifest，输出来源commit、seed=20261009、候选/gold hashes及支持数，检查参考/exact/override排除。依赖1.1；验收：全部106已审查及audit/定义/回归组为dev（≥88）、未见holdout≥60，四root各≥10阳性、非研究/组织动态≥20，T19泄漏0违规；不足则补未见样本，当前228候选hash见design且不得假定已满足gold支持。
- [ ] 1.3 （承接原8.3 / 原1.4）用`predict_evaluation.py --backend v1`在共同稳定taxonomy/完整身份参考上重跑同输入基线，`run_evaluation.py`保存公开汇总质量及耗时。依赖1.2；验收：有效分母、支持、P/R/F1/CI、父类-only/过度细分、拒判分布、版本及prediction hash齐全，holdout参考先排除、exact-seen另报，不以旧archive不同输入或56/88代替准确率。
- [ ] 1.4 （承接原8.4 / 原3.5）仅dev比较词语v2/语义/融合，校准分维阈值、分差、置信度并冻结选择依据、代码/catalog/definition/threshold/override/model revision及配置hash。依赖1.2和原change候选/decision能力；验收：独立记录无读取holdout错误调参，配置冻结与基线兼容，若污染则换holdout；不自动调整生产配置。
- [ ] 1.5 （承接原8.5 / 原6.2）独立评估者在冻结gold/config后运行holdout并交付公开aggregate evaluation report及绑定dataset+normalized predictions SHA256的排除收据。依赖1.3/1.4及原change技术证据；验收：核对root P≥95%、fine P/R/F1≥90%/75%/80%、相对v1≥5pp或高基线例外、支持root降幅≤5pp、非研究误入≤5%、eligible coverage≥70%、kind macro F1≥90%、domain micro F1≥85%、broad_only过度细分≤5%，报告所有支持/低支持类/独立分母/CI；缺gold/支持/排除证明fail-closed、空分母N/A，不把runtime/browser/Pages通过当质量通过，不向分类作者暴露holdout错误供调参。
