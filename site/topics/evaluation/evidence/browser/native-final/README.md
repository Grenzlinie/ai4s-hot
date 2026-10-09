# Final native browser acceptance

全部阶段使用真实线上 `https://grenzlinie.github.io/ai4s-hot/`、已安装 Chrome 154.0.8037.99 及同一个独立持久化测试 profile。没有 request route、测试归档替换或浏览器 agent 调用 workflow。截图已人工查看。前端为 `a46136428a041984850368328de406436ceed2bc`。

| 阶段 | 原生操作 run | 浏览器检查 |
|---|---|---|
| 最终新版浏览 | 37894330336 | 15 项，含定义版本/同步时间、旧 URL alias、1440/390 |
| 目录同步故障 | 37894554091 | 8 项，真实 error sidecar/banners、原归档 bytes 与本机状态不变 |
| 分类故障 | 37894654207 | 9 项，含指定公开卡片失败说明 |
| 历史 v1 回滚 | 37894759805 | 12 项，b83dd archive/前端 a461/hash 对齐，本机状态保留 |
| 最新 v2 恢复 | 37895016891 | 18 项，afa651 archive/hash 对齐，旧 URL/纠错恢复，桌面手机 |
| 最终正常更新 | 37895143455 | 14 项，sidecar ok、错误提示清除、状态保留、桌面手机 |

每一阶段的完整结果在对应 `.json`，运行脚本和截图同目录。`live-rollback-baseline.json` 在实际 schema2 回滚前准备，包含公开 item/topic ID、本机收藏/已读/公开纠错文本，不含凭据。

历史 v1 不含 stable topic alias，因此回滚时无法保留新版 stable-ID 主题筛选：明确告知清除不可用条件，其他查询和阅读记录保留。本机纠错在 v1 标为待复核，恢复 v2 后重新有效。这个兼容限制没有被记成筛选保留通过。

最终生产归档为 `17231ace5bdbcb517f9e0008b84ddee23934c58d`，schema2，110 条，SHA256 `ac78e4a8b7692a54b14a8c348a37ce3dc7d68a37635e45ab3dcc2292c9c6f460`。准确率仍未量化；浏览器与运行检查不等于分类质量测量。
