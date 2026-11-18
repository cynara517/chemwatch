"""Build the reviewed seed catalog. Counts describe the cited version, never live totals."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
entries = []


def add(id, name, kind, family, topics, description, url, year, target, origin, count=None, unit=None, count_note=None, license="待核实", repo=None, path=None, doi=None, note="", record=None):
    e = dict(id=id, name=name, kind=kind, family_id=family, topics=topics.split(), description=description, url=url, publication_year=year, targets=target.split("|"), data_origin=origin, record_count=count, record_unit=unit, count_note=count_note, data_license=license, verified_at="2026-11-17", first_seen="2026-11-17", doi=doi, notes=note, evidence=[{"label":"官方来源 / 原始论文", "url":url}])
    if repo:
        e["monitor"] = {"type":"github", "repo":repo, **({"path":path} if path else {})}
    if record:
        e["monitor"] = {"type":"zenodo", "record":record}
    entries.append(e)


add("uspto-raw", "USPTO · Lowe 原始专利反应", "dataset", "uspto", "retrosynthesis", "美国专利抽取反应的基础语料；用于反应预测与逆合成衍生数据。", "https://figshare.com/articles/dataset/Chemical_reactions_from_US_patents_1976-Sep2016_/5104873", 2017, "反应物预测|反应预测", "专利抽取", doi="10.6084/m9.figshare.5104873", note="专利覆盖1976–2016年9月。与50k、Full同源，家族计数只计一次；记录数及数据许可待逐版本核实。")
add("uspto-50k", "USPTO-50k", "dataset", "uspto", "retrosynthesis", "约五万条、十类反应的常用单步逆合成数据版本。", "https://github.com/connorcoley/retrosim", 2017, "单步逆合成", "专利抽取 / 处理版本", repo="connorcoley/retrosim", path="retrosim/data", note="50k是版本名称，不在本目录中当作实时精确记录数。软件许可与数据许可分开核验。")
add("uspto-full", "USPTO-Full · GLN 处理版本", "dataset", "uspto", "retrosynthesis", "GLN项目提供的清洗、去重与划分流程，用于大规模单步逆合成。", "https://github.com/Hanjun-Dai/GLN", 2019, "单步逆合成", "专利抽取 / 处理版本", repo="Hanjun-Dai/GLN", note="具体清洗版本和划分决定记录数；不与其他USPTO版本相加声称独立反应总量。")
add("paroutes", "PaRoutes", "benchmark", "paroutes", "retrosynthesis", "多步逆合成路线规划的评估框架，提供路线集与评估工具。", "https://github.com/MolecularAI/PaRoutes", 2022, "多步逆合成|路线恢复|路线多样性", "专利路线整理", repo="MolecularAI/PaRoutes", note="n1 / n5各含10,000条路线；集合可能重叠，不合计为20,000条独立路线。按一个benchmark套件计。")
add("ord", "Open Reaction Database", "database", "ord", "coupling yield", "开放反应数据与标准化schema，可按具体反应类型继续整理子集。", "https://github.com/open-reaction-database/ord-data", 2021, "反应条件|产率|反应数据管理", "实验 / 专利等多来源", license="CC-BY-SA-4.0（数据）", repo="open-reaction-database/ord-data", path="data", note="这是持续数据库，不按其内含的每个Dataset文件再重复计为独立数据集家族；具体偶联和杂环子集待整理。")
add("buchwald-hartwig", "Buchwald–Hartwig HTE", "dataset", "bh-hte", "coupling yield", "Doyle / Ahneman高通量C–N偶联实验，常用于产率预测。", "https://doi.org/10.1126/science.aar5169", 2018, "产率|C–N偶联|杂环添加剂效应", "高通量实验", repo="rxn4chemistry/rxn_yields", path="data", note="公开处理表与完整实验/控制实验的计数口径不同，暂不填精确条数；杂环标签指添加剂，不泛指所有底物。")
add("suzuki-hte", "Suzuki–Miyaura HTE · Perera", "dataset", "suzuki-hte", "coupling yield", "流动化学平台的Suzuki–Miyaura C–C偶联高通量实验。", "https://doi.org/10.1126/science.aap9112", 2018, "产率|C–C偶联|反应条件优化", "流动化学 / 高通量实验", count=5760, unit="实验", count_note="原始论文报告规模，非实时更新数", repo="rxn4chemistry/rxn_yields", path="data", note="与Buchwald–Hartwig可位于同一处理仓库，但它们是不同实验家族。")
add("direct-arylation", "Direct Arylation · EDBO", "dataset", "direct-arylation", "coupling yield", "Shields等的咪唑直接C–H芳基化数据，用于贝叶斯反应优化。", "https://doi.org/10.1038/s41586-021-03213-y", 2021, "产率|C–H官能团化|C–C成键|杂环|条件优化", "实验 / 条件网格", count=1728, unit="条件", count_note="12×4×4×3×3条件网格；不是1728类反应", repo="b-shields/edbo", path="experiments/data/direct_arylation", note="关联EDBO优化工具；数据集和软件不重复计数。")
add("denmark-selectivity", "Denmark · CPA 选择性数据", "dataset", "denmark-cpa", "selectivity", "手性磷酸催化N,S-acetal相关反应的选择性建模数据。", "https://pmc.ncbi.nlm.nih.gov/articles/PMC6417887/", 2019, "选择性|ee相关|ΔΔG‡", "实验", count=1075, unit="均值记录", count_note="43×25组合；原始独立重复实验为2150次", note="选择性自由能差ΔΔG‡不同于反应热力学ΔG。ee标签与转换方式需保留温度和符号约定。")
add("sad", "Sharpless Asymmetric Dihydroxylation", "dataset", "sad", "selectivity", "Denmark组公开的不对称双羟基化反应数据与相关工具。", "https://github.com/SEDenmarkLab/SAD", 2025, "ee|不对称催化", "文献 / 实验整理", repo="SEDenmarkLab/SAD", note="数据条数与数据许可待核实；仓库软件许可不能直接等同于数据许可。")
add("rgd1", "RGD1", "dataset", "rgd1", "free-energy", "计算反应数据库，包含反应物、产物、过渡态与Gibbs自由能字段。", "https://github.com/zhaoqy1996/RGD1", 2023, "反应ΔG|势垒ΔG‡|过渡态", "量子化学计算", count=126857, unit="独立反应", count_note="官方组页报告；另有176,992过渡态，两个数量不相加", repo="zhaoqy1996/RGD1", note="R_F / P_F / TS_F等字段及温度、理论水平必须随数据使用说明保存。")
add("freesolv", "FreeSolv", "dataset", "freesolv", "free-energy", "小分子水合自由能的实验值、计算值及模拟输入文件。", "https://github.com/MobleyLab/FreeSolv", 2014, "水合ΔG|不确定性", "实验 + 分子模拟", license="CC-BY-4.0（数据）；MIT（代码）", repo="MobleyLab/FreeSolv", path="database.txt", note="水合自由能不是化学反应自由能；预测任务必须分开。")
add("sampl6", "SAMPL6 · Host–Guest / SAMPLing", "benchmark", "sampl6", "free-energy", "主客体结合自由能与采样方法的盲测挑战及公开结果。", "https://github.com/samplchallenges/SAMPL6", 2017, "结合ΔG|采样收敛|方法评估", "实验 + 模拟评估", repo="samplchallenges/SAMPL6", path="host_guest", note="按SAMPL6一个挑战套件计；不将不同轮次和所有子任务直接视作同一数据集。")
add("matbench", "Matbench", "benchmark", "matbench", "materials", "材料性质机器学习的标准化数据与交叉验证框架。", "https://github.com/materialsproject/matbench", 2020, "材料性质|分类与回归", "实验 + 计算整理", repo="materialsproject/matbench", note="v0.1包含13个任务，本目录按一个benchmark套件计；每个任务有自己的样本与单位。")
add("matbench-discovery", "Matbench Discovery", "benchmark", "matbench-discovery", "materials", "评估机器学习能量模型发现稳定无机晶体的能力。", "https://docs.materialsproject.org/services/ml-and-ai-applications/matbench-discovery", 2023, "晶体稳定性|材料发现", "第一性原理计算 / 评估", repo="janosh/matbench-discovery", path="data", note="与Matbench是不同评估套件；其底层数据与Materials Project可能重叠。")
add("tdc", "Therapeutics Data Commons", "benchmark", "tdc", "bioactivity", "药物发现任务的数据加载、划分与评估套件。", "https://tdcommons.ai/benchmark/overview/", 2021, "药物活性|ADMET|多任务评估", "多来源整理", repo="mims-harvard/TDC", note="按一个套件计；每个子任务需要继续拆解来源、划分、指标和许可。")
add("chembl", "ChEMBL", "database", "chembl", "bioactivity", "人工整理的化合物、生物活性、靶点和实验信息数据库。", "https://www.ebi.ac.uk/chembl/", 2009, "活性|效力|靶点", "文献 / 实验整理", note="实时库与固定版本benchmark分开；暂未接入本平台的ChEMBL版本采集器。")
add("bindingdb", "BindingDB", "database", "bindingdb", "bioactivity", "分子结合亲和力数据，可用于药物活性和亲和力任务。", "https://www.bindingdb.org/rwd/bind/chemsearch/marvin/Download.jsp", 2000, "Ki|Kd|IC50等", "实验 / 文献整理", note="不同终点、实验条件和测量单位不可直接混合；许可和具体快照需再核实。")
add("indpensim", "IndPenSim · 工业青霉素发酵", "dataset", "indpensim", "bioprocess penicillin", "100,000 L工业规模青霉素补料发酵的模拟过程与Raman数据。", "https://data.mendeley.com/datasets/pdnjz7zz5x/2", 2019, "浓度软测量|过程控制|故障检测|生产工艺优化", "工业规模机理模拟", count=100, unit="模拟批次", count_note="Mendeley v2，2019-10-08；模拟数据，不是真实工厂逐批测量", license="CC-BY-4.0", repo="StephenGoldie/indpensim-notebook", doi="10.17632/pdnjz7zz5x.2", note="按一个数据集家族计。仓库探测的是作者notebook提交，不代表Mendeley数据新版本。")
add("erythromycin-efp", "EFP · 红霉素工业发酵", "dataset", "erythromycin-efp", "bioprocess erythromycin", "宜昌东阳光长江药业2022年历史生产数据，小时采样，23项过程变量。", "https://zenodo.org/records/14619074", 2025, "发酵效价|过程软测量", "真实工业生产测量", count=406, unit="发酵批次", count_note="Zenodo v1，平均每批154小时；406是批次而非时间点数", license="CC-BY-4.0（Zenodo元数据）", record="14619074", doi="10.5281/zenodo.14619074", note="目标是chemical potency。不能直接宣称包含得率、生产强度或分离纯化标签；数据许可已通过Zenodo API核实。")

# Earlier editions and paper tables are citable even when they predate data hubs.
original_ids = {row["id"] for row in entries}
add("steroid-binding-1981", "Dunn · 甾体结合亲和力", "dataset", "steroid-binding", "bioactivity", "原论文报告 21 种内源性甾体对两种人血浆载体蛋白的结合亲和力。", "https://doi.org/10.1210/jcem-53-1-58", 1981, "结合亲和力", "实验 / 论文数据表", count=21, unit="甾体", note="按论文可核实年份回溯；同一甾体有多个结合终点。")
add("comfa-steroids", "CoMFA · 甾体 QSAR 评估", "benchmark", "comfa-steroids", "bioactivity", "Cramer 等用甾体的结合活性检验三维 QSAR 预测，原论文给出建模与预测集合。", "https://doi.org/10.1021/ja00226a005", 1988, "结合亲和力预测", "实验 / 论文评估集", note="早期评估集。与甾体亲和力实验可能共享分子，在评估套件中计一次。")
add("tecr-oxidoreductases", "NIST · 氧化还原酶反应平衡数据表", "dataset", "tecr-tables", "free-energy", "Goldberg 与同事整理酶催化反应的平衡常数和反应焓，保留测量条件。", "https://doi.org/10.1063/1.555939", 1993, "表观平衡常数|反应热力学", "文献 / 实验整理", note="1993 年系列第一部分。由 K′ 换算标准变换自由能时需保留温度、pH 等条件。")
add("dud", "DUD · 虚拟筛选评估", "benchmark", "dud", "bioactivity", "用已知配体与匹配的诱饵分子评估对接方法的富集能力。", "https://dud.docking.org/", 2006, "虚拟筛选|配体富集", "实验活性 / 构建诱饵", doi="10.1021/jm0608356")
add("dude", "DUD-E · 虚拟筛选评估", "benchmark", "dude", "bioactivity", "DUD 的重建评估套件，包含 102 个靶点。", "https://dude.docking.org/", 2012, "虚拟筛选|配体富集", "实验活性 / 构建诱饵", count=102, unit="靶点", doi="10.1021/jm300687e", note="DUD-E 重新构建任务与诱饵，按独立命名套件计。")
add("uspto-2014", "USPTO · Lowe 2014 公开版", "dataset", "uspto", "retrosynthesis", "作者公开从美国专利及申请中抽取的反应，随后在 2017 年发布扩大版。", "https://nextmovesoftware.com/blog/2014/02/27/unleashing-over-a-million-reactions-into-the-wild/", 2014, "反应物预测|反应预测", "专利抽取", note="作者的发布公告日期为 2014-02-27；不把所含最早专利年份作为数据集发布年份。")
add("retro-star-190", "Retro* · 190 个多步规划目标", "benchmark", "retro-star-190", "retrosynthesis", "Chen 等随 Retro* 发布的多步逆合成测试任务。", "https://github.com/binghong-ml/retro_star", 2020, "多步逆合成|规划成功率", "专利路线整理", count=190, unit="测试目标", repo="binghong-ml/retro_star", note="底层反应来自 USPTO，按测试套件计一次。")
add("omat24", "OMat24 · 无机材料计算数据", "dataset", "omat24", "materials", "FAIR Chemistry 公开的无机晶体结构与 DFT 计算数据，用于预测能量、力和应力。", "https://huggingface.co/datasets/facebook/OMAT24", 2024, "能量|力|应力", "第一性原理计算", license="CC-BY-4.0", note="2024 年预印本与作者 Hugging Face 数据卡指向同一资源。")
entries[-1]["monitor"] = {"type":"huggingface", "repo":"facebook/OMAT24"}
add("csd", "Cambridge Structural Database", "database", "csd", "materials", "CCDC 汇编的有机与金属有机小分子晶体结构。按发表年份的官方统计可追溯至建库以前。", "https://www.ccdc.cam.ac.uk/CCDCStats/", 1965, "晶体结构", "实验 / 文献整理", note="建库于 1965 年，早期文献回溯至 1923 年。公开统计表与完整结构库的访问条件分别由 CCDC 规定。")

add("heifets-planning", "Heifets–Jurisica · 合成规划题集", "benchmark", "heifets-planning", "retrosynthesis", "作者随 AAAI 2012 论文公开的有机合成规划题与评估程序。", "https://www.cs.toronto.edu/~aheifets/ChemicalPlanning/", 2012, "多步逆合成|规划成功率", "教学题 / 专家整理")
add("retrotransformdb", "RetroTransformDB", "dataset", "retrotransformdb", "retrosynthesis", "由有机化学专家核验的通用逆合成转化规则。", "https://doi.org/10.3390/data3020014", 2018, "逆合成规则", "专家整理", note="统计对象是规则集，不把一条通用规则当作一次实验。")
add("het-retro-cjhif", "Het-retro · CJHIF 杂环成环子集", "dataset", "het-retro-cjhif", "retrosynthesis", "作者从期刊反应数据整理的杂环成环记录，用于单步逆合成。", "https://doi.org/10.1021/acs.jcim.4c02041", 2025, "单步逆合成|杂环", "文献 / 处理版本", repo="duartegroup/Het-retro", note="仅收录 CJHIF 成环子集；同一仓库中的 USPTO 通用训练集沿用原家族。杂环成环并非都属于偶联。")
add("absynth", "AbSynth · 全合成路线集", "dataset", "absynth", "retrosynthesis", "从经典全合成文献回溯整理的机器可读路线，用于分析合成策略。", "https://doi.org/10.1021/jacs.6c08434", 2026, "多步逆合成|全合成路线", "文献 / 专家整理", note="作者通过 Allchemy 向经核验的研究机构提供数据。论文与路线所跨的历史时期采用不同日期。")
# The date evidence identifies this edition or study; an earlier release may exist.
dated_sources = {
    "uspto-50k": "https://pubs.acs.org/doi/10.1021/acscentsci.7b00355",
    "uspto-full": "https://proceedings.neurips.cc/paper/2019/hash/0d2b2061826a5df3221116a5085a6052-Abstract.html",
    "paroutes": "https://doi.org/10.1039/D2DD00015F",
    "matbench": "https://doi.org/10.1038/s41524-020-00406-3",
    "matbench-discovery": "https://arxiv.org/abs/2308.14920",
    "sad": "https://doi.org/10.1021/acscentsci.5c00900",
    "rgd1": "https://doi.org/10.1038/s41597-023-02043-z",
    "freesolv": "https://doi.org/10.1007/s10822-014-9747-x",
    "tdc": "https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/hash/4c56ff4ce4aaf9573aa5dff913df997a-Abstract-round1.html",
    "omat24": "https://arxiv.org/abs/2410.12771",
    "retro-star-190": "https://arxiv.org/abs/2006.15820",
    "csd": "https://www.ccdc.cam.ac.uk/media/CCDC-Newsletter-2015-for-CSD50.pdf",
}
for row in entries:
    row["date_source"] = dated_sources.get(row["id"], row["url"])
    if row["date_source"] != row["url"]:
        row["evidence"].append({"label":"年代依据", "url":row["date_source"]})
    if row["id"] not in original_ids:
        row["first_seen"] = row["verified_at"] = "2026-11-18"
    if row["id"] == "chembl":
        row["notes"] = "历史曲线来自 EMBL-EBI 各版本说明中 activities 的计数。"
catalog = {"schema_version":"1.0", "title":"ChemWatch", "catalog_version":"0.3.0", "reviewed_at":"2026-11-18", "scope":"人工核验的种子目录，非全领域普查。数据集按family_id去重；benchmark按套件计；数据库单列。", "entries":entries}
target = ROOT / "dist/data/catalog.json"
target.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Built {len(entries)} reviewed entries")
