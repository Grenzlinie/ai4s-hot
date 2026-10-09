# AI4S Hot

公开的科研进展阅读站，使用 GitHub Actions 采集，GitHub `site-data` 分支持久保存归档，GitHub Pages 发布。这是独立网站项目，不包含邮件推送和 SMTP 配置。

## 数据与运行方式

- `Collect Zotero papers`：每天 22:00 UTC（北京时间次日 06:00）运行。沿用仓库变量 `REPOSITORY` / `REF` 指定的上游 arXiv 获取、Zotero 兴趣向量排序和 TLDR 生成；先用标题/摘要排序，默认不下载候选论文全文。设置本地 `executor.fetch_full_text=true` 可只对最终推荐论文获取全文；`site/export_daily.py` 只替换末端运行编排，导出 JSON，不调用邮件发送。
- `Update AI4S Hot`：论文 workflow 结束后更新网站；另在每天 23:43 UTC（北京时间次日 07:43）补跑，也可手动触发。重跑按稳定 URL 去重，单个来源失败时保留已有内容，全部来源失败时不覆盖归档或发布。
- `site-data/data/index.json` 保存完整条目和来源状态，`site-data/data/daily/YYYY-MM-DD.json` 保存按北京时间的首次收录索引。Actions artifact 只作为论文结果交接，不承担长期存储。
- 不发布 Zotero 库条目、添加日期或任何凭证。按用户选择，网站会公开 Zotero 分类名称与层级，用于主题导航；不公开 collection key、库内文献记录或用于分类的词表。公开条目仅含推荐结果的论文标题、摘要、作者、链接、生成摘要及相关度；Hot 榜单名次与 Zotero 相关度分别保留。
- 界面支持标题、作者和摘要搜索；按来源、发表时间、收录日期、领域筛选；收藏、已读和 JSON 导出。收藏、已读只在当前浏览器存储。

## Zotero 主题目录

每日使用 pyzotero 读取 collection 层级，沿用材料研究、AI方法、数据集与评测、科研软件与计算工作流及其子目录，排除 `00 待确认`。树形导航支持父类别和细分类别筛选，多标签内容计入所有对应祖先类别。数字表示网站归档条数，不是 Zotero 库条数。

在采集进程内，用各目录已保存论文的标题与摘要构建 TF-IDF 主题特征，给公开聚合内容匹配最多三个相近类别；完全同标题的已有论文沿用库内类别。新内容的标签是自动推断，低相似度内容保留“待分类”。分类不调用外部 LLM，不将库内文献、分类目录或词表发送给摘要服务；分类语料只在进程内存中存在。只有公开新闻的标题和摘录参与原有摘要请求。

目录同步失败时保留上一版目录和已匹配标签；分类结构或库内示例变化时重新计算。前端旧归档没有目录时仍可按原领域筛选。

## 来源

见 `sources.json`。初始回看 30 天；每个来源每次最多 12 条，站内来源状态会明确展示上限，因此这是一份精选聚合，不能作为全部发表论文的完整索引。模型公司通过 Hugging Face Daily Papers 和 Qwen / moonshotai / deepseek-ai 官方模型仓库补充。Daily Papers 是社区精选，不能保证覆盖所有发布。alphaXiv 是近 30 天热门榜，按原始名次单独展示。

Hugging Face Daily API 与官网 HTML 提取需要随来源结构变化维护。Semantic Scholar 查询只覆盖配置中的科学主题，日期上界为本次采集日。来源内容保留原文链接，摘要与网页摘录均标明来源类型。

## 已有配置复用

GitHub Actions Secrets：`ZOTERO_ID`、`ZOTERO_KEY`、`OPENAI_API_KEY`、`OPENAI_API_BASE`、`ALPHAXIV_API_KEY`。可选 `SEMANTIC_SCHOLAR_API_KEY` 可改善共享 API 的限流体验。

`CUSTOM_CONFIG` 复用原采集与 LLM 参数并去掉 `email` 节；Zotero 凭据补齐后设置仓库变量 `ZOTERO_ENABLED=true` 才启动论文推荐，配置未齐时先发布其他来源；新闻中文摘要直接使用其中 `llm.generation_kwargs.model`，无需另设模型。每次新闻摘要最多 24 条，连续 3 次请求失败即停止，未生成的条目显示来源摘录。论文摘要数量仍由既有 `executor.max_paper_num` 决定。

不需要 `SENDER`、`RECEIVER`、`SENDER_PASSWORD`。历史邮件尚未导入；网站的长期归档从首次采集开始。

## Pages 部署

仓库 Settings → Pages → Source 选择 GitHub Actions。`Update AI4S Hot` 在同一 workflow 中使用官方 `upload-pages-artifact` / `deploy-pages` 发布，避免依赖 `GITHUB_TOKEN` 提交再次触发 push workflow。

