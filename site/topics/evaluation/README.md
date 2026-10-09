# 公开分类评估资料

此目录只含公开内容；不得放入 Zotero 私有参考、密钥或参考向量。目录下候选标签目前全部未人工确认，不能作为 gold 或声称分类精度已达标。

## 冻结输入

`baseline-input.json` 是 `d49956853ecf5e74232d330dc4f889dab01b7dba:data/index.json` 的逐字节快照。实际为 **106** 条，方案审查记录写的 88 条与该 commit 不一致；保留全部 106 条作 dev，避免将任何已审查资料放进 holdout。真实公开候选经过 DOI/arXiv/URL/标题分组后为 122 条 holdout，当前总计 228 条，人工确认数量为 0。支持是否满足四维度每维至少 10 阳性、非研究至少 20，必须等待人工确认，不能按采集 query 推定。

`dataset-manifest.json` 记录源 commit、原始输入 hash、API 响应 hash、seed、去重规则、样本身份和输入 hash。`annotation-dataset.json` 保存公开元数据与空 gold。全部 audit/开发组强制 dev；DOI/arXiv 跨版本和转载的 alias 先合并，再确定 split。

## 人工标注

```bash
python scripts/review_annotation.py --html /path/to/AI4S-Hot-annotation-review.html
python scripts/review_annotation.py --import-labels /path/to/ai4s-human-labels.json --output /path/to/human-reviewed-dataset.json
```

HTML 完全离线运行，只在用户点击原文链接时打开公开网站；草稿保存在本机 localStorage，可导出继续评审。每条需填写评审者、公开证据并勾选人工确认。AI 可以提出候选，但不能代替该确认。仅父类明确时 `status=broad_only`、`fine_applicable=false`。非研究与必须拒判条目使用 `fine_applicable=true`、空主题集合，误分计 FP。可接受替代集合是完整集合，须在冻结前确认。审核者可阅读留出材料，分类调参者冻结前仅可读取 dev 和汇总支持数。独立复核与维护者定稿仍是额外门禁，HTML 本身不证明已独立复核。

导入不会覆盖原候选数据；未知 ID、额外字段、非法主题、未确认 gold、冗余父子 gold 均拒绝。当前 UI 以冻结 v1 公开主题 ID 标注；v2 评分前需通过稳定 registry 的 aliases 统一迁移 dataset、baseline 与预测 ID，并记录迁移 hash。

## 评分与门禁

```bash
python scripts/run_evaluation.py --dataset /path/to/frozen-reviewed-dataset.json --predictions /path/to/v2-predictions.json --baseline-predictions /path/to/v1-predictions.json --evidence /path/to/independent-receipts.json --output /path/to/report.json
```

预测字段为 `id, topic_leaf_ids, scope, status, content_kind, domain_facets`。同一冻结数据的 v1 与 v2 预测分别输入；现有 archive 标签仅是旧的自动预测，不是 gold，也不能代替未见样本的 v1 运行。未标注、缺预测、未知主题等直接失败。程序只输出汇总指标及 gate，不输出留出逐条错误。退出码 2 表示质量 gate 未全部通过。

门禁包括各项 OpenSpec 阈值和支持数、相对基线改进、根维度不下降、分组隔离。私有参考排除与独立人工复核需要独立执行者收据（与完整 dataset 的 SHA256 一致，含 reviewer 与 pass）。即使指标全好，缺收据也保持 false。`leakage_check()` 接受进程内 private references 和 override IDs，只返回违规数量；不得保存其输入。排除需在预测前完成，不能只在事后签字。首次 holdout 错误如果用于调参，该集转为回归资料并收集新 holdout。

质量 gate 通过只证明此次冻结集的指标。真实浏览器、500/200 冷暖运行、RSS、Actions、Pages 与回滚属于其他收据，不能由本报告替代。

## 当前状态

