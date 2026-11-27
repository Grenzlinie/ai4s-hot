"""Build the paper landscape from public archive records."""
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import re

# Title matches carry more weight than mentions of a method or application in
# the abstract. The order breaks ties in favor of the scientific application.
AREAS = [
    ("materials", "材料与能源", r"materials? (?:science|design|discovery|prediction|informatics)|materials?\b.{0,30}\b(?:synthesi[sz]|characteri[sz])\w*|interatomic potentials?|machine[- ]learned potentials?|\bmlips?\b|perovskites?|photovoltaics?|crystal (?:structures?|generation|prediction)|alloys?|electrolytes?|solid[- ]state batter\w*|cathodes?|electrodes?|semiconductors?|microstructures?|ceramics?|polymers?|thermoelectric\w*|crystalline materials?|ferroelastic|ferroelectric|phase diagrams?|solid solutions?|\bmofs?\b|metal.organic frameworks?|batter(?:y|ies)|electrocatal\w*"),
    ("chemistry", "化学与分子设计", r"retrosynthesis|cheminformatics|chemical (?:reactions?|identification|synthesis|discovery|research)|reaction (?:prediction|mechanisms?|optimization)|molecular (?:design|generation|property|graph|synthesis)|\bsmiles\b|catalysis|ligand design|quantum chemistry|chemical kinetics|hydrogenation|molecular (?:conformation|dynamics)|organic synthesis|chemical space"),
    ("biology", "生命科学与药物", r"proteins?|biomolecular|genom\w*|transcriptom\w*|clinical|disease|drug (?:design|discovery|development)|bioinformatics|antibod\w*|enzymes?|\b(?:dna|rna|crispr)\b|medical imaging|cellular"),
    ("physics", "物理、数学与计算", r"astrophysics|cosmolog\w*|gravitational|particle physics|fluid dynamics|plasma|quantum (?:computing|systems?|mechanics|circuits?)|physics[- ]informed|scaling laws?|mathematics|mathematical (?:reasoning|discovery|proof)|theorem prov\w*|partial differential|numerical (?:method|solver)|finite element"),
    ("discovery", "科研智能体与实验", r"scientific (?:discovery|research|reasoning|hypotheses|experiment\w*)|research agents?|\bsciagents?\b|autonomous (?:labs?|laborator\w*|experiment\w*)|self[- ]driving laborator\w*|hypothesis generation|lab automation|laboratory execution|automated experiment\w*|experiment design|literature (?:review|retrieval)|scientific workflows?"),
    ("evaluation", "数据集与评测", r"benchmarks?|benchmarking|datasets?|leaderboards?|evaluation suite|verifier|model evaluation|measuring (?:model|llm|ai)|hallucination (?:evaluat\w*|detect\w*)|model (?:judge|judging)|data contamination"),
    ("systems", "代码与计算系统", r"code (?:generation|repair|editing|completion)|coding agents?|software (?:engineering|repositories|development|agents?)|gpu kernels?|parallel computing|compilers?|speculative (?:decoding|draft)|kv cache|(?:gpu|npu) kernel generation|inference (?:acceleration|serving)|distributed training|high[- ]performance computing|\brtl\b|repository[- ]level"),
    ("embodied", "视觉、多模态与机器人", r"computer vision|vision language|video (?:generation|understanding|reasoning)|image (?:generation|segmentation|editing)|text.to.image|scene (?:graphs?|understanding|reconstruction)|multimodal|world models?|\b(?:lidar|3d scene)\b|embodied|robot\w*|dexterous manipulation|spatial (?:reasoning|intelligence)|gui grounding|speech recognition|dialogue data"),
    ("agents", "智能体与推理", r"multi[- ]agents?|\bagentic\b|\bagents?\b|tool (?:use|calling)|chain.of.thought|reasoning|planning|test.time (?:scaling|computation)|agent orchestration|retrieval.augmented"),
    ("models", "模型与学习方法", r"\b(?:llms?|vlms?|gnns?)\b|language models?|foundation models?|deep learning|machine learning|reinforcement learning|\brl\b|distillation|autoregressive|attention|variance reduction|transfer learning|fine.tun\w*|transformers?|diffusion|generative (?:models?|ai)|neural networks?|self.supervised|training|representation learning|embeddings?"),
]
PATTERNS = [(key, re.compile(r"\b(?:" + terms + r")\b", re.I)) for key, _, terms in AREAS]
APPLICATIONS = {"materials", "chemistry", "biology", "physics", "discovery"}
STOP = ("also can using use based approach proposed existing novel paper study work method methods "
        "results demonstrate provide present enables across effectively experiments performance "
        "framework introduction abstract arxiv model models system systems tasks task").split()
