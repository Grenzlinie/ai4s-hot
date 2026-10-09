# 验收计划（目标，尚未执行）

## 数据与分母

1. 将 audit.md 指定 commit 的88条公开记录作为pilot，保存输入hash和canonical identity，不把现有自动标签当gold。
2. 发布验收集至少148条真实公开内容：现有88条pilot全部固定进入开发/回归资料；另收集至少60条未用于本次审查、类别定义或规则设计的真实公开条目作为留出候选，补齐科研软件、材料对象、组织动态、空摘要、模型发布与冷启动案例。用人工确认每条的研究范围、内容性质、领域、可接受细类或仅父类、证据不足状态和公开理由。未确认记录不进入gold。
3. 先按canonical DOI/arXiv/规范URL去重，同一论文的版本和转载归一组；已审查的88条以及所有用于audit/定义/强制回归的同源组强制进入开发集，不得通过随机seed分入留出。新增未见池用固定seed=20261009按类型/维度分层抽取至少60条留出；开发集≥88条。两个split分别覆盖四研究维度，留出集每维度至少10条阳性、至少20条非研究/组织动态；一条可计入多个维度支持数，但总体分母只计一次。
4. 留出标识从私有参考示例、精确匹配和人工overrides中排除，标题别名也做检查；自动主指标关闭留出覆盖和exact-seen捷径。exact-seen单独验证身份/继承机制，不加入unseen分类得分。
5. 类别定义/阈值/权重只在开发集调整。保持留出集封存；若读过错误并据此改规则，则该集变为开发资料，补建新的留出集，不能反复试到通过。
6. 金标准先由阅读公开材料的人员标注并独立复核，冲突由维护者定稿；可以使用AI提出候选，但未经人工确认的标签不算gold。文献不足时明确标为证据不足，不根据标题猜测。
7. 保存 `dataset-manifest.json`：来源commit、样本身份、去重规则、split seed、标签版本、支持数和输入hash。私有参考只记录内部排除是否成功，不导出私有条目清单。

## 标签计分约定

- 每个facet分别保存规范ID的明确标签集，可由人工给出少量、完整的可接受替代集合。替代集合在冻结时定稿，不由预测结果临时扩大。
- fine预测只取显式最具体标签，移除纯展示用ancestor closure；真值同样规范化。对允许的完整替代集逐一计算集合TP/FP/FN，选择F1最高者（并列按冻结ID顺序），两版分类器使用同一规则；重复标签只算一次。
- 真值明确到细类时，仅预测父类不算fine TP，缺失细类计FN；对应父类可在独立层级报告得到credit。根precision单独用ancestor closure，每条每根只计一次，不把祖先加进fine分母。
- 真值仅能判定父类（broad_only）时，fine_applicable=false，不冒充精确细类gold；预测未经证据支持的子类计“过度细分”，须通过独立门槛。非研究或明确证据不足要求拒判者fine_applicable=true且gold为空，预测研究细类计FP。
- scope、content_kind、domain_facets和状态各有独立混淆矩阵；scope=research但Zotero无对应领域标taxonomy_gap，不能伪装成non_research。覆盖率同时报告目录内、目录缺口、证据不足与域外分母。
- 标注者可以读取留出材料；调参实现者在冻结配置前只读取开发集及预先约定的支持统计，不读取留出逐条错误。首次验收失败后的改进必须更换留出集或明确报告其已成为回归资料。

## 发布门槛

以下是拟定目标，不是当前实测结果。冻结数据和门槛后才运行留出验收。

