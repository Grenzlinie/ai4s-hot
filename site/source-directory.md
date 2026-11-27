# 官方来源目录

`site/static/sources.html` 是访客入口。HTML 保留源站、RSS 和站内筛选链接。页面脚本负责搜索、分组和读取轻量的 `data/source-health.json`。测试检查静态目录与采集注册表同步。

当前目录覆盖 25 个入口：4 个论文发现平台、12 本期刊、9 个官方发布源。alphaXiv 的访客链接使用其网站，不能把采集 API/MCP 地址当阅读入口。arXiv 另外给出材料科学、机器学习和计算物理的官方 new 列表。

## 本轮接入

2026-11-27 实际只读核对：

| 期刊 | 官方资料 | 配置与实时免费请求 |
|---|---|---|
| Nature Machine Intelligence | [Journal Information](https://www.nature.com/natmachintell/journal-information)，在线 ISSN 2522-5839 | [官网](https://www.nature.com/natmachintell/)、[官方 RSS](https://www.nature.com/natmachintell.rss) HTTP 200、8 条；[Crossref](https://api.crossref.org/journals/2522-5839/works?rows=1) HTTP 200，期刊标题与 ISSN 一致 |
| Nature Computational Science | [官网](https://www.nature.com/natcomputsci/)直接提供 RSS；[期刊资料](https://www.nature.com/natcomputsci/journal-information)，在线 ISSN 2662-8457 | [官方 RSS](https://www.nature.com/natcomputsci.rss) HTTP 200、8 条；[Crossref](https://api.crossref.org/journals/2662-8457/works?rows=1) HTTP 200，期刊标题与 ISSN 一致 |

Nature Communications 已有配置，保留原 `nature-communications` ID、2041-1723 和 [官方 RSS](https://www.nature.com/ncomms.rss)，本轮不重复注册。

新增两刊直接使用原有 RSS + Crossref 增量适配器，沿用当前材料 AI 相关性判定、主题分类与归档机制，不自动把全刊所有研究都视为材料 AI 论文。目录中的“官网”展示完整源站，“站内收录”仅展示站内选入内容。

## 官方入口依据

- 论文发现：[arXiv 官方首页](https://arxiv.org/)、[材料 new](https://arxiv.org/list/cond-mat.mtrl-sci/new)、[alphaXiv](https://www.alphaxiv.org/)、[Hugging Face Papers](https://huggingface.co/papers)、[Semantic Scholar](https://www.semanticscholar.org/)。
- Nature：[Nature](https://www.nature.com/nature/)、[Nature Materials](https://www.nature.com/nmat/)、[Nature Communications](https://www.nature.com/ncomms/)，另加上表两刊。
- AAAS：[Science](https://www.science.org/journal/science)、[Science Advances](https://www.science.org/journal/sciadv)。
- Wiley：[Advanced Materials](https://advanced.onlinelibrary.wiley.com/journal/15214095)、[Advanced Energy Materials](https://advanced.onlinelibrary.wiley.com/journal/16146840)、[Advanced Functional Materials](https://advanced.onlinelibrary.wiley.com/journal/16163028)；官网 ISSN 与现配置相符。
- Elsevier/Cell Press：[Acta Materialia](https://www.sciencedirect.com/journal/acta-materialia)、[Matter](https://www.cell.com/matter/home)。

“官方入口”指出版商/项目自己的链接，不等于承诺网页抓取工具始终能访问。此次 Nature 部分页面触发 cookie 跳转，AAAS/Elsevier 页面被自动化访问返回 403；没有关闭 TLS 或绕过访问控制。RSS 与采集状态和官网链接在目录中分开呈现。未调用付费服务、模型或私密凭据。
