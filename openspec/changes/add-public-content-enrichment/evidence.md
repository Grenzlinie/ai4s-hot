# 验收记录

代码发布：76af0f9。用户2026-10-13授权Bohrium每天最多20次，允许复用本机AccessKey为Actions Secret。普通设置保留在本地YAML，密钥保存于0600环境文件和GitHub Secret。

- 独立Python：184/184，其中新增24项。
- 前端：29+67+132=228断言，后续仅后端/workflow调整未重复跑前端。
- OpenSpec严格校验：8项通过。
- 新正式模块公开探针：arXiv、Anthropic、Nature三条均成功，无付费调用。
- 图谱接口实测属于前一轮本地spike；正式集成离线验证精确DOI、kind、失败降级和预算。
- 预算先预留再push，成功后才给runner额度；CLI安装或认证失败给0额度。每轮最多8条补充，20是每日预留上限。未用完预留不退回。

真实云端首轮：CI 38338323102成功，Pages 38338323116成功，固定CLI安装与认证成功。176条归档，本轮新摘要20、失败0；公开正文补充6条、降级2条、Bohrium查询0次。

最终7042ea2：CI 38338582534成功，Pages 38338582597成功；公开归档66f917c548e281ff8b79971954befaa481c87606，线上SHA256与manifest一致，update-status=ok。176条，保留6条public_html依据。当天预算reserved20；第二轮CLI安装skipped，实际Bohrium0次。预算是预留而非实际消耗，不能把reserved20说成查询或扣费20次。

本次云端没有触发LKM图谱查询；成功认证不等同于图谱内容成功。服务能力取自前一轮真实spike，正式适配的DOI/kind/故障路径已独立测试。
