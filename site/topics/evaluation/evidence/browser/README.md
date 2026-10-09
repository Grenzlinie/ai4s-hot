# Real browser acceptance receipt

2026-10-09 在本机已安装的 Google Chrome 154.0.8037.99 中运行 headless 浏览器，通过 Playwright Core 1.64.0 控制。访问 `http://127.0.0.1:8765/` 的 106 条公开开发归档，静态资源与仓库文件逐字一致，输入哈希见 `input-manifest.json`。

- `results.json`：1440×1000 与 390×844 的 25 项真实浏览器检查。
- `combinations.json`：真实浏览器中的同轴 OR / 跨轴 AND、当前/全部计数、逐项清除、拒绝含私有字段的导入，共 4 项。
- `desktop.png`、`mobile.png`、`mobile-drawer.png`：截图已人工查看。
- 两个 `.cjs` 文件：此次执行的验收脚本；依赖 `playwright-core@1.64.0`，使用本机 Chrome executable，不下载浏览器。运行时需可访问该本机 HTTP 预览，截图输出在 `/tmp/ai4s-browser-acceptance/`。

这份证据只证明该输入下的浏览器行为。分类质量、GitHub Actions、线上部署读回与回滚必须分别验收。CUA 的 Chrome 原生连接挂起并被中断；最终结果来自成功执行的真实 headless Chrome，未使用最小 DOM 断言代替浏览器。

## Local rollback rehearsal

`rollback.json` 记录同一 origin 下从当前静态资源切换到 `f085ba6`、再恢复当前版本的 9 项检查。使用浏览器请求路由替换本机静态资源；公开归档不变，没有修改线上生产。收藏、已读和本机纠错存储保留，恢复新版后 URL 筛选和本机纠错再次生效。旧版不会解析新版 `q/topics` URL 参数，因此回滚期间需要手动选择筛选；这项限制明确记为 limitation，并未计为通过。相关截图是 `rollback-old.png` 和 `rollback-restored.png`。
