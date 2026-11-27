# CynaraWatch · Shifan Chen

A bilingual home for **My Benchmarks**, **My Papers** and **ChemWatch**. The existing repository URL, data feeds, CLI and monitoring skill remain available.

[Visit CynaraWatch](https://cynara517.github.io/Cynarawatch/) · [My Benchmarks](https://cynara517.github.io/Cynarawatch/benchmarks/index.html) · [My Papers](https://cynara517.github.io/Cynarawatch/papers/index.html) · [ChemWatch](https://cynara517.github.io/Cynarawatch/chemwatch.html)

Build the shared navigation and bilingual pages with `python3 scripts/build_site.py`. Paper translations are maintained in `content/papers-translations.json`; Chinese stories live in `dist/papers/app.js`. Third-party paper figures retain their source licenses; see `dist/papers/assets/ATTRIBUTION.md`.

## ChemWatch tools and data


**English** | [简体中文](README.zh-CN.md)

**A public catalog of chemical datasets and benchmarks, with a portable monitoring CLI and Agent Skill for your own AI.**

[Website](https://cynara517.github.io/Cynarawatch/) · [Public catalog JSON](https://cynara517.github.io/Cynarawatch/data/catalog.json) · [Agent Skill](skills/chemwatch-monitor/SKILL.md)

Browsing the website, installing the tools and reading the catalog require no ChatGPT or GitHub account. The CLI uses only the Python 3.10+ standard library. Your AI interprets reports; your chosen harness or the local watcher handles execution and scheduling.

## Install the CLI and skill

On macOS / Linux, install for the current user without sudo:

```sh
curl -fsSL https://cynara517.github.io/Cynarawatch/install.sh | sh -s -- --agent codex
```

This installs the CLI at `~/.local/bin/chemwatch`, the runtime at `~/.local/share/chemwatch/chemwatch-monitor`, and a skill link at `~/.agents/skills/chemwatch-monitor`. If the skill does not appear in Codex, refresh skills or restart the client. See the [Codex skills documentation](https://learn.chatgpt.com/docs/build-skills).

For DeepSeek Harness or another Agent Skills-compatible AI, pass the skills directory actually used by that harness. For example, a project-level directory:

```sh
curl -fsSL https://cynara517.github.io/Cynarawatch/install.sh | sh -s -- --skill-dir ./.agents/skills
```

Skill paths and scheduling capabilities vary by harness. The installer does not change your model provider, API keys or unrelated configuration. It verifies the skill archive's SHA-256 checksum and refuses to overwrite an unrelated skill or CLI with the same name.

After installation, ask your AI:

> Use chemwatch-monitor to check chemistry reasoning benchmarks, retrosynthesis, coupling and heterocycles, and penicillin and erythromycin production datasets daily. Report new entries, source changes or failed checks with original-source links. Stay quiet when nothing changes.

You can also ask your AI to read `skills/chemwatch-monitor/SKILL.md`, identify its supported skill directory, and run the appropriate installation command.

## Monitor from the CLI

You can omit `~/.local/bin/` if it is already on your PATH.

```sh
~/.local/bin/chemwatch list --topic chemistry-ai --json
~/.local/bin/chemwatch follow --topic chemistry-ai --topic retrosynthesis --topic bioprocess
~/.local/bin/chemwatch check --json
~/.local/bin/chemwatch watch --background --interval 86400
~/.local/bin/chemwatch watch --status
~/.local/bin/chemwatch watch --stop
```

`follow` saves a subscription and establishes its first baseline; `check` runs once; `watch` starts a real local background process. Installing the skill or saving website preferences alone does not start monitoring. The watcher requires your computer to stay on and does not register a startup service. To monitor while your computer is off, use a harness's cloud scheduler or your own GitHub Actions subscription workflow.

Multiple topics match with OR: `chemistry-ai`, `retrosynthesis`, `coupling`, `materials`, `yield`, `free-energy`, `selectivity`, `bioactivity`, `bioprocess`, `penicillin`, `erythromycin`.

The default public source comes from this repository and includes newly reviewed catalog entries. You can also use another catalog JSON source:

```sh
~/.local/bin/chemwatch sync --source https://cynara517.github.io/Cynarawatch/data/catalog.json --topic yield --probe --json
```

State, subscriptions, pending emails and JSON/Markdown reports are stored under `${XDG_STATE_HOME:-~/.local/state}/chemwatch/`, independently of your working directory. Use `follow --config /absolute/path/subscription.json` for a separate subscription, and pass the same `--config` to `check` and `watch`.

The first run establishes a baseline without reporting every historical entry as new. Unchanged runs create no new report and are quiet by default; `--json` always returns structured status. New entries, metadata changes, entries leaving the subscription and upstream revisions are reported separately. Repository commits do not automatically mean more data records. API failures retain the last successful revision.

Exit codes: 0 for success, 1 for catalog/configuration failure, and 2 for partial probe or email failures. An optional `GITHUB_TOKEN` increases the GitHub API allowance. Fix your local certificates or set `SSL_CERT_FILE` correctly if HTTPS verification fails; do not disable verification.

## Optional email

Set `CHEMWATCH_SMTP_HOST` and `CHEMWATCH_SMTP_FROM` in the subscriber's environment, plus `CHEMWATCH_SMTP_USER` and `CHEMWATCH_SMTP_PASSWORD` if required. The default is STARTTLS on port 587; use `CHEMWATCH_SMTP_MODE=ssl` and `CHEMWATCH_SMTP_PORT=465` for implicit TLS.

```sh
~/.local/bin/chemwatch follow --topic erythromycin --email you@example.com
~/.local/bin/chemwatch watch --background
```

Change emails are sent only when an email address is explicitly configured. The initial baseline sends no email. Failed delivery remains pending for retry. A lost SMTP response can still cause a duplicate delivery; the Message-ID remains stable.

For personal cloud subscriptions, copy `templates/subscribe.yml` into your own repository's `.github/workflows/subscribe.yml`, set the topics and public source, configure your own SMTP Secrets, and enable its schedule. State is retained through Actions cache. You do not need to share email credentials with this project.

## How the public site updates

`.github/workflows/refresh-and-publish.yml` runs on pushes to `main`, manual dispatch and daily at 02:00 UTC (10:00 China Standard Time). It runs tests, probes sources, saves real observations, packages the skill and publishes GitHub Pages. Reviewed catalog changes are built locally and committed with their source. Scheduled runs may start later than the configured time.

Registered sources monitor DeltaScience's public chemistry task catalog, GitHub repository or data-path commits, Hugging Face dataset revisions, and Zenodo archive versions and checksums. New resources still require source review: edit `scripts/build_catalog.py` and run it. Dataset families are deduplicated by `family_id`; benchmark suites and ongoing databases are counted separately. Original record units are preserved.

For a fork, select GitHub Actions in Settings → Pages and update the public-source and installer URLs. The project has no website account system or private hosting dependency.

### Catalog additions — November 27, 2026

The new `chemistry-ai` topic covers chemistry reasoning and agents across website filters, CLI subscriptions and daily discovery searches. Additions include ChemBench, ChemIQ, ChemToolBench, CompChemBench, OPRD-target, ChemInsight and [DeltaScience](https://deltascience.bohrium.com/). Each catalog entry records its original sources, date evidence and version/count caveats. ChemInsight is currently verified from its paper; a separate data download and data license remain unconfirmed.

DeltaScience counts as one suite. Daily monitoring reads the official public task table, selects the primary Chemistry category, publishes a [per-task snapshot](dist/data/deltascience.json), and detects changes to task IDs, titles and research directions. This scope does not include every cross-disciplinary chemistry tag. Individual tasks are not counted as separate datasets or benchmark suites. Parsing failures retain the last successful snapshot and expose an error. Task downloads and licenses require per-task verification.

Automatic refresh does not automatically admit every new benchmark. Daily jobs refresh observations and discovery candidates; admission to the reviewed catalog requires checking original papers or author resources. Keyword searches and bounded sampling cannot guarantee complete coverage.

## Local development and validation

```sh
python3 scripts/build_catalog.py
python3 scripts/refresh.py
python3 scripts/package.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8888 --directory dist
```

Open [localhost:8888](http://localhost:8888). The site is static, with no frontend build dependencies. `scripts/package.py` copies the root CLI into the self-contained skill and generates the skill ZIP, SHA-256 manifest, source toolkit and website installer. `chemwatch.py` at the repository root is the runtime source of truth.

See the [catalog](dist/data/catalog.json) for current counts and item-level evidence. Coverage includes chemistry reasoning and agents, retrosynthesis, C–C/C–N/C–H and heterocycle experiments, materials evaluation, free energy, selectivity, bioactivity and industrial penicillin/erythromycin production. IndPenSim contains 100 industrial-scale simulated batches; EFP contains 406 real industrial production batches. Dedicated C–O/C–S/C–B and separation/purification datasets remain coverage gaps.

### Historical timelines

The website supports cumulative, annual and logarithmic views by metric and topic, with values and sources for each point. [Historical series](dist/data/timeseries.json) and [catalog coverage snapshots](dist/data/history.json) are published separately.

| Metric | Dates and counting method |
| --- | --- |
| Dataset families and benchmark suites | Reconstructed from the earliest verified paper or public-release year in this catalog, counting each family or suite once. Resources not yet cataloged are absent. Entries with only a first-verification year explicitly state this limitation. |
| Materials Cloud dataset DOIs | Annual publication counts from DataCite for repository identifier `ethz.marvel` and type Dataset, reconciled against the repository total. Different versions can have separate DOIs. [Archive documentation](https://archive.materialscloud.org/about). |
| CSD crystal structures | Literature publication year from CCDC's statistics. The 4,045 pre-1965 entries form a combined baseline; annual views start in 1965. The final two years are marked partial. [Official statistics](https://www.ccdc.cam.ac.uk/media/CSD-Publication-Year-Statistics-2026.pdf). |
| ChEMBL activity records | Preparation dates and activity totals from release notes, using the final release per year. Annual changes use adjacent years only; gaps remain missing and corrections may be negative. [EMBL-EBI release archive](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/). |

Daily publishing refreshes Materials Cloud's annual counts, scans new ChEMBL releases and checks the current-year CSD statistics file. CSD PDF updates use `pdftotext` or `pypdf` to parse the table. Failures are recorded in the historical JSON while retaining the previous successful observation. Papers and mirrors may establish dates or revisions; search candidate counts do not represent new resources.

### Public OpenReview submissions

Daily title searches use OpenReview API 2 and API 1 for older venues, reading all result pages. Root-post and submission-invitation checks exclude reviews, comments and imported external references. Ambiguous topics also require chemistry or fermentation context. Each public forum ID counts once overall; topic memberships may overlap.

Curves use the submission record's creation date (`cdate`, UTC); `odate` is shown separately as the first-public date. Records without a creation date remain in the detailed list only. Venue text is preserved from the source. The same work submitted to different venues may have multiple forums. API or pagination failures retain the previous complete snapshot. Inspect [queries and submission records](dist/data/openreview.json) to audit the data. Submissions do not automatically increase dataset-family, benchmark-suite or experimental-record counts.

### Discovery candidates

Daily searches cover 10 topics across OpenReview, Europe PMC, Crossref, GitHub and Hugging Face. Europe PMC and Crossref searches cover the past 365 days. Europe PMC sorts by publication date; Crossref filters titles from the top 30 relevance results and then sorts by date. Repository and dataset-card searches sample recently updated results, apply keyword filters and show at most five candidates per group.

Each group includes its actual query, last successful timestamp and error status. [Discovery JSON](dist/data/discovery.json) contains full queries and results; reviewed resources belong in the catalog. Europe PMC coverage is constrained by its subject scope. Historical review also uses publishers, authors and data archives.

This catalog distributes resource metadata and links, not raw chemical experimental data. Verify each source's data license separately: a software license does not automatically cover its datasets.

Code is MIT-licensed. Design inspired by [Scaling Biology](https://wconnell.github.io/scaling-bio/), independently implemented.

## My benchmark design notes

[Explore the bilingual portfolio](https://cynara517.github.io/Cynarawatch/benchmarks/) by **Shifan Chen**, presenting four chemistry tasks contributed to DeltaScience: C-01, CSF-1, CSF-2 and CSF-3. Each v1.0 note covers research inspiration, scientific motivation, tools, verification criteria and reflections on model performance.

The preserved public score snapshot is dated November 25, 2026 and was saved on November 27. Tables list the model, harness and score out of 100, identifying incomplete sets of scored rounds. Pending rounds are excluded from the mean.

Edit `content/benchmarks.json` and run `python3 scripts/build_benchmarks.py` to regenerate the static pages. The portfolio shares the main site's language preference and can be read offline; external papers still require an internet connection. Only curated design notes and public metadata are included.
