# Actual production rollback / restore browser evidence

Chrome persistent profile 与首次真实线上 v2 浏览验收相同。浏览器 agent 未调用任何 workflow。

- 实际归档回滚为 `b83dd083...` 时，收藏、已读及页面可浏览等 9 个前置断言通过，最后关于 stable-ID 筛选被清除时的说明断言失败。首次脚本因此未写出完整 native receipt；`rollback-partial-attempt.json` 明确标为工具断言记录的重建，不宣称回滚浏览器矩阵完整通过。
- 本机纠错是在页面已经回滚为 v1 后创建；不能据此证明纠错曾经历 v2→v1。其旧 `zt-` ID 在真实恢复为 v2 后正确映射，10 项恢复检查完整通过，原始输出见 `live-restored.json`。
- 收藏/已读从初次线上 v2 验收一直保留，本机修正从 v1 到 v2 恢复后字节保持不变，URL 的旧主题 ID 与关键词也恢复。
- 历史 v1 归档缺少稳定 ID alias，回滚期间新版主题筛选存在兼容限制；没有将这项丢失记作通过。