CLUSTER_SEED = 23


# Match stable catalog paths rather than archive-specific topic IDs. Roots and
# generic methods such as "training and optimization" cannot place a paper.
FINE_TOPIC_AREAS = {
    "01 材料研究": {
        "materials": (
            "二维材料", "复合与人工结构材料", "多孔框架材料", "无机非金属材料",
            "有机与高分子材料", "跨体系材料研究", "金属与合金",
        ),
    },
    "02 AI方法": {
        "materials": ("表征、预测与分析 / 机器学习势函数",),
        "discovery": (
            "语言模型与 Agent / 自主科研系统", "表征、预测与分析 / 符号学习与科学发现",
        ),
        "embodied": ("表征、预测与分析 / 视觉与多模态表征",),
        "agents": (
            "语言模型与 Agent / 多Agent协作", "语言模型与 Agent / 推理与规划",
            "语言模型与 Agent / 记忆、RAG与知识处理",
        ),
        "models": (
            "学习、训练与优化 / 预训练与后训练", "学习、训练与优化 / 训练目标与多任务优化",
            "学习、训练与优化 / 迁移与元学习", "学习、训练与优化 / 强化学习与Agent RL",
            "表征、预测与分析 / 图学习与结构表征", "表征、预测与分析 / 可解释性与不确定性",
            "生成模型 / VAE与GAN", "生成模型 / 扩散与流模型", "生成模型 / 自回归及其他生成方法",
        ),
    },
    "03 数据集与评测": {
        "evaluation": (
            "数据资源", "评测基准",
            "构建方法与评测可信度 / 任务与基准构建", "构建方法与评测可信度 / 指标、评分器与验证",
            "构建方法与评测可信度 / 数据采集、生成与整理",
        ),
    },
}

TOPIC_PATH_AREAS = {
    f"{root} / {suffix}": area
    for root, groups in FINE_TOPIC_AREAS.items()
    for area, suffixes in groups.items()
    for suffix in suffixes
}

