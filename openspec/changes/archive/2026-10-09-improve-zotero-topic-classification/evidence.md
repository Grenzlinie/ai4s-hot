# 实施证据索引

当前状态（2026-10-09）：用户最新明确“直接采用新版”，最终提交`72cd88d6ba746478434692c0b28e016a543cc438`已推送，默认v2已发布并HTTP读回，不新增opt-in/selector。真实质量为`unmeasured`；人工gold目前0，dev校准和holdout质量属于Deferred measurement，不阻塞本次上线，也未完成。Pages `37892904488`、CI `37892904490`、semantic shadow `37892914767`均成功；原生恢复与HTTP读回完成。该段为72cd历史验收；最终a461的失败尝试状态、原生故障注入、完整回滚/恢复及健康更新见文末。延期量化独立承接，保持未完成。

当前离线汇总：148/148 Python测试，前端29+37=66行为断言；真实Chrome 1440px/390px矩阵25+4=29项通过，另有2项新版标记检查（仅路由调整公开fixture的schema，用于UI标记，不是分类质量）。本机回滚9项通过但未替代远端原生恢复/部署收据。下方历史段落保持当时版本与边界，任何“默认v1/未部署”等描述仅指历史验证时点。

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

## 历史独立离线验证（2026-10-09，保留当时版本与状态）

独立 Agent 执行 `../site-venv/bin/python -m unittest discover -s site/tests`：108/108 通过。新增 `test_shadow_safety.py` 的8项合成回归通过：mock Zotero 私有语料只在内存使用；公开影子文件和日志无私有 sentinel；采集异常仅输出异常类型且不创建 artifact；无效公开字段、嵌套 classification/override 私有字段和未知/重复身份被拒绝；原子写入校验失败保留原文件；按 item 选择的 backfill 仅传入对应 overrides，保留 v1 alias 迁移。测试对所有修改环境变量的 CLI 调用恢复环境，生产缺省仍为 v1。

对 `.github/workflows/topics-shadow.yml` 的静态检查确认 `contents: read`，仅上传 `${{ runner.temp }}/public-shadow`，无生产提交或 Pages deploy 步骤。上述结果是合成离线测试及 workflow 静态审查；未读取真实凭据或 holdout 标题，也不证明原生 Actions 运行、分类准确率或浏览器验收完成。

后续新增 `test_v2_wrapper.py`，执行 `../site-venv/bin/python -m unittest discover -s site/tests -p test_v2_wrapper.py -v`：6/6 通过。直接覆盖 v2 wrapper 的读异常、空 snapshot、未配置时保留 last valid/last_success 与异常消息清洗；stale 分类不改已有标签；仅白名单内 research records 进入内存 corpus，排除未发布分类、note、attachment 和额外私有字段。仅检查 baseline 的公开 taxonomy，确认53个节点路径与 catalog 中53项 authored 定义唯一且一一对应；这不替代生产 catalog schema validator 或语义质量评估。

生产新增 `topics_catalog.validate_catalog/load_catalog` 后，独立新增 `test_catalog.py`，6/6 通过：实际53项 catalog 合法；私有未知字段、重复路径、空定义、非法/重复 terms、状态/rules 枚举及 website facet ID 边界均拒绝，错误消息不含注入的私有值。classifier 的简化 fixture 已补齐合法 schema，没有绕过 validator；受影响核心测试21/21 通过。该证据证明结构验证，不证明定义内容的分类准确率。

新增按轴阈值和语义后端合成回归 `test_thresholds.py`，7/7 通过：各轴 min_score/relative_score/margin/quota 独立生效、其他轴不占配额、非法数值/枚举/未知轴/私有字段拒绝、阈值变更使缓存失效、非法配置在候选执行前停止；省略 backend 的 lexical 默认经回归发现并修复。semantic/fusion 在低词语 coverage 下仍能依据语义候选决策、method 记录实际后端，语义分数限制在[0,1]；依赖失败的 degraded 结果记录 lexical method。受影响核心测试21/21再次通过。语义模型全程 mock，未下载或调用模型；没有校准阈值或证明质量提升。

