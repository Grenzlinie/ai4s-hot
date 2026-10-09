# 实施与验收证据

## 实施范围

访客文案为独立AI4S Hot网站；导航、研究主题、内容类型、多来源按钮与综合排序接入公开归档，不修改分类算法或本机存储键。

## 离线验证

- `node --check site/static/app.js`通过。
- `node site/tests/test_frontend.cjs`：29断言通过。
- `node site/tests/test_topic_explorer.cjs`：67断言通过。
- `node site/tests/test_discovery_feed.cjs`：132断言通过；独立子Agent编写与验收，主Agent重复运行复核。覆盖110条公开数据及合成边界，不代表分类或推荐质量测量。
- `../site-venv/bin/python -m unittest discover -s site/tests -q`：160测试通过。
- `openspec validate --all --strict`：7项通过。
- `git diff --check`通过。

## 发布前回滚点

2026-10-09在线manifest读取：frontend `a46136428a041984850368328de406436ceed2bc`，archive `17231ace5bdbcb517f9e0008b84ddee23934c58d`，archive hash `ac78e4a8b7692a54b14a8c348a37ce3dc7d68a37635e45ab3dcc2292c9c6f460`。可用既有pages-restore workflow指定这两个不可变SHA并publish恢复；无须重新采集。

## 正式前端本地浏览器

独立子Agent使用真实Chrome154：54/54项通过，page_errors=[]；主Agent复核JSON和1440/390固定视口截图。覆盖来源OR/计数/零态、领域/类型/四维主题、推荐/最新候选守恒、旧URL/history、原本机存储、纠错导出导入、退役alias、故障与过期提示、键盘焦点。收据与截图：`site/discovery/evidence/final-production-local-*`；原验收脚本`production.cjs`保留运行时绝对依赖路径，输入为本地从site-data导出的公开快照，非私有数据。

## 原生部署与线上读回

- 代码9916a9cb339b34a6dc1f73678e3718dd594636c6已发布，CI37908625833成功；Pages37908625753和重试37908850893均发布成功，原生run收据见`site/discovery/evidence/{ci,pages-run}.json`。
- 两次更新在taxonomy阶段失败，正常触发retention；本地只读诊断主题API返回HTTP503，外部故障尚未恢复。没有将workflow成功当成采集成功；不修改采集配置、凭据或归档来掩盖失败。
- manifest.mode=retention，沿用archive17231ace5bdbcb517f9e0008b84ddee23934c58d，110条，hash ac78e4a8b7692a54b14a8c348a37ce3dc7d68a37635e45ab3dcc2292c9c6f460。全部5项静态资源与本地及manifest hash一致，见online-http.json。
- 独立真实Chrome线上49/49通过，0 JS errors；动态锁定实际index/manifest，首末快照一致。覆盖来源、领域/类型、日期、排序、旧链接、history、收藏/已读/纠错导入导出、手机与焦点。线上真实error提示可见，未称healthy；synthetic退役/四维/归档不可用边界保留local54证据，不在公网伪造。
- 主Agent复核online-http与live JSON及1440/390固定视口截图，全部证据位于site/discovery/evidence。

## 完成边界

本次UI替换完成；外部主题服务503是仍存在的独立服务异常，后续既有定时任务仍会尝试更新。分类准确率及推荐收益仍未量化，measure-topic-classification-quality五项任务保持未完成。