# Specific phrases observed in the archive. Single words like "optimization",
# "generation", "robustness", and "2D" cannot resolve an area on their own.
EXTRA_TERMS = {
    "materials": (
        r"hydrogels?|eutectogels?|polyurethane|hydrogen storage|laser deposition|spinel oxides?"
        r"|crystals?|mxenes?|nanosheets?|layered double hydroxides|material(?:s)? (?:databases?|space)"
        r"|electronic bandgaps?|metallic meshes|dielectric energy storage|negative thermal expansion"
        r"|covalent organic frameworks?|sputtering|ferroelastic strain|sic polytypes"
        r"|atom(?:ic)? structure prediction"
        r"|membrane water electroly[sz]ers?|materials? modeli[sz]ng|dichalcogenide monolayers?"
        r"|carbon[- ]fiber|metal nanomaterials?|osmotic energy harvest\w*|magnetic structures?"
    ),
    "chemistry": (
        r"molecular chemistry|thermolysis|reaction pathways?|acid[-– ]base equilibria"
        r"|epoxidation|electrosynthesis|catalyst discovery|nitrate to ammonia|hydrated electron|confined water|vibrational signatures.{0,75}aqueous solution"
    ),
    "biology": r"organoids?|microbial metabolomics|epithelial barrier repair|tcr[-– ]+pmhc|survival analysis",
    "physics": (
        r"quanti[sz]ation of gravity|magnons?|anharmonicity|computational mechanics"
        r"|neural pde solvers?|threefolds of general type|automatic differentiation|density functional tight binding"
        r"|density functional theory|solid[- ]liquid interfaces?|moir[eé] patterns?|eshelby stability|soliton[- ]lattice"
        r"|vibrational spectroscopy|optical interferometry|self.normalized kullback.leibler estimation"
    ),
    "discovery": (
        r"scientific simulations?|scientific figures|electron microscopy analysis|autoresearch"
        r"|x[- ]ray beamline|self[- ]diagnosing laboratory|instrument automation|ai[- ]scientists?|ai[- ]for[- ]science"
    ),
    "evaluation": (
        r"ai evaluation|evaluation of ai interpretability"
        r"|evaluation of (?:vision|model|language model)|eval(?:uating|uation of) .{0,60}(?:baselines|models?)"
        r"|speech corpus|research dataset|active evaluation for failure discovery"
        r"|bench:\s*evaluat\w*"
    ),
    "systems": (
        r"pipeline[- ]parallel|data center networks?|(?:gpu|npu)[- ]accelerated (?:quadratic|kernel)"
        r"|text[- ]to[- ]sql|linux[- ]rtos|6g ran|compiler optimization|cache ssm inputs"
    ),
    "embodied": (
        r"video edit(?:ing|ors?)|video detection|procedural video|video interactive"
        r"|video world modeling|video[- ]conditioned|vision[- ]language|vla policies|image vectori[sz]ation"
        r"|image tokeni[sz]ation|3d reconstruction|view synthesis|surface reconstruction from images"
        r"|(?:whole[- ]body|loco|bimanual|egocentric|dexterous|household)[- ](?:mobile )?manipulation"
        r"|humanoid(?:s| locomotion)?|quadruped locomotion|multi[- ]object tracking|multi[- ]task ocr"
        r"|music source separation|video[- ]audio generation|keypoint detection|drone navigation"
        r"|dexterous bimanual|articulated object understanding"
        r"|contact[- ]rich manipulation|generative reference rendering|3d cinemagraphs?"
    ),
    "agents": r"harness[- ]model|(?:agent )?harness self[- ]improvement|tool[- ]use policies|autonomous agent",
    "models": (
        r"pre[- ]?training|post[- ]?training|federated learning|reinforcement learning"
        r"|sparse autoencoders?|flow matching|neural operators?|neural synthesis"
        r"|(?:softmax|cross[- ]entropy) (?:loss|and cross[- ]entropy)|low[- ]rank adaptation"
        r"|looped moe models?|generative reward models?|language[- ]model space|energy[- ]based models?"
        r"|streaming decision trees?|class[- ]incremental learning|weight quantization"
    ),
}
CORROBORATING_PATTERNS = dict(PATTERNS)
EXTRA_PATTERNS = {
    area: re.compile(r"\b(?:" + terms + r")\b", re.I)
    for area, terms in EXTRA_TERMS.items()
}


def paper_area(title, excerpt):
    scores = []
    for key, pattern in PATTERNS:
        title_hits = {m.group().lower() for m in pattern.finditer(title)}
        excerpt_hits = {m.group().lower() for m in pattern.finditer(excerpt)}
        score = 5 * min(3, len(title_hits)) + min(3, len(excerpt_hits - title_hits))
        # Scientific domain in a title outranks a generic method in that title.
        if title_hits and key in APPLICATIONS:
            score += 4
        if title_hits and key in {"materials", "chemistry", "biology"}:
            score += 4
        scores.append((score, key))
    score, key = max(scores, key=lambda pair: pair[0])
    return key if score >= 2 else "other"


