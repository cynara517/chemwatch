---
name: chemwatch-monitor
description: Discover and monitor chemical datasets and benchmarks with ChemWatch. Use for retrosynthesis, coupling and heterocycles, materials, yield, free energy, ee/selectivity, bioactivity, or industrial penicillin/erythromycin data subscriptions and change reports.
---

# ChemWatch monitor

Use the bundled Python CLI at `scripts/chemwatch.py`, resolved relative to this skill's directory. It reads a public GitHub catalog and needs Python 3.10+; no ChatGPT account, model API key, or GitHub login is required. `GITHUB_TOKEN` is optional for higher upstream API limits.

## Choose topics

Map the user's interests to these stable topic IDs; multiple topics mean OR:

| Interest | Topic |
| --- | --- |
| Retrosynthesis, route planning | `retrosynthesis` |
| C–C/C–N/C–H and other coupling, heterocycles | `coupling` |
| Materials benchmarks | `materials` |
| Yield prediction / reaction optimization | `yield` |
| Reaction / hydration / binding ΔG, ΔG‡ | `free-energy` |
| ee, stereoselectivity, ΔΔG‡ | `selectivity` |
| Drug activity / affinity | `bioactivity` |
| Industrial fermentation / process data | `bioprocess` |
| Penicillin or erythromycin production | `penicillin` / `erythromycin` |

## Discover or check once

```sh
python3 <skill-directory>/scripts/chemwatch.py list --topic retrosynthesis --json
python3 <skill-directory>/scripts/chemwatch.py sync --topic retrosynthesis --probe --json
```

Replace `<skill-directory>` with this skill's actual location. The installed `chemwatch` launcher is equivalent if it is on PATH. Use absolute executable and config paths for unattended tasks. `chemwatch --help` lists commands.

## Save a recurring subscription

When the user requests monitoring, save their chosen topics, then check the result:

```sh
python3 <skill-directory>/scripts/chemwatch.py follow --topic coupling --topic bioprocess --json
python3 <skill-directory>/scripts/chemwatch.py check --json
```

The default config, successful-state cache, pending mail, and reports live under `${XDG_STATE_HOME:-~/.local/state}/chemwatch/`, independent of the current project. `follow --config /absolute/path/subscription.json` and `check --config ...` support separate subscriptions. First use establishes a baseline; existing entries are not new discoveries.

For a requested recurring schedule, use an actual scheduler supported by the current harness if one is available. Schedule `check --json`, read its report, and notify only about meaningful changes or failures. If the harness has no scheduler, the portable local watcher can run:

```sh
python3 <skill-directory>/scripts/chemwatch.py watch --background --interval 86400
python3 <skill-directory>/scripts/chemwatch.py watch --status
python3 <skill-directory>/scripts/chemwatch.py watch --stop
```

The local watcher requires the computer to remain on; it writes reports and optionally sends configured email. It does not create an AI conversation or register a boot service. A skill is an integration package, not a scheduler by itself. Tell the user which mechanism actually started. Do not claim unattended monitoring is active after merely installing the skill or saving preferences.

## Interpret reports

- Exit 0: baseline, changed, or unchanged. `--json` always emits machine-readable output; default text stays quiet when unchanged.
- Exit 1: catalog/config read or validation failure. Preserve the previous good state.
- Exit 2: partial upstream failure or email failure. Inspect `errors` / `email_error`; failed probes retain their previous successful revision.
- Distinguish `added`, `changed`, `removed`, and `upstream_changes`. A Git commit is an upstream signal, not proof of more data records. Follow evidence links before reporting a dataset release.
- Counts are curated catalog coverage. Count dataset families by `family_id`, benchmark suites separately, and retain record units. Do not sum USPTO versions, reaction conditions, routes and fermentation batches.
- IndPenSim is industrial-scale simulation; EFP is real industrial production data. ΔG, ΔG‡ and ΔΔG‡ are different prediction targets.

## Email

Use `follow --email recipient@example.com` only for the recipient and notification intent requested by the user. Read SMTP credentials from the runtime environment: `CHEMWATCH_SMTP_HOST`, `CHEMWATCH_SMTP_FROM`, optionally `CHEMWATCH_SMTP_USER` and `CHEMWATCH_SMTP_PASSWORD`. Default is STARTTLS on port 587; `CHEMWATCH_SMTP_MODE=ssl` selects TLS on 465. Never put credentials into chat, committed files, or the public catalog. Failed deliveries stay queued for retry; the initial baseline sends no email.

Project: https://github.com/cynara517/chemwatch

Catalog: https://cynara517.github.io/chemwatch/data/catalog.json

## 历史与论文线索

回答历史增长问题时，使用公开的 [历史序列](https://cynara517.github.io/chemwatch/data/timeseries.json)，保留指标、单位、年度、来源及缺测标记。目录发布年、CSD 结构发表年、ChEMBL 版本准备年分别解释。GitHub 提交和 Hugging Face 数据仓库修订均可能仅改动说明。
需要核查新论文和仓库时，读取 [公开检索线索](https://cynara517.github.io/chemwatch/data/discovery.json)，按主题取每组最后成功结果并标注候选身份。常规订阅报告使用审核后的目录及登记来源的实际修订。