回滚准备独立验证：`test_deployment_contract.py` 6/6 通过，随后全量 Python 离线测试141/141通过。覆盖新UI支持v1/v2、legacy UI仅支持v1且在生成目录前拒绝v2、40hex immutable revision、精确asset/index SHA256、无LLM请求标记、标签facet根/score有限范围/closure/枚举校验。发现并修复 manifest 的v1 classification私有字段旁路；build与manifest均验证公开archive，两个schema的私有注入拒绝。静态审查 `pages-restore.yml` 确认默认仅build review artifact，只有显式publish才上传Pages并deploy；build只读contents且未引用Secrets或执行采集/LLM。此证据仍不是原生Actions回滚执行收据。

最终迁移契约回归：`test_shadow_safety.py` 10/10通过。v2显式标签必须一对一公开receipt，v1允许缺省；首次v1→v2按item局部迁移在读取私有源之前拒绝且不产出文件。合法v2 selective backfill仅分类选中item，完整迁移所有已有receipt的id/facet，未选item公开reason/score/method等原样保留。

用户授权直接采用v2后，独立新增实际模块集成 `test_v2_publication_integration.py`：2/2通过。仅mock Zotero与新闻输入，真实执行 collector→v2 identity/classifier→公开schema验证→build→manifest，确认schema2、exact标签receipt、quality_status=unmeasured、calibration_status=pending_human_gold与私有sentinel不公开。workflow静态验证TOPICS_MODE=v2/私密配置Secret已传入、build成功后才commit site-data、manifest成功后才上传Pages，无always绕过。最后全套Python148/148通过、前端行为29断言与explorer37断言通过。失败不覆盖远端快照仅由workflow步骤顺序和默认success guard证明，未执行远端故障注入；未部署、提交或读取真实凭据，浏览器/Pages/原生Actions仍由主Agent验收。

失败保留实现后的独立验证：新增 `test_failure_retention.py` 8/8通过，最新全套Python160/160、前端29断言及explorer67断言通过。末项分类异常和curation异常均不提交工作副本；同步/分类失败保持原index与daily字节且不调用summary；退役label receipt保留history，schema拒绝unknown及active历史引用；status拒绝私有字段/非法identity类型，发布前剔除未归档failed_item_id。实际维护probe在无网络/summary条件下经真实collector和classifier故障路径验证两个stage均返回2且保留旧档。发现非法timestamp异常会重复私有输入，修复为固定安全消息后回归通过。workflow静态确认仅collect+candidate成功才提交candidate，失败分支从预先记录的immutable archive重建并公开匿名status；这些离线/静态证据不替代远端故障注入和HTTP读回。

## 当前技术完成项与对应证据

| 任务 | 证据 | 边界 |
|---|---|---|
| 3.1 | `site/topics_{corpus,candidates,decision,classifier,schema,reclassify}.py`；`test_topics_v2_core.py`、`test_core_independent.py`、`test_thresholds.py` | 乱序、完整签名/阈值/backend失效、公开不透明收据；不是准确率证明 |
| 3.3 | `test_topics_v2_core.py` T03–T08，catalog/thresholds独立回归 | 四轴、冷启动、OOV、组织范围与证据不足合成检查 |
| 4.3 | `browser/version-marker/results.json`的纠错打开/本机生效/刷新/公开导出，`test_identity_curation.py`导入校验 | 访客修正本机范围，CLI维护者导入；无前端写凭据 |
| 5.2–5.5 | `site/topics/evaluation/evidence/browser/version-marker/results.json`25项、`combinations.json`4项；同目录`input-manifest.json`绑定静态资源 | 真实Chrome 154.0.8037.99、1440×1000/390×844；树键盘、搜索、URL历史、手机焦点、纠错与空结果；公开理由另经schema/privacy测试 |
| 6.1 | 历史独立验证中的全套148项Python和66项前端断言；对应测试文件保留 | 合成/集成契约，未给真实holdout精度 |
| 7.1 | `.github/workflows/site-ci.yml`固定`@fission-ai/openspec@1.13.0`，本索引与strict 4/4 | CI行为已实现；最终72cd原生CI运行结果仍单独等待 |

