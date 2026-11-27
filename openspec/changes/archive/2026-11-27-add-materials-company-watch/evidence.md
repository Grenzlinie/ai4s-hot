# 材料 AI 公司采集验收

## 官方采集

- 七个官方来源均实际读取。Periodic Labs 与 Radical AI 使用官网新闻页。CuspAI、Entalpic、深度原理与 Matlantis 使用官方 RSS。
- 开物纪使用[研究与进展](https://www.kairosmaterials.com/news/#research)的研究卡片，读取 Creator、Prophet 和 ELEMENTA 的发布日期和简介，链接官方 PDF。
- 实测代表性技术条目包括 Periodic Neon/XRD、Radical AI 的电子材料验证和样品制备、CuspAI 的 OpenDAC、Entalpic 的原子层沉积、深度原理 ReactNexus，以及 Matlantis PFP。保留官方标题语言与发布日期。

## 回归与浏览

- 独立运行 Python 测试 282 项以及 Node 阅读、来源筛选逻辑。收紧公司新闻栏目与融资筛选后复验相关专项测试。
- Chrome 320 px 触屏视口通过材料 AI 公司分组、关键词搜索、站内链接、来源状态和页面宽度检查。目录七个公司链接与采集注册表一一对应。

## 发布

- 应用提交 `d0ebf5f4cdc257cd2590dbed5308285f45e3306d`。
- [站点 CI](https://github.com/Grenzlinie/ai4s-hot/actions/runs/45971585440) 与 [Pages 发布](https://github.com/Grenzlinie/ai4s-hot/actions/runs/45971585711) 通过。
- 线上 manifest 匹配应用提交。公司目录和合辑链接可访问，七个来源状态均为 `ok`。首轮公开收录 19 条，开物纪 3 条均有材料领域与有效主题标签。
