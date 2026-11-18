# ChemWatch · 化学数据观测站

**公开的化学数据集与 benchmark 目录，以及可嵌入你自己 AI 的监测 skill。**

[打开网页](https://cynara517.github.io/chemwatch/) · [公开目录 JSON](https://cynara517.github.io/chemwatch/data/catalog.json) · [Agent Skill](skills/chemwatch-monitor/SKILL.md)

浏览网页、安装工具、读取目录都无需 ChatGPT 或 GitHub 登录。CLI只依赖Python 3.10+标准库；你的AI负责理解报告，运行和调度由你选择的harness或本地watcher承担。

## 一行安装 CLI + skill

macOS / Linux，安装到当前用户，不需要sudo：

```sh
curl -fsSL https://cynara517.github.io/chemwatch/install.sh | sh -s -- --agent codex
```

安装内容：`~/.local/bin/chemwatch` CLI、`~/.local/share/chemwatch/chemwatch-monitor`运行时，以及`~/.agents/skills/chemwatch-monitor` skill链接。Codex可发现标准SKILL.md；若未显示，请刷新skills或重启客户端。[Codex skills文档](https://learn.chatgpt.com/docs/build-skills)

对于DeepSeek Harness或其他支持Agent Skills的AI，把实际加载的skills根目录传给安装器。例如使用项目级标准目录：

```sh
curl -fsSL https://cynara517.github.io/chemwatch/install.sh | sh -s -- --skill-dir ./.agents/skills
```

不同harness的技能目录与调度能力可能不同；使用该harness实际支持的目录。安装器不会更改模型提供商、API key或无关配置。它验证技能包SHA-256，并拒绝覆盖不属于它的同名skill或CLI。

安装后，在AI里说：

> 使用 chemwatch-monitor，每天监测逆合成、偶联与杂环、青霉素和红霉素生产相关的数据集与benchmark。有新条目、来源变化或检查失败时报告并附原始来源，无变化保持安静。

也可以让AI先读取本仓库的`skills/chemwatch-monitor/SKILL.md`，识别自己支持的skills路径，再执行安装命令。

## 直接用CLI监测

如果`~/.local/bin`已在PATH上，下面可以省略该前缀。

```sh
~/.local/bin/chemwatch list --topic retrosynthesis --json
~/.local/bin/chemwatch follow --topic retrosynthesis --topic coupling --topic bioprocess
~/.local/bin/chemwatch check --json
~/.local/bin/chemwatch watch --background --interval 86400
~/.local/bin/chemwatch watch --status
~/.local/bin/chemwatch watch --stop
```

`follow`保存订阅并建立首次基线；`check`检查一次；`watch`是实际的本地后台进程。仅安装skill或保存网页偏好不会启动监测。watcher需要电脑开机，未注册开机服务；要在关机时继续监测，可使用harness云端调度或自己的GitHub Actions订阅工作流。

多个topic按“或”匹配：`retrosynthesis`, `coupling`, `materials`, `yield`, `free-energy`, `selectivity`, `bioactivity`, `bioprocess`, `penicillin`, `erythromycin`。

默认公开源来自本GitHub仓库，包含新增目录条目。也可指定自己的JSON源：

```sh
~/.local/bin/chemwatch sync --source https://cynara517.github.io/chemwatch/data/catalog.json --topic yield --probe --json
```

状态、订阅、待发邮件和JSON/Markdown报告保存在`${XDG_STATE_HOME:-~/.local/state}/chemwatch/`，与工作目录无关。使用`follow --config /absolute/path/subscription.json`可管理独立订阅；check/watch使用同一`--config`。

第一次只建立基线，不把所有历史条目当作新发现。没有变化不创建新报告、默认不输出；带`--json`始终返回结构化状态。目录新增、元数据变化、移出订阅范围、上游revision变化分别报告。仓库提交变化不自动等于数据记录增长。API失败保留上次成功版本。

退出码：0成功；1目录/配置读取失败；2部分探测或邮件失败。GitHub匿名API有额度，可选`GITHUB_TOKEN`提高额度。HTTPS失败应修复本机证书或正确设置SSL_CERT_FILE，不应关闭验证。

## 可选邮件

在订阅者的运行环境设置`CHEMWATCH_SMTP_HOST`、`CHEMWATCH_SMTP_FROM`，必要时设置`CHEMWATCH_SMTP_USER`、`CHEMWATCH_SMTP_PASSWORD`。默认STARTTLS/587；可用`CHEMWATCH_SMTP_MODE=ssl`与`CHEMWATCH_SMTP_PORT=465`。

```sh
~/.local/bin/chemwatch follow --topic erythromycin --email you@example.com
~/.local/bin/chemwatch watch --background
```

只有显式指定邮箱才会发变化邮件。初始基线不发；失败报告保留待重试。SMTP响应丢失仍可能重复投递，Message-ID保持稳定。

云端个人订阅见`templates/subscribe.yml`：复制到你自己仓库的`.github/workflows/subscribe.yml`，修改主题和公开源，配置自己的SMTP Secrets，再启用其schedule。状态通过Actions cache保存。安装者无需向本项目提供邮箱密码。

## 公开站点如何更新

`.github/workflows/refresh-and-publish.yml`在main推送、手动运行，以及每天02:00 UTC（北京时间10:00）执行：测试 → 来源探测 → 保存真实快照 → 打包skill → 发布GitHub Pages。

已登记的来源分别监测 GitHub 数据路径或仓库提交、Hugging Face 数据集修订，以及 Zenodo 存档版本与校验和。新资源收录仍需人工核验；编辑`scripts/build_catalog.py`并运行它。目录按family_id统计数据集家族，benchmark套件与持续数据库单列；保留记录的原单位。

在新fork中使用时，在Settings → Pages选择GitHub Actions。将公开源与安装器地址改为自己的仓库；此项目没有网站账户系统，也没有私有平台托管依赖。

## 本地开发与验证

```sh
python3 scripts/build_catalog.py
python3 scripts/refresh.py
python3 scripts/package.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8888 --directory dist
```

打开http://localhost:8888。网页静态，无前端构建依赖。`scripts/package.py`将根目录CLI复制进自包含skill，生成技能ZIP、SHA-256清单、完整源码包与站点安装器。根目录`chemwatch.py`是运行时源码。

当前计数与逐项证据见 [公开目录](dist/data/catalog.json)。已覆盖逆合成、C–C/C–N/C–H与杂环实验、材料评估、自由能、选择性、药物活性及工业青霉素/红霉素。IndPenSim是100批工业规模模拟；EFP是406批真实工业生产数据。C–O/C–S/C–B专用集和分离纯化等数据待补，不将覆盖缺口伪装成全领域数量。

### 历史时间线

首页可按指标与专题切换累计、年度和对数视图。每个点可查数值与来源。[历史序列 JSON](dist/data/timeseries.json) 与建站以来的 [收录快照](dist/data/history.json) 分开发布。

| 指标 | 日期及计量方式 |
| --- | --- |
| 数据集家族、benchmark 套件 | 据本目录最早已核实的论文或公开版本年份回溯，家族或套件计一次。尚未收录的资源不会出现在曲线上。 |
| Materials Cloud 数据集 DOI | 按 DataCite 仓库标识 ethz.marvel 和 Dataset 类型统计每年发表的 DOI，逐年相加与整库总数核对。一个研究的不同版本可能分别有 DOI。[仓库说明](https://archive.materialscloud.org/about) |
| CSD 晶体结构 | 按 CCDC 统计表中的文献发表年。1965 年前的 4,045 条为合并基数，年度图从 1965 年开始。末两年带部分数据标记。[官方统计表](https://www.ccdc.cam.ac.uk/media/CSD-Publication-Year-Statistics-2026.pdf) |
| ChEMBL 活性记录 | 从 release notes 取准备日期、activities 总数，逐年选择最后版本。只计算相邻年份的净差，缺测保持空值，订正可带来负值。[EMBL-EBI 版本档案](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/) |

每日发布任务重新统计 Materials Cloud 的各年份，扫描 ChEMBL 新版本并校验当年 CSD 统计文件。更换 CSD 版本时使用 pdftotext 或 pypdf 解析表格。采集异常会在历史 JSON 中标记，同时保留上次成功观测。论文版及镜像可提供年代或修订证据，一个来源对应的候选数不作为新增资源数。

### 新资源线索

每日对 9 个专题分别查询 Europe PMC、Crossref、GitHub 和 Hugging Face，发布每个平台各专题最近一批待审核线索。论文查询限近 365 天。Europe PMC 按发表日期排序，Crossref 从相关度前 30 条中筛选题名再按日期排序；仓库和数据卡按更新时间取样，按关键词筛选后每组最多展示 5 项。每组附实际查询、最后成功时间与失败状态。完整查询与结果见 [发现记录](dist/data/discovery.json)，已核验资源另存入目录。论文检索覆盖受 Europe PMC 学科范围影响，历史盘点还使用出版社、作者与数据存档。

本目录提供资源元数据与链接，不分发原始化学实验数据；各来源许可独立核实，软件许可不自动用于数据。

代码MIT许可。设计受[Scaling Biology](https://wconnell.github.io/scaling-bio/)启发，独立实现。
