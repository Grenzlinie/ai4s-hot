# 实施证据索引

当前状态：v2 影子实施；生产默认 v1；用户在 2026-10-09 选择“先保持影子测试，稍后标注”。人工质量、dev 校准、留出评分和最终切换均未完成，不 archive。

| 任务 | 已完成证据 | 边界 |
|---|---|---|
| 1.1 | `site/topics/evaluation/baseline-input.json` + `dataset-manifest.json` | 指定commit实际106条；原方案88条记录错误，完整保留dev |
| 2.1 | `topics_identity.load_private_config`；`scripts/configure.py --topics-private`；真实0600配置与Secret同步成功 | 私密值不进入argv/公开变量/日志 |
| 2.2 | `topics_identity.registry_from_collections`、CLI dry-run；`test_identity_curation.py`、`test_identity_independent.py` | HMAC128bit、rename/reparent、retired、alias攻击、false根、孤儿/循环/歧义拒绝 |
| 2.3 | `site/topics/catalog.yaml` 53节点、web facets；catalog_path绑定 | 全部公开人工编写定义，冷启动明确低confidence；质量未证明 |
| 3.2 | `topics_corpus.py`与`test_topics_v2_core.py` | DOI/arXiv、标题冲突、去重与乱序确定性；exact分开 |
| 4.1/4.2 | `topics_curate.py` strict CLI、人工覆盖/history/needs_review测试 | 本机和全站范围分开；无Zotero写入 |
| 5.1 | `test_topic_explorer.cjs` 33断言 + 原29断言 | OR/AND、计数和URL逻辑；不是浏览器证明 |
| 本机影子 | 53主题、532参考、106公开输入；Zotero20.147s、词语分类1.052s、峰值76,251,136bytes | macOS本机词语后端；不是500/200 native runner或准确率证明 |
| OpenSpec结构 | `openspec validate --all --strict` 4/4 | 仅结构合法，不计实现/质量完成 |

## 独立离线验证（2026-10-09）

独立 Agent 执行 `../site-venv/bin/python -m unittest discover -s site/tests`：108/108 通过。新增 `test_shadow_safety.py` 的8项合成回归通过：mock Zotero 私有语料只在内存使用；公开影子文件和日志无私有 sentinel；采集异常仅输出异常类型且不创建 artifact；无效公开字段、嵌套 classification/override 私有字段和未知/重复身份被拒绝；原子写入校验失败保留原文件；按 item 选择的 backfill 仅传入对应 overrides，保留 v1 alias 迁移。测试对所有修改环境变量的 CLI 调用恢复环境，生产缺省仍为 v1。

对 `.github/workflows/topics-shadow.yml` 的静态检查确认 `contents: read`，仅上传 `${{ runner.temp }}/public-shadow`，无生产提交或 Pages deploy 步骤。上述结果是合成离线测试及 workflow 静态审查；未读取真实凭据或 holdout 标题，也不证明原生 Actions 运行、分类准确率或浏览器验收完成。

后续新增 `test_v2_wrapper.py`，执行 `../site-venv/bin/python -m unittest discover -s site/tests -p test_v2_wrapper.py -v`：6/6 通过。直接覆盖 v2 wrapper 的读异常、空 snapshot、未配置时保留 last valid/last_success 与异常消息清洗；stale 分类不改已有标签；仅白名单内 research records 进入内存 corpus，排除未发布分类、note、attachment 和额外私有字段。仅检查 baseline 的公开 taxonomy，确认53个节点路径与 catalog 中53项 authored 定义唯一且一一对应；这不替代生产 catalog schema validator 或语义质量评估。

生产新增 `topics_catalog.validate_catalog/load_catalog` 后，独立新增 `test_catalog.py`，6/6 通过：实际53项 catalog 合法；私有未知字段、重复路径、空定义、非法/重复 terms、状态/rules 枚举及 website facet ID 边界均拒绝，错误消息不含注入的私有值。classifier 的简化 fixture 已补齐合法 schema，没有绕过 validator；受影响核心测试21/21 通过。该证据证明结构验证，不证明定义内容的分类准确率。