浏览器完整说明、初次矩阵、截图与本机回滚：`site/topics/evaluation/evidence/browser/README.md`、`results.json`、`combinations.json`、`rollback.json`。新版标记复验在`browser/version-marker/`；其2项标记检查只改变公开fixture的schema，不冒充真实v2精度或线上读回。本机旧UI不能解析新版q/topics URL筛选，限制已如实保留；收藏、已读、纠错数据及恢复新版后的URL状态通过。

## 原生运行与当前待补证据

- 历史旧提交`fe70`词语影子[37891067362](https://github.com/Grenzlinie/ai4s-hot/actions/runs/37891067362)成功，不替代最终提交的原生收据。
- 最终`72cd88d6`：[Pages 37892904488](https://github.com/Grenzlinie/ai4s-hot/actions/runs/37892904488)、[CI 37892904490](https://github.com/Grenzlinie/ai4s-hot/actions/runs/37892904490)、[semantic shadow 37892914767](https://github.com/Grenzlinie/ai4s-hot/actions/runs/37892914767)在本次文档快照进行中。最终状态、500/200 cold/warm收据和默认v2 HTTP读回待补；job绿色不能替代runtime_pass。
- 真实远端恢复/回滚、每日分类/同步失败不覆盖有效快照的故障注入，以及最终默认版本/前端/归档HTTP一致性尚未记为完成；本机回滚和workflow success guard不是这些原生收据。
- 3.6逐条error状态尚缺具体失败收据，保持未勾；语义模型原生运行尚未验收，3.4保持未勾；未测后端不默认启用。
- Deferred measurement：人工确认gold、四轴/非研究支持数、独立复核、同源排除量化、v1同输入质量基线、dev选择依据、冻结holdout指标。保留未完成状态，按用户最新决定不阻塞直接采用新版。

## 历史本机性能与实现验证（非最终原生验收）

本机固定500/200词语测试：500实际去重参考（可用521）、200公共输入；cold26.238s/warm18.346s，RSS83,968,000/83,623,936bytes；来源为`runtime-local-informational.json`。代码当时未提交，收据明确dirty；只能作为本机流程/性能信息，不能替代native runner或质量验收。

2.4：`test_v2_wrapper.py` 6项验证v2失败保留、范围读取和最后有效目录；`topics_schema.py`版本与引用验证。3.7：`test_shadow_safety.py`选择backfill、alias迁移、override缩小范围、原子写拒绝保留原档；真实本地影子原子写完成且未请求LLM。

## 默认新版生产读回（72cd88d6）

原生 CI `37892904490` 和 Pages `37892904488` 均成功。HTTP manifest 读回 code_revision=72cd88d6ba746478434692c0b28e016a543cc438，archive_revision=1aeb22e303b9229097f83d13dc31d7ceb0c0e1bd；线上 schema2、53主题、53条旧ID alias、110内容（76论文/30报告/4发布），分类算法faceted-local-v2.3、quality_status=unmeasured。与上一公开归档107条比较，原ID及first_seen全部保持，新增3条；完整schema验证与archive SHA256一致。证据见 `site/topics/evaluation/evidence/native/publication-http.json` 与 deployment-manifest.json。summary.classified 表示本次处理110条，不是细分类成功数或准确率。

独立 Agent 使用真实Chrome154在正式网址验证13项通过，显式1440×1000和390×844视口：默认schema2/未量化标记、structured labels、旧主题URL→稳定ID、收藏与已读刷新保留、手机抽屉/焦点/Esc、无溢出和页面异常。证据 `site/topics/evaluation/evidence/browser/live-v2/`。

只读恢复预览 `37893133065` 成功。实际回滚 `37893230406` 已成功发布上一公开归档b83dd0839f18a599fc7b883cbee5b8d39915a1fe，使用新版前端；恢复默认v2的原生运行和HTTP收据另补。此处不将旧归档缺少新ID alias的筛选限制算作通过。

## 最终原生性能与恢复验收

最终代码72cd88d6影子run 37892914767成功，已下载并审查public artifact。Ubuntu24.04、Python3.13.16、4CPU，500真实去重参考/200公开输入：lexical cold22.4929s/warm20.2148s、RSS63,496,192/63,373,312bytes；semantic实际后端非degraded，cold127.9181s/warm121.2323s、RSS1,712,734,208/1,686,589,440bytes。两个runtime_pass均true、quality_pass均false（未量化）。收据见site/topics/evaluation/evidence/native/runtime-{lexical,semantic}.json；性能不代表准确率，生产默认仍lexical。

恢复默认v2 run 37893363352成功；HTTP读回archive1aeb22e303b9229097f83d13dc31d7ceb0c0e1bd、schema2、archive SHA256与原发布一致。独立真实Chrome10项恢复检查通过：收藏/已读、本机修正storage字节保持，v1旧zt修正在v2映射stableID，URL主题与关键词恢复；见browser/live-rollback-restore/。实际旧归档浏览器9项前置检查通过，但最后旧stableURL说明断言失败且未完整写首轮收据；partial-attempt为tool trace重建，不宣称完整回滚浏览器矩阵通过，限制已写手册。

只读故障注入37893443923使用旧前端f085+新schema2，按预期在build报Frontend does not support this archive schema，无archive写权限且deploy跳过；失败后HTTP仍为有效v2。这证明兼容构建fail-closed，不冒充真实Zotero接口故障注入。分类/同步异常保留由离线wrapper/原子写与workflow guard验证；逐条异常error收据尚未实现，3.6保持未勾。

## 最终完成审计（a461364，替代此前待补状态）

独立 Agent 再次逐项核对5份delta的24个requirements、39个scenarios，未发现尚未实现的本次技术要求。最终修复：分类采用批次副本事务、v2目录同步失败立即停止归档写入、摘要在分类/公开schema校验成功后才运行；error是独立更新尝试状态，保留上次分类，不以空标签伪装错误；topic_history保留退役显式标签，浏览器可浏览归档主题但不能将其作为有效新纠错；缺定义的新公开目录用名称/父路径建立低confidence候选，词语与语义共用公开fallback。

独立执行160/160 Python测试，前端29+67=96断言；新增failure_retention8项含第二条分类异常、curation异常、同步/分类失败旧index/daily字节不变和零summary/API、历史标签、状态白名单及immutable保留workflow。真实Chrome本机29项矩阵+20项退役/sidecar/回滚fixture通过；fixture不作为native证据。

最终正式代码a46136428a041984850368328de406436ceed2bc，CI37894330283成功，正常Pages37894330336成功。原生故障注入taxonomy37894554091和classification37894654207：受控collector退出2，原始archive SHA256始终013207a2cdd65df08642b3fa6e901dfee16e44ee1661489344b87d9865506e10，site-data commit被跳过，只有先前immutable archive及匿名update-status sidecar部署；真实页面错误阶段可见，收藏/已读/本机纠错保持。工作流success表示保留部署成功，不表示本次分类成功。

原生回滚37894759805、恢复37895016891、正常健康更新37895143455全部成功；最终真实Chrome六阶段15+8+9+12+18+14=76次检查完整通过，证据见site/topics/evaluation/evidence/browser/native-final/。历史schema1不可用stable筛选明确提示清除并保留关键词，纠错存储字节保持且标待复核；恢复schema2后旧alias、有效纠错和阅读状态恢复，1440/390视口及抽屉焦点正常。

最终主Agent HTTP独立读回：schema2，110内容/53主题，algorithm faceted-local-v2.4，quality_status unmeasured，update-status ok/run37895143455，无故障banner；archive17231ace5bdbcb517f9e0008b84ddee23934c58d，SHA256 ac78e4a8b7692a54b14a8c348a37ce3dc7d68a37635e45ab3dcc2292c9c6f460。与上次110内容逐项比较，ID和first_seen全部保持。

原生runtime37894338419已下载实际收据：4CPU Ubuntu24.04/Python3.13.16，500真实去重参考/200公开输入，lexical cold18.8985s/warm22.3557s、RSS62,820,352/63,340,544bytes；semantic真实非degraded cold129.1203s/warm123.8363s、RSS1,701,859,328/1,688,432,640bytes。两者runtime_pass true，quality_pass false（未量化）；生产默认lexical。证据site/topics/evaluation/evidence/native/a461/。

本次27项技术任务完成。原8.1–8.5的5项真实质量任务没有完成或勾选，已逐项转交active change measure-topic-classification-quality；用户明确稍后标注、直接采用新版。当前不报告精度达标。已实现delta同步main，技术change归档保留延期记录，后续量化独立执行。