def recovery_area(item, topic_areas):
    """Recover a broad area using an existing specific label or a clear title."""
    title = item.get("title") or ""
    excerpt = item.get("excerpt") or ""
    if re.match(r"^(?:the )?\d+(?:st|nd|rd|th) international workshop on\b", title, re.I):
        return "other"
    # Accept a new single-domain phrase in a title. Two competing areas stay
    # undecided unless the existing labels supply a clear choice.
    title_areas = {area for area, pattern in EXTRA_PATTERNS.items() if pattern.search(title)}
    # An application named in the title can establish the primary area even
    # when a fine label describes the model used to tackle it.
    if title_areas & (APPLICATIONS | {"embodied", "systems", "evaluation"}):
        title_areas.difference_update({"models", "agents"})
    context = title + " " + excerpt[:420]
    confirmed, inferred = set(), set()
    for label in item.get("topic_labels") or ():
        if label.get("method") == "public_coarse_v1":
            continue
        area = topic_areas.get(label.get("id"))
        if not area:
            continue
        method = label.get("method")
        if method in {"manual", "zotero_exact"}:
            confirmed.add(area)
        elif label.get("confidence") in {"medium", "high"}:
            if title_areas and area not in title_areas:
                continue
            if EXTRA_PATTERNS[area].search(context) or CORROBORATING_PATTERNS[area].search(context):
                inferred.add(area)
    if confirmed:
        if len(confirmed) == 1:
            return next(iter(confirmed))
        agreed = confirmed & title_areas
        return next(iter(agreed)) if len(agreed) == 1 else "other"
    if len(inferred) == 1:
        return next(iter(inferred))
    return next(iter(title_areas)) if len(title_areas) == 1 else "other"


def active_topic_areas(payload):
    result = {}
    taxonomy = payload.get("taxonomy") or {}
    for topic in taxonomy.get("topics", []):
        if not topic.get("active", True) or topic.get("retired"):
            continue
        path = topic.get("catalog_path") or topic.get("path", "")
        if topic.get("id") and path in TOPIC_PATH_AREAS:
            result[topic["id"]] = TOPIC_PATH_AREAS[path]
    return result


def publication_day(value, latest):
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        day = parsed.astimezone(ZoneInfo("Asia/Shanghai")).date() if parsed.tzinfo else parsed.date()
    except ValueError:
        return None
    return day.isoformat() if date(1900, 1, 1) <= day <= latest else None


