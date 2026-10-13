## Context
现有 collect.py 在分类和公开归档校验之后生成摘要。独立原型已实测公开HTML和LKM，详见工作区 outputs/bohr-extraction-trial/report.md。

## Goals / Non-Goals
Goals: 将有界公开证据传给摘要，按北京时间持久预算，无服务依赖硬失败。
Non-Goals: 不上传PDF、不调用付费PDF解析、不声称全文完整、不批量重写已有摘要、不改主题算法或前端导航。

## Decisions
- 新 enrichment 模块仅接收公开条目；临时text与公开basis分开，summarize只序列化白名单字段。
- 使用公开来源域名白名单，逐次验证重定向并限制响应大小、超时、条目数；暂不扩展全网抓取。
- DOI图谱精确查询是唯一自动付费回退；标题关键词检索匹配不稳定，不纳入本轮自动链路。
- 在site-data根目录 .bohr-budget.json保存日期和计数；调用前预留当日剩余额度，Actions先提交并push预算文件成功再给采集器本次额度；未使用的预留额度不退回。预算提交失败则终止调用与发布。现有单一workflow concurrency串行保护该账本。
- CUSTOM_CONFIG中enrichment是站点专用配置，prepare_config移除它避免上游Hydra拒绝未知字段。BOHR_ACCESS_KEY仅环境注入；不复制登录缓存。
- 用户2026-10-13授权每天最多20次，允许本机AccessKey同步为Actions Secret；本地YAML已配置该上限。每轮补充最多8条，20为日上限并非调用目标。

## Risks / Trade-offs
- 长文前段可能不足 → 将输入标为有界提取，不能宣称模型阅读完整全文。
- 网站重定向/挑战 → 降级摘录并记录类型，不绕过访问限制。
- runner强制终止 → 账本先push再调用，未用完的预留次数作废，保证重跑不重新获得次数；代价是当天可能少调用。
- 图谱是模型提取而非原文 → basis独立标记并保留kind。

## Migration Plan
先离线独立测试，再公开资源真实探针及CI验证；启用公开提取及已授权Bohrium回退；CLI认证失败则给采集器0额度，公开提取继续。部署后读取运行结果与公开归档。回滚将enrichment.enabled=false并保留预算账本，不能通过回滚重置额度。

验收分母是规则/集成检查和实际探针数量，不将它等同于摘要事实准确率。
