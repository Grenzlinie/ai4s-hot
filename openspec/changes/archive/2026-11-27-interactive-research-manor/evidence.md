# 交互科研庄园验收

## 场景与阅读

- Blender 导出 1.30 MB GLB、48 个网格和 Wave、Walk 动作。地标与角色在独立节点，动作由网页按需播放。
- 真实 Chrome WebGL2 验证桌面拖动、复位、场景地标进入论文和图谱、角色行走。窄屏上搜索可用，竖划场景可滚动页面。实测触摸图书馆屋顶模型打开论文列表。
- 验证无法启用 WebGL 时，庄园插画和图书馆的文字入口仍可用。

## 分类与来源

- 用更新前 4,512 条公开归档构建，空主题和无效主题 ID 均为 0。图谱收录的 1,755 篇论文沿用有据领域，期刊相关性字段保留。
- 原主题待分类入口覆盖 168 条，其中 53 条获研究宽领域、87 条归通用 AI 与应用动态、28 条归综合研究。
- Nature Machine Intelligence 和 Nature Computational Science 的官方 RSS 与 Crossref 元数据均可读。目录提供 25 个官方入口，其中 12 本期刊。移动浏览器验证期刊检索、分组和站内收录链接。
- 新增宽类属于覆盖改进。细主题人工准确率评估由 `measure-topic-classification-quality` 继续跟踪。

## 发布

- 应用提交 `3b98e9419a34e05f38eddf62381f434af96ae23c`。
- [站点检查](https://github.com/Grenzlinie/ai4s-hot/actions/runs/45968023926) 成功。
- [GitHub Pages 发布](https://github.com/Grenzlinie/ai4s-hot/actions/runs/45968023719) 成功。线上 manifest 是该应用提交。公开归档 4,541 条，缺少当前主题的条目为 0，来源目录和 GLB 可读。
- 首次 Nature Machine Intelligence 采集成功。Nature Computational Science 的 RSS 返回 8 条候选，Crossref 请求或解析失败，来源标为部分完成。两刊各有 1 条进入相关论文。用同一增量窗口单独补测 Crossref 返回 25 条，线上游标将在正常日更时继续。