所有前端资源和数据路径都是相对路径，支持 `https://grenzlinie.github.io/ai4s-hot/` 项目路径。本项目使用独立 Actions Secrets 和数据归档，不修改原 zotero-arxiv-daily 仓库。

## 本地开发与检查

```bash
python -m pip install -r site/requirements.txt
python site/collect.py --data-dir work/data --no-summary
python site/build.py --data-dir work/data --output work/preview
python -m http.server 8765 --directory work/preview
python -m unittest discover -s site/tests -v
node --check site/static/app.js
```

本地 `--no-summary` 不调用 LLM；凭证只通过环境变量传入。`--source` 可重复指定以调试单个来源，不清除其他来源的已有状态。

## 复用与许可证

论文逻辑复用 [TideDra/zotero-arxiv-daily](https://github.com/TideDra/zotero-arxiv-daily)，本仓库继续使用 AGPL-3.0。RSS 和网页解析使用 `feedparser`、`trafilatura`。聚合与归档设计参考 [Horizon](https://github.com/Thysrael/Horizon) 和 [osmosfeed](https://github.com/osmoscraft/osmosfeed)，未复制它们的实现。当前版本选择独立的小型采集器，以便直接复用本仓库 Secrets 和上游论文流程，避免额外维护整套新闻推送服务。

## 本地管理模型与凭据

密钥写入本地 `.env` 文件，填入 `OPENAI_API_KEY`、`OPENAI_API_BASE`、`ZOTERO_ID`、`ZOTERO_KEY`，以及可选 alphaXiv / Semantic Scholar key。本地 YAML 保存原上游采集参数，模型位于 `llm.generation_kwargs.model`；当前使用 `deepseek/deepseek-v4.1-flash`。可复制根目录 `config.example.yaml` 为 `config.local.yaml`。`.env` 和 `config.local.yaml` 已加入 Git 忽略。

```bash
python -m pip install -r site/requirements.txt
chmod 600 .env config.local.yaml
python scripts/configure.py --env .env --config config.local.yaml --run
```

凭据和 YAML 也可保存在项目以外的私密目录，通过参数指定路径。同步工具使用标准输入设置 Actions Secrets，YAML 则同步为 `CUSTOM_CONFIG` 变量，同时启用 Zotero 任务。`--run` 会立即触发采集；去掉它仅更新配置。`llm.summary_kwargs` 控制网页两句摘要的输出预算与 reasoning 参数，独立于上游长摘要的 `llm.generation_kwargs`。OpenRouter 的推理 token 也占输出预算，不能用过小的预算导致正文为空。修改本地文件不会自动影响 GitHub，运行同步命令后下一次采集才生效。公开来源及站点采集上限在本地 `site/sources.json` 配置，按普通代码提交更新。无需额外 GitHub token，使用 `gh auth login` 已有身份及 Actions 的内置 token。

## 默认新版分类与回滚

2026-10-09 起生产工作流明确使用 `TOPICS_MODE=v2`，按 Zotero 已发布的四维目录做本地分类。私密参考文献仅在 runner 内处理；公开页面显示分类依据、状态和网站标签，可在本机修正并导出。词语后端为当前默认；语义后端已提供但不据未测质量自动切换。页面标明“准确率尚未量化”，人工标注是后续质量评估工作，不是本次启用条件。

新版支持历史 schema 1 与新版 schema 2 归档。每次部署的 `deployment-manifest.json` 记录精确的代码、公开归档 commit 与资源 hash。每日分类、同步或构建失败时不提交失败候选归档；流程只用上次有效的不可变快照构建页面，并发布独立update-status.json失败状态，显示最近成功时间。分类按批次事务提交；成功后才生成摘要。

维护者通过 `Restore public Pages snapshot` 手动工作流恢复快照：填入 manifest 中的完整 `code_revision` 和 `archive_revision`。`publish=false` 先生成审查 artifact，`publish=true` 发布；流程只读取公开快照，不采集、不调用摘要模型、不需要服务密钥。历史前端仅支持 schema 1 时禁止与 schema 2 混搭；可使用当前前端搭配历史归档。浏览器收藏、已读和本机修正按条目 ID 保留；退役主题修正需要复核。

实际回滚演练限制：历史schema1归档没有新版稳定主题ID的反向映射，切回该归档期间，新版主题筛选会被清除；收藏、已读保持。恢复schema2后，旧主题链接及本机修正恢复正常。2026-10-09已实际验证公开快照回滚和恢复，当前线上为新版。

维护验收：Update AI4S Hot手动工作流的failure_probe可选taxonomy/classification，默认none。探针只在现有公开输入上注入故障，不读取私有参考或调用采集/摘要API；保留部署成功不表示本次分类成功，请检查update-status及日志。完成演练后选none正常更新清除失败状态。退役主题保留归档浏览和历史标签，不能继续作为有效新纠错目标。
