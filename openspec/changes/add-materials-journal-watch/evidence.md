# 期刊功能实施证据

## 范围与证据边界

2026-10-13 实现10刊官方RSS+Crossref、独立期刊多选、统一分类与相关性待确认。筛选为本地规则，质量未量化。没有扩大LLM或Bohrium预算；待确认条目不请求摘要/正文补全。

## 实现和独立检查

- OpenSpec严格校验通过。registry固定10刊；Crossref200条×10页上限、indexed3天重叠、首次14天，发表窗口90天；部分失败公开partial。按Crossref自身成功游标恢复增量，RSS失败不使成功的Crossref无意义地全量重跑。
- 独立Agent覆盖DOI身份、schema、pending预算隔离、taxonomy/validation故障保留、候选缓存不随页面复制、excluded多来源保留。发现并修复版本类型冲突、partial-only可用结果被整批拒绝；后续检查补充首次同DOI非期刊记录的空日期字段及晚到DOI稳定身份。
- 最终独立集成12/12、Python完整223/223通过。前端原228断言、新期刊26断言通过；合成公开数据Chrome26项通过，独立真实归档Chrome19项通过。真实归档检查未替换网络响应；1440/390两档截图已目检，无JS错误及横向溢出。

## 本地真实数据

- 10刊均实际请求，6ok/4partial/0error。Nature系列RSS在本机TLS/超时失败，未关闭TLS；Nature/Matter部分Crossref请求失败。每刊来源状态保留真实错误边界。
- 去重筛选2167条候选，33相关、516待确认、1618排除。549篇相关/待确认进入index，排除仅候选state保存。不是完整论文索引或人工准确率结果。
- 使用真实私密分类配置在内存读取主题并执行当前分类器，输出747篇归档（198原条目+549期刊）。549条均走分类，59条有非空主题标签；其余保持现有待分类状态。不输出私有参考。
- 本地集成明确no-summary，模型请求0，Bohrium请求0。
- 本地manifest是preview，资源和数据hash准确，但code/archive指针为基线提交下的工作树预览，不作为线上提交证据。
- 原始运行收据保存在工作区 outputs/journal-live-{items,status,registry,state}.json、journal-local-integration.json、journal-integration-independent-checks.json、journal-local-browser/。发布后补充仓库内可复验的摘要收据。

## 线上验收

待实际GitHub Actions与Pages读回后填写；绿色retention不能代替本次采集成功。
