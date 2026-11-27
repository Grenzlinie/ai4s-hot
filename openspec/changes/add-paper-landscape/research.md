# 论文研究版图：分类、聚类与更新日志调研

调研日期：2026-11-27。按 research 技能实际浏览官方文档及项目主页；仅写调研，不修改实现、不调用模型或付费 API。以下“建议”是针对 AI4S Hot 的设计判断，不是被调研工具已经提供的项目功能。

## 可复用模式

| 一手来源 | 实际核对的设计 | AI4S Hot 可借鉴之处 |
|---|---|---|
| [OpenAlex Topics](https://help.openalex.org/data/topics/) | 四层结构：4 domains、26 fields、252 subfields、4,516 topics；标签体系与每篇论文的模型推断归属分开，论文最多分配三个 topic | 导航目录保持稳定、归属允许不确定；保存标准主题 ID，不把一次自动分组当永久学科目录 |
| [VOSviewer Online 文档](https://app.vosviewer.com/docs/user-interface/main-panel/) | 网络距离近似联系强度，坐标轴无固有语义；大小、颜色和连线强度由所选属性决定；放大显示更多标签 | 图例明确“颜色=研究簇、点=论文、邻近点的文本较相似”；避免把图中央解释为重要或推荐更高。默认等大节点，缺少引用数时不伪造影响力 |
| [Open Knowledge Maps FAQ](https://openknowledgemaps.org/faq) | 用标题、摘要等 metadata 的词共现矩阵聚类和降维；以簇内高频、簇间相对少见的短语命名；中心位置不代表重要性，避碰后的组内点位不宜精确解释 | 用短语解释小组，用点击小组→文章列表衔接地图与阅读；摘要缺失时诚实降低文本信息量，不要求全文才能使用 |

OpenAlex 最近确实发生主题改名与父级调整；官方说明 topic ID 保持稳定，2026-11-23/24 又发布一轮变更。因此外部映射应记录 `external_topic_id` 与映射版本，而不是依赖英文显示名恒定不变。[官方变更记录](https://help.openalex.org/data/topic-hierarchy-changes/)

上述不是只有概念图：VOSviewer Online 有[公开源码](https://github.com/neesjanvaneck/VOSviewer-Online)，Open Knowledge Maps 提供 [Headstart 可视化框架](https://github.com/OpenKnowledgeMaps/Headstart)。本轮推荐借鉴已解释清楚的交互和数据语义，不建议为了一个新入口迁移整站框架。未安装或运行这两个工具，未以 stars 代替成熟度判断。

## 稳定宽主题与动态聚类分开

建议第一版采用以下 **10 个可重叠的宽主题**，维护本地固定 ID、简短定义、正负例，作为首页入口和图中颜色；这是站点阅读导航，并非声称复现某个国际学科标准。

| 稳定 ID 示例 | 导航名称 | 范围提示 |
|---|---|---|
| materials | 材料与固态 | 合金、晶体、聚合物、结构—性能 |
| energy | 能源与电化学 | 电池、电解质、光伏、能源转化 |
| chemistry | 化学与催化 | 反应、催化剂、化学设计 |
| biology | 生物与分子设计 | 蛋白、药物、生物材料 |
| physics | 物理与科学计算 | 物理建模、模拟与数值计算 |
| experiments | 实验、表征与自动化 | 合成、仪器、测量、自主实验室 |
| learning | 机器学习与科学建模 | 表征、预测、学习方法、科学基础模型 |
| generation | 生成模型与逆向设计 | 有明确生成方法证据的设计与生成任务 |
| agents | 科研 Agent 与工具 | 科研智能体、软件、计算工作流 |
| evaluation | 数据集与评测 | 研究数据、基准、评测方法 |

每篇可有一个主宽主题及少量副主题；暂不确定者保留“未分类”，不为凑满目录强贴主题。期刊、来源、论文/报告类型、AI-for-materials 相关性仍是独立筛选维度。`next-generation` 不等于生成模型、`MLCCs` 不等于机器学习、材料化学耐受性不等于评测稳健性。

建议另设 `cluster_id`、`cluster_label`、`layout_version`、`cluster_method`：在选定时间窗的公开标题与可用摘要上产生相似文章小组，名称如“固态电解质的机器学习势”“自主催化实验”。宽主题提供稳定入口，cluster 提供当下内容局部结构；不要把每次聚类的编号变成永久导航 ID。使用公开文本 TF-IDF/相似度或本地 embedding 均可，首版不依赖 LLM。

图和列表共用同一组筛选状态、文章身份与收藏状态；选择图中小组直接过滤旁侧文章列表。显示“本图覆盖 N 篇、时间范围、标题/摘要覆盖情况”，让用户知道看到的是当前采集集合。已有数据若未建立可靠引用关系，名称应为“文本相似研究版图”，不能称引用网络；稀疏或缺证据文章可以显示为未归组，不强拉一条连线。这个边界来自现有数据条件，VOSviewer 和 Open Knowledge Maps 的官方图例也都强调布局含义必须由其输入关系决定。[VOSviewer 图解](https://app.vosviewer.com/docs/user-interface/main-panel/)、[Open Knowledge Maps 图解](https://openknowledgemaps.org/faq)

## 更新日志格式

采用 [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) 的人工整理、版本倒序、ISO 日期和 `Unreleased`；类别为 Added、Changed、Deprecated、Removed、Fixed、Security。只展示本次实际发生的类别。发布说明写用户能观察到的变化，不直接倾倒 Git commit 列表。

建议根目录 `CHANGELOG.md` 为单一来源，站内“更新日志”呈现同一内容。示例仅为待发布格式：

```markdown
# Changelog

## [Unreleased]

### Added
- 新增研究版图，可按宽主题浏览并查看相似文章。

### Changed
- 图与论文列表共用来源、期刊和日期筛选。

### Fixed
- 修正材料标题中的 next-generation 被当作生成模型的情况。
```

正式发布时替换为真实版本与实际日期，例如 `## [版本号] - YYYY-MM-DD`。每日采集成功/部分失败、论文新增数、最后更新时间保留在运行状态区；不要每天新增一个软件版本条目。分类算法或映射的实际行为变化应进入 Changed/Fixed，并注明对旧文章重分类的可见影响。不要把计划中的功能写进已发布版本。

## 本站采用的方案

按实际归档将材料与能源合并，在 AI 部分增设代码与计算系统、视觉多模态与机器人。每篇论文采用一个主领域，便于比较数量。研究簇根据公开文本单独生成。实际目录与图表口径见 [设计](design.md)。
