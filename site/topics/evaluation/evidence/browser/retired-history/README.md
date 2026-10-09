# Retired history and local browser rollback

真实 Chrome 154.0.8037.99 下，普通开发归档矩阵 29 项通过，退休节点、topic_history、更新失败 sidecar 和同一 profile 数据 v2→v1→v2 fixture 20 项通过。`retired-and-data-rollback.json` 是完整的此次本机浏览器收据。

数据版本、退役节点及失败状态通过仅本浏览器 context 的 request route 提供测试 fixture；这里证明真实浏览器行为，不能冒充原生生产归档或远端回滚。历史 v1 缺少 stable-ID alias 时明确告知清除不可用筛选；收藏、已读、本机修正字节保留，新版恢复后有效修正重新生效。