| 门槛 | 目标及分母 |
|---|---|
| 四维度根标签precision | ≥95%，在全部留出条目预测的根标签上计 |
| 细类micro precision / recall / F1 | ≥90% / ≥75% / ≥80%；仅在fine_applicable的unseen样本计分，含可判定细类、非研究和明确要求拒判样本；非研究/拒判误标计FP，研究拒判计FN；仅父类样本另验过度细分 |
| 支持类macro F1 | gold支持≥5的类单独宏平均，报告所有更少样本类；不得静默删掉少样本类 |
| 相对基线改进 | 同一固定split上micro F1至少提高5个百分点；若基线已≥95%则保持且修复全部强制反例；任一有足够支持的根维度F1不得降低超过5个百分点 |
| 非研究内容误入研究目录 | ≤5%，分母为人工判定的非研究/组织动态，不是全部文章 |
| 可判定研究条目覆盖 | ≥70%，分母为gold中有足够证据且目录能表达的研究条目；组织新闻与证据不足另报，不能用拒判隐藏漏分 |
| 内容性质 / 通用领域 | content_kind macro F1≥90%、domain_facets micro F1≥85%，各自报告支持数及N/A，不以研究目录指标代替 |
| 父类-only过度细分 | ≤5%，分母为人工只能判断父类的样本；该组不混入fine F1，单独报告精确父类匹配与支持数 |
| 结构/隐私/迁移 | 无孤儿引用、稳定ID重命名/移动保持、无私有资料出现在公开产物；强制回归全部通过 |
| 浏览 | 1440px与390px真实浏览器矩阵全部通过；minimal-DOM只能补充 |
| 运行 | 固定runner的500参考/200新公开条目冷启动分类≤10分钟，缓存模型权重后≤5分钟，峰值RSS≤5GiB；包含目录/参考读取，另报网络和推理耗时，不包含原arXiv排序及新闻摘要 |

同时报告每项支持数、空分母为N/A，以及precision/recall的置信区间（按item分组bootstrap，固定seed）。小样本下目标是试运行门槛，不宣称统计上保证达到同等总体精度。关键支持不足时只能发布明确受限的试用范围，不能标全目录验收通过。

## 强制回归矩阵

下列测试名称为待实施的计划，当前不声称存在或通过。

| ID | 场景 / 对应能力 | 完成证据 |
|---|---|---|
| T01 | rename/reparent稳定ID、旧alias（taxonomy-sync） | 合成树迁移前后ID/标签/收藏不变 |
| T02 | 删除、同名、孤儿、循环、未发布根（taxonomy-sync） | 无错误自动合并，最后有效目录保留 |
| T03 | MOF + ML potential跨维度（topic-assignment） | 两轴标签共存；校准后细类多标签不被全局top-3挤掉 |
| T04 | PYS残差诊断不是主动选样（topic-assignment） | 依定义拒绝无证据的BO标签 |
| T05 | 银行Claude部署/资助声明（topic-assignment） | 内容性质为组织/工程动态，不误标自主科研 |
| T06 | 空目录+明确类别名（topic-assignment） | 有definition-only候选及降置信度，无不可达主题 |
| T07 | crystal音乐节等OOV反例（topic-assignment） | 域外拒判，包含覆盖率/负证据，不能只凭重合词强标 |
| T08 | 中文/英文、同义词、短标题/空摘要（topic-assignment） | 证据不足与目录外分离，跨语言成对样本评估 |
| T09 | DOI/arXiv冲突、同标题不同论文（topic-assignment） | 不误继承exact标签 |
| T10 | 阈值/规范化/模型/定义/override变化（topic-assignment） | 缓存失效与diff可复现，输入顺序变化不改变结果 |
| T11 | API/模型不可用、半途迁移（topic-assignment） | degraded可见，上一版保留，原子发布 |
| T12 | 私有资料注入标记（private boundary） | archive/artifact/log/cache/摘要请求均不含标记 |
| T13 | 多标签父数量与筛选、同维OR/跨维AND（topic-explorer） | 当前/全量计数与结果集合一致，无重复 |
| T14 | 展开/选择、标签路径、主题搜索（topic-explorer） | 桌面真实浏览器录屏或截图+步骤收据 |
| T15 | 手机抽屉/Esc/焦点/无溢出（topic-explorer） | 390px真实浏览器操作收据 |
| T16 | URL、后退、旧ID、收藏/已读迁移（topic-explorer） | 刷新/分享/回滚均恢复正确范围 |
| T17 | 本机纠错导出导入和未知ID（topic-curation） | 本机与全站范围明确，无前端token |
| T18 | 人工覆盖优先、删除节点待复核（topic-curation） | 重跑不覆写人工选择，保留历史 |
| T19 | 去重split、参考/override排除（classification-evaluation） | 泄漏检查0违规，seed/hash可重建 |
| T20 | 质量、runtime、Pages、回滚（classification-evaluation） | 冻结报告+真实Actions链接+HTTP读回，恢复上一版 |

## 发布收据

`evaluation/report.md/json`：代码SHA、模型revision、包/runner版本、目录/定义/阈值/override版本、dataset manifest、支持数与各项指标、失败/拒判分布、耗时与RSS、影子diff、前端浏览器矩阵、Actions URL、发布/回滚archive版本。发布包只包含公开数据和汇总，不包含库内参考资料。
