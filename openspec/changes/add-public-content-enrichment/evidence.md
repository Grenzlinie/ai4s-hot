# 验收记录

代码发布：76af0f9。用户2026-10-13授权Bohrium每天最多20次，允许复用本机AccessKey为Actions Secret。普通设置保留在本地YAML，密钥保存于0600环境文件和GitHub Secret。

- 独立Python：183/183，其中新增23项。
- 前端：29+67+132=228断言，后续仅后端/workflow调整未重复跑前端。
- OpenSpec严格校验：8项通过。
- 新正式模块公开探针：arXiv、Anthropic、Nature三条均成功，无付费调用。
- 图谱接口实测属于前一轮本地spike；正式集成离线验证精确DOI、kind、失败降级和预算。
- 预算先预留再push，成功后才给runner额度；CLI安装或认证失败给0额度。每轮最多8条补充，20是每日预留上限。未用完预留不退回。

云端CI、认证和公开归档读回待本次真实Actions结束后补充；不能以离线测试替代。
