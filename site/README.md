# AI4S Hot

公开的科研进展阅读站，使用 GitHub Actions 采集，GitHub `site-data` 分支持久保存归档，GitHub Pages 发布。这是独立网站项目，不包含邮件推送和 SMTP 配置。

## 数据与运行方式

- `Collect Zotero papers`：每天 22:00 UTC（北京时间次日 06:00）运行。沿用仓库变量 `REPOSITORY` / `REF` 指定的上游实现、Zotero 兴趣向量排序和 TLDR 生成；`site/export_daily.py` 只替换末端运行编排，导出 JSON，不调用邮件发送。
- `Update AI4S Hot`：论文 workflow 结束后更新网站；另在每天 23:43 UTC（北京时间次日 07:43）补跑，也可手动触发。重跑按稳定 URL 去重，单个来源失败时保留已有内容，全部来源失败时不覆盖归档或发布。
- `site-data/data/index.json` 保存完整条目和来源状态，`site-data/data/daily/YYYY-MM-DD.json` 保存按北京时间的首次收录索引。Actions artifact 只作为论文结果交接，不承担长期存储。
- 不发布 Zotero 库条目、文件夹、添加日期或任何凭证。公开条目仅含推荐结果的论文标题、摘要、作者、链接、生成摘要及相关度；Hot 榜单名次与 Zotero 相关度分别保留。
- 界面支持标题、作者和摘要搜索；按来源、发表时间、收录日期、领域筛选；收藏、已读和 JSON 导出。收藏、已读只在当前浏览器存储。

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

凭据和 YAML 也可保存在项目以外的私密目录，通过参数指定路径。同步工具使用标准输入设置 Actions Secrets，YAML 则同步为 `CUSTOM_CONFIG` 变量，同时启用 Zotero 任务。`--run` 会立即触发采集；去掉它仅更新配置。修改本地文件不会自动影响 GitHub，运行同步命令后下一次采集才生效。公开来源及站点采集上限在本地 `site/sources.json` 配置，按普通代码提交更新。无需额外 GitHub token，使用 `gh auth login` 已有身份及 Actions 的内置 token。