新增按轴阈值和语义后端合成回归 `test_thresholds.py`，7/7 通过：各轴 min_score/relative_score/margin/quota 独立生效、其他轴不占配额、非法数值/枚举/未知轴/私有字段拒绝、阈值变更使缓存失效、非法配置在候选执行前停止；省略 backend 的 lexical 默认经回归发现并修复。semantic/fusion 在低词语 coverage 下仍能依据语义候选决策、method 记录实际后端，语义分数限制在[0,1]；依赖失败的 degraded 结果记录 lexical method。受影响核心测试21/21再次通过。语义模型全程 mock，未下载或调用模型；没有校准阈值或证明质量提升。

回滚准备独立验证：`test_deployment_contract.py` 6/6 通过，随后全量 Python 离线测试141/141通过。覆盖新UI支持v1/v2、legacy UI仅支持v1且在生成目录前拒绝v2、40hex immutable revision、精确asset/index SHA256、无LLM请求标记、标签facet根/score有限范围/closure/枚举校验。发现并修复 manifest 的v1 classification私有字段旁路；build与manifest均验证公开archive，两个schema的私有注入拒绝。静态审查 `pages-restore.yml` 确认默认仅build review artifact，只有显式publish才上传Pages并deploy；build只读contents且未引用Secrets或执行采集/LLM。此证据仍不是原生Actions回滚执行收据。

最终迁移契约回归：`test_shadow_safety.py` 10/10通过。v2显式标签必须一对一公开receipt，v1允许缺省；首次v1→v2按item局部迁移在读取私有源之前拒绝且不产出文件。合法v2 selective backfill仅分类选中item，完整迁移所有已有receipt的id/facet，未选item公开reason/score/method等原样保留。

用户授权直接采用v2后，独立新增实际模块集成 `test_v2_publication_integration.py`：2/2通过。仅mock Zotero与新闻输入，真实执行 collector→v2 identity/classifier→公开schema验证→build→manifest，确认schema2、exact标签receipt、quality_status=unmeasured、calibration_status=pending_human_gold与私有sentinel不公开。workflow静态验证TOPICS_MODE=v2/私密配置Secret已传入、build成功后才commit site-data、manifest成功后才上传Pages，无always绕过。最后全套Python148/148通过、前端行为29断言与explorer37断言通过。失败不覆盖远端快照仅由workflow步骤顺序和默认success guard证明，未执行远端故障注入；未部署、提交或读取真实凭据，浏览器/Pages/原生Actions仍由主Agent验收。

## 待补证据

- 人工确认gold（目前0）、四轴阳性支持/非研究支持、独立复核、同源排除、v1同输入基线、dev选择依据、冻结holdout指标。
- 固定Ubuntu runner 500真实去重参考/200公共新内容 cold/warm 与本地语义候选RSS；不足500不可复制补足。
- 1440px/390px真实浏览器矩阵、发布/回滚收据、Pages HTTP读回。
- `.github/workflows/topics-shadow.yml`仅产出public-shadow artifact，无生产写入或deploy权限。benchmark步骤即使不满足门槛仍保存失败收据，job绿色不能代替收据runtime_pass。
- CI固定OpenSpec1.13.0并检查新前端逻辑。实际Actions链接将在运行后补入。

本机固定500/200词语测试：500实际去重参考（可用521）、200公共输入；cold26.238s/warm18.346s，RSS83,968,000/83,623,936bytes；来源为`runtime-local-informational.json`。代码当时未提交，收据明确dirty；只能作为本机流程/性能信息，不能替代native runner或质量验收。

2.4：`test_v2_wrapper.py` 6项验证v2失败保留、范围读取和最后有效目录；`topics_schema.py`版本与引用验证。3.7：`test_shadow_safety.py`选择backfill、alias迁移、override缩小范围、原子写拒绝保留原档；真实本地影子原子写完成且未请求LLM。
