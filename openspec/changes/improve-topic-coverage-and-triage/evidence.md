# 分类覆盖修复验收

## 基线与实现

2026-10-26基线线上code431b938、archive869d4c，2282条归档：1621无topic、1577相关性待确认（其中1511无topic）、按新定义研究主题待分类77。分类/同步正常，未分类积压不是运行异常。

- v2.5：上下文收购/任命判定，修复真实14篇paper的acquisition误伤；缺摘要标题只用公开定义关键词命中，标明title-only及low置信。直接材料词可父类回退，单独molecular/chemistry不强归材料；弱标题仍不造标签。
- UI：相关性待确认独立；研究待分只看非pending/非non_research且无有效主题标签；两个入口互斥，旧URL兼容，机构/模型显示内容类型。
- 摘要：公开免费Crossref→OpenAlex DOI batch→白名单publisher摘要；exact DOI校验、20 HTTP单轮预算、成功归档累计当日预算、10候选优先级、1/3/7天退避。坏账本零请求软失败。分类/验证失败不提交恢复状态。
- 元数据恢复发现AEM期刊封面条目与正文重复，扩展已有封面排除模式到Advanced Energy Materials，避免当两篇研究文章。

## 验证边界

- 标题规则专项9项，真实公开14项词义误伤全部恢复研究身份；独立metadata集成5项（含跨collect预算/重新筛选/身份保持/故障保留/坏账本）。元数据模块19项，包括DOI错配、反爬、redirect预算和退避。
- 完整Python257项通过（独立完整256项后主Agent补1条实际AEM封面回归通过）；前端原254断言及新队列15项通过，真实公开快照及修复后2268条快照1440/390原生Chrome各18项通过。不是人工分类质量验收。
- 真正私有参考语料只在内存，重放同一公开2282输入：无topic1621→1255（新增366篇有据主题）；72篇原相关期刊论文无topic10→0；研究待分77→62。ID/first_seen保持。之后用同一封面识别规则排除14条AEM期刊封面/期次重复，实际input2268、无topic1251、pending1564、研究待分仍62，不能把删除计作新增分类。
- 免费实测：10候选、11请求，恢复6摘要（Crossref4、OpenAlex2；其中1条是之后识别排除的封面），4篇暂无摘要并退避。LLM0、Bohrium0。独立2候选/3请求试验另有1篇恢复，非此批结果相加。
- 回放与补全收据在工作区outputs/classification-repair-20261026/；独立检查收据classification-v25-independent-checks.json、metadata-integration-independent-checks.json、UI收据classification-ui-browser-20261026/。

## 正式发布

待GitHub Actions与Pages实际验证后补充。不得将local routed snapshot或retention成功称为新版正式采集。


## 独立标题抽样后的收紧

首轮v2.5的UI/运行验收完成后，独立语义抽查26项发现3个明确错误标题标签：next-generation被当生成模型、MLCCs材料优化被当AI训练优化、chemical robustness被当评测稳健性。不能把运行回归通过等同语义准确。v2.5.1增加按AI/评测/科研软件维度的标题语境，并对生成模型、稳健性主题加专用证据限制；传统interatomic potential也不能单独代表AI。13项标题专项、完整Python261项通过，重新版本化使v2.5标签全部复算。
