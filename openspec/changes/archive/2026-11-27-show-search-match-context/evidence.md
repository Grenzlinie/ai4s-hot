# 搜索匹配片段验收

## 用户案例

使用 2026-11-27 17:11 北京时间的公开归档，共 4,576 条。原算法对近 30 天的 “Bo Hu” 返回 399 条，例如把 Whole-Body 和 Humanoid 内的字符视为短词。复算后，单词边界匹配的 3 条均由不同作者共同满足。

Chrome 验收中，原链接在近 30 天与全部日期均为 0 条，两处空态显示查询。真实正例 “Bo Yang” 返回 4 条，“Yuyang Hu” 返回 3 条，命中作者名在卡片可见。

## 浏览与回归

- Chrome 验证 FIG-MAC 标题词组、实际 DOI 链接、来源结合标题和作者、最新排序与完整摘要展开。
- 在 320px 触屏视口看到原始摘要第 898 字符附近的上下文与命中高亮，页面可正常换行。
- 6 个 Node 前端测试文件共 288 条断言通过，包括短词、不同作者、远处摘要、HTML 转义和编号。

## 发布

- 应用提交 `dad452f8c67b1add5dab9b4ddca6a7bb00273ea2`。
- [站点 CI](https://github.com/Grenzlinie/ai4s-hot/actions/runs/45979027381) 和 [Pages 发布](https://github.com/Grenzlinie/ai4s-hot/actions/runs/45979027348) 成功。
- Pages manifest 匹配本次应用提交。Chrome 线上打开用户链接显示“没有找到「Bo Hu」”，结果为 0 条。390px 触屏视口搜索 Bo Yang 返回 4 条，作者全名加粗高亮，无横向溢出。
