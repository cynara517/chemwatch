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

来源探测针对GitHub数据路径/仓库提交，以及Zenodo存档版本/文件校验和。新资源收录仍需人工核验；编辑`scripts/build_catalog.py`并运行它。目录按family_id统计数据集家族，benchmark套件与持续数据库单列；保留记录的原单位。

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

当前20个种子条目、10个数据集家族、5个benchmark套件、3个持续数据库。已覆盖逆合成、C–C/C–N/C–H与杂环实验、材料评估、自由能、选择性、药物活性及工业青霉素/红霉素。IndPenSim是100批工业规模模拟；EFP是406批真实工业生产数据。C–O/C–S/C–B专用集和分离纯化等数据待补，不将覆盖缺口伪装成全领域数量。

历史曲线按真实观测日积累，不按论文年份伪造。本目录提供资源元数据与链接，不分发原始化学实验数据；各来源许可独立核实，软件许可不自动用于数据。

代码MIT许可。设计受[Scaling Biology](https://wconnell.github.io/scaling-bio/)启发，独立实现。
