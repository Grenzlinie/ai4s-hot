# 项目执行路线

2026-10-09用户最新选择“直接采用新版”：保持准确性、目录结构与浏览体验三个目标，本次直接发布默认v2，不新增opt-in/selector。真实质量状态为`unmeasured`；人工gold、dev校准、holdout准确率与基线改进独立延期，不作为本次上线硬依赖，不勾完成。技术安全、真实浏览器、所启用后端runtime、原生Pages与回滚/HTTP仍须有证据。

| 里程碑 | 当前产物及状态 | 结束条件/剩余 |
|---|---|---|
| M0 公开输入 | 指定commit实际106条全部dev，122条独立候选；工具已建，gold=0 | 输入hash已冻结；人工复核和质量支持数转Deferred measurement |
| M1 目录基础 | 稳定HMAC身份、alias/retired、53节点定义、发布范围与schema验证已实现 | 独立迁移/隐私逻辑证据已记录，不等同分类精度 |
| M2 分类与浏览 | 分维候选、定义冷启动、公开理由、纠错、计数、URL和手机抽屉；148 Python+66前端断言；真实Chrome 29项矩阵 | error状态逐条失败收据等仍按tasks保留未勾，语义原生验收单列 |
| M3 默认新版发布 | `72cd88d6`已上线，最终原生Pages/CI/semantic shadow成功，实际回滚及恢复完成 | 原生收据及HTTP已读回；历史归档筛选兼容限制和故障注入边界详见evidence |
| 后续独立量化 | tasks 8.1–8.5（原1.2/1.3/1.4/3.5/6.2）明确Deferred measurement | 人工确认、无泄漏支持、同输入基线、dev校准及冻结holdout评分；不以覆盖率代替准确率 |

实施入口为`changes/improve-zotero-topic-classification/tasks.md`的当前未完成技术项，不再从已完成1.1重做。完成项由`evidence.md`索引到实际测试/浏览器/原生运行收据；只有本次默认v2行为验收完成、延期量化有明确承接后才合并已验收delta，当前change保持active。

## 当前原生运行快照

- 旧提交`fe70`的词语影子运行[37891067362](https://github.com/Grenzlinie/ai4s-hot/actions/runs/37891067362)成功；它属于该历史提交，不能替代最终`72cd88d6`验收。
- 最终[Pages 37892904488](https://github.com/Grenzlinie/ai4s-hot/actions/runs/37892904488)、[CI 37892904490](https://github.com/Grenzlinie/ai4s-hot/actions/runs/37892904490)、[semantic shadow 37892914767](https://github.com/Grenzlinie/ai4s-hot/actions/runs/37892914767)均成功，最终HTTP及恢复收据见evidence.md。

## 独立运行项

- **O1：arXiv/Zotero排序运行已取得成功收据。** [37883000672](https://github.com/Grenzlinie/ai4s-hot/actions/runs/37883000672)成功，随后[Pages更新37888361387](https://github.com/Grenzlinie/ai4s-hot/actions/runs/37888361387)也成功。上游排序/网站导入与本次主题准确率分别记录，不能将它们作为分类质量指标。
- 数据采集来源失效、中文摘要失败、长期归档和来源覆盖后续按独立change管理；当前未宣称这些方面已有完整OpenSpec。

不得为了完成路线图发送邮件、修改Zotero库、将私有分类资料发给外部模型，或重复运行付费摘要作为主题回归测试。