- 冻结公开输入和候选采集已完成。
- 金标准、独立复核、真实 v1/v2 未见集评分、dev 阈值校准均待完成。
- 本模块的合成单元测试验证分母/替代集合/拒判/泄漏处理，不算真实分类质量结果。

## 安全生成预测与运行收据

```bash
python scripts/predict_evaluation.py --dataset site/topics/evaluation/annotation-dataset.json --split dev --backend v2 --output /path/dev-predictions.json --receipt /path/dev-prediction-receipt.json --aligned-dataset /path/stable-id-dataset.json
python scripts/benchmark_topics.py --dataset site/topics/evaluation/annotation-dataset.json --backend lexical --output /path/runtime-receipt.json
```

`predict_evaluation.py` 在任何分类前，依据完整 holdout canonical/title aliases 在内存中过滤私有参考；移除 holdout 和非当前 split 的 overrides；清除旧预测缓存；gold 不传给分类器。输出仅公开预测和聚合数量收据。`--backend v1` 可生成真实相同输入的 v1 预测；未人工确认时不可用来宣称质量验收。v2 `--aligned-dataset` 通过稳定 registry aliases 映射 gold ID；跨版本预测也须先统一 ID。`adapt_prediction()` 将网站 `web:paper` 等名字空间与 `topic_scope/topic_status` 转换为冻结评分字段，不改变网页 schema。

benchmark 将 200 条公开输入的同源参考也排除、去重后取 500 条实际参考；不足则记录 `insufficient_references`，绝不复制补足。cold/warm 在独立子进程中强制重算，含每次 Zotero 读取，RSS 统一为 bytes；两个阶段各有超时并保存失败收据。语义后端用 `--backend semantic|fusion --model-cache /fresh/model-cache`，仅公开模型权重可缓存，目录非空时不能声称已测真正冷模型下载。任何降级、计数不足、耗时/RSS 越线都保持 runtime_pass=false。性能报告不含逐条预测、私有文本/ID，且 quality_pass 恒为 false，必须另做人工金标准评分。

### Gold 与外部收据约束

`fine_applicable=false` 只允许 `scope=research,status=broad_only`，且每个可接受集合必须包含明确父类；非研究、证据不足和目录缺口不能借此退出细类 FP/FN 分母。`insufficient_evidence`、`taxonomy_gap` 的研究标签必须为空。`reviewed_at` 必须是带时区的 ISO timestamp；领域白名单与 catalog 一致，仅 `web:materials/web:chemistry/web:life_sciences/web:general_ai`，不允许任意 `web:*` 或重复项。

`private_exclusion_verified` 收据必须同时绑定 `dataset_sha256` **和** `predictions_sha256`，并含 `reviewer,pass=true`。预测 hash 取 `digest([adapt_prediction(p) for p in predictions])`，即规范字段和内容性质名字空间转换后的完整预测数组；`predict_evaluation.py` 的聚合收据已包含该 hash。`independent_review_verified` 绑定冻结 dataset，因人工 gold 复核不依赖具体预测。缺失、另一组预测或 hash 不符都会 failclosed。采用稳定 ID 对齐后的 dataset/预测时，独立收据也须重新绑定对齐后版本。

### v1 与 v2 的共同输入边界

评估入口的两个 backend 均通过 v2 reader 取得稳定公开目录及包含 DOI/arXiv/URL 的完整私有参考，再按相同 holdout 身份/标题 aliases 在内存中排除同源参考。随后分别直接调用 `topics_v1.classify` 与 `classify_v2`。因此 v1 baseline 表示“旧分类算法在共同稳定 ID、共同可发布目录范围及排除后的参考资料上重跑”，而非未经范围校正的生产旧归档，也不改变生产 v1 读取逻辑。这样即使私有参考与留出条目标题不同、但 DOI/arXiv 相同，也会在任一算法执行前排除。收据注明 `taxonomy_reader=v2_shared_identity` 与比较范围；不导出私有标识或文本。
