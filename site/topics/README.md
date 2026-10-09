# 分类 v2 影子运行

生产分类默认仍为 v1（`TOPICS_MODE` 未设置）。v2 尚未通过人工金标准质量门禁，不应据合成测试或覆盖率宣布准确率达标。

`catalog.yaml` 保存 53 个公开目录节点的定义和同义词；`catalog_path` 在目录更名/移动后保留定义绑定。`thresholds.yaml` 是待人工 dev 校准的初始配置。语义候选是可选的本地 CPU 后端，固定模型 revision，默认不启用。

## 配置与预览

私密配置位于仓库外的0600文件 `ai4s-topics.private.yaml`，包含独立 `id_salt` 和四个已发布根的 `publish_root_keys`，经 `scripts/configure.py --topics-private` 的 stdin 上传 `ZOTERO_TOPIC_CONFIG` Secret。备份这个文件以保持永久身份。新增根需维护者显式加入；只读 Zotero，网站纠错不会回写库。

```bash
python scripts/configure.py --env /private/path/ai4s-hot.env --config /private/path/ai4s-hot.yaml --topics-private /private/path/ai4s-topics.private.yaml
python scripts/run_topics_shadow.py --input site/topics/evaluation/baseline-input.json --output /tmp/public-shadow/index.json --receipt /tmp/public-shadow/receipt.json
python site/build.py --data-dir /tmp/public-shadow --output /tmp/shadow-site
```

运行前通过安全环境加载 `ZOTERO_ID`、`ZOTERO_KEY`、`ZOTERO_TOPIC_CONFIG`。影子流程只发布公共候选和汇总收据，不写生产 `site-data`。完整私有参考仅在内存，不保存向量、参考标题或原始身份 hash。

## 维护与回滚

本机纠错只作用当前浏览器；填写公开理由后导出，维护者用 `python site/topics_curate.py --help` 检查并导入。人工记录优先，删除目标或定义版本变化转待复核。旧 ID 用 registry aliases 迁移，永久 ID 不重定向；item ID 和 `first_seen` 不变，因此收藏和已读沿用。

`python site/topics_reclassify.py --input public-index.json` 默认仅输出公共 diff，指定 `--item` 可局部 backfill，`--output` 才原子写候选；不会请求 LLM 或重生成摘要。发布门禁未过时不替换生产数据。最终切换需先记录上一个 `site-data` commit 与前端 SHA，回滚使用该公开归档及前端重新 build/deploy，无需重新生成摘要。

`evaluation/README.md` 说明人工评审与质量门禁。OpenSpec active change 持续记录剩余工作；全部验收前不 archive。