def cluster_papers(docs, papers):
    from collections import defaultdict
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA, TruncatedSVD
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
    from sklearn.preprocessing import normalize
    from threadpoolctl import threadpool_limits

    if len(docs) < 12:
        return [], "insufficient"
    vectorizer = TfidfVectorizer(
        stop_words=sorted(ENGLISH_STOP_WORDS | set(STOP)), ngram_range=(1, 2),
        min_df=2, max_df=.55, max_features=12000, sublinear_tf=True, dtype=np.float32,
    )
    try:
        vectors = vectorizer.fit_transform(docs)
    except ValueError:
        return [], "insufficient"
    usable = np.flatnonzero(vectors.getnnz(axis=1) >= 4)
    if len(usable) < 12 or vectors.shape[1] < 3:
        return [], "insufficient"
    vectors = vectors[usable]
    count = len(usable)
    with threadpool_limits(limits=2):
        dimensions = min(48, vectors.shape[1] - 1, count - 1)
        compact = normalize(TruncatedSVD(n_components=dimensions, random_state=CLUSTER_SEED).fit_transform(vectors))
        groups = min(10, max(2, round(count ** .25 * 1.36)), count // 6)
        estimator = KMeans(n_clusters=groups, n_init=10, random_state=CLUSTER_SEED).fit(compact)
        positions = PCA(n_components=2, random_state=CLUSTER_SEED).fit_transform(compact)
    groups_by_label = defaultdict(list)
    for row, group in enumerate(estimator.labels_):
        groups_by_label[int(group)].append(row)
    lower, upper = np.percentile(positions, [1, 99], axis=0)
    coordinates = np.clip((positions - lower) / np.maximum(upper - lower, 1e-6), 0, 1)
    vocabulary = vectorizer.get_feature_names_out()
    overall = np.asarray(vectors.mean(axis=0)).ravel()
    clusters = []
    used_ids = set()
    generic = {"ai", "llm", "llms", "machine", "learning", "high", "deep", "scientific", "research"}
    for members in sorted(groups_by_label.values(), key=lambda rows: (-len(rows), int(usable[rows[0]]))):
        if len(members) < 3:
            continue
        inside = vectors[members]
        average = np.asarray(inside.mean(axis=0)).ravel()
        support = inside.getnnz(axis=0)
        priority = average * np.sqrt(average / (overall + .001))
        priority *= np.array([1.3 if " " in term else 1 for term in vocabulary])
        ranked = np.argsort(-priority, kind="stable")
        terms = []
        for index in ranked:
            term = str(vocabulary[index])
            if term in generic or support[index] < max(2, len(members) * .06):
                continue
            if any(term in existing or existing in term for existing in terms):
                continue
            terms.append(term)
            if len(terms) == 7:
                break
        if not terms:
            continue
        label = " / ".join(terms[:2])
        group_id = "c-" + re.sub(r"[^a-z0-9]+", "-", terms[0]).strip("-")
        if group_id in used_ids:
            group_id += f"-{len(clusters) + 1}"
        used_ids.add(group_id)
        center = coordinates[members].mean(axis=0)
        clusters.append({"id": group_id, "label": label, "terms": terms[:5],
                         "x": round(float(center[0]), 4), "y": round(float(center[1]), 4)})
        for row in members:
            point = papers[int(usable[row])]
            point.update(cluster=group_id, x=round(float(coordinates[row, 0]), 4),
                         y=round(float(coordinates[row, 1]), 4))
    return clusters, "ok" if clusters else "insufficient"


def landscape(payload):
    generated_at = payload.get("generated_at")
    latest = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    if generated_at:
        latest = date.fromisoformat(publication_day(generated_at, latest) or latest.isoformat())
    papers, docs = [], []
    topic_areas = active_topic_areas(payload)
    excluded_pending = 0
    for item in sorted(payload["items"], key=lambda p: p["id"]):
        if item.get("type") != "paper":
            continue
        if item.get("journal_relevance", {}).get("status") == "pending":
            excluded_pending += 1
            continue
        if item.get("topic_scope") == "non_research":
            continue
        title = item.get("title") or "未提供标题"
        excerpt = item.get("excerpt") or ""
        area = paper_area(title, excerpt)
        if area == "other":
            area = recovery_area(item, topic_areas)
        papers.append({"id": item["id"], "title": title, "url": item.get("url") or "",
                       "date": publication_day(item.get("published_at"), latest),
                       "area": area, "cluster": None, "x": None, "y": None})
        docs.append(f"{title}. {title}. {excerpt[:2200]}")
    try:
        clusters, status = cluster_papers(docs, papers)
    except ImportError:
        # The reader, domain bars and weekly trends remain usable without the
        # optional clustering runtime in legacy local environments.
        clusters, status = [], "unavailable"
    papers.sort(key=lambda p: (p["date"] or "", p["id"]), reverse=True)
    return {
        "schema_version": 1, "generated_at": generated_at, "as_of_date": latest.isoformat(),
        "areas": [{"id": key, "label": label} for key, label, _ in AREAS] +
                 [{"id": "other", "label": "综合研究"}],
        "clusters": clusters, "papers": papers, "excluded_pending": excluded_pending,
        "method": {"areas": "research-areas-v2", "clustering": "tfidf-kmeans-v1",
                   "projection": "pca-2d", "status": status},
    }


def write_landscape(payload, output):
    data = landscape(payload)
    path = Path(output) / "data" / "landscape.json"
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n",
                    encoding="utf-8")
    print(f"Landscape: {len(data['papers'])} papers, {len(data['clusters'])} clusters ({data['method']['status']})")
