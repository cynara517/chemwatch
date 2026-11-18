"use strict";

function agentCommand(config, codeMode, topicNames, lang) {
  const english = lang === "en";
  const say = (zh, en) => english ? en : zh;
  const cli = "~/.local/bin/chemwatch";
  const remoteCatalog = "https://cynara517.github.io/chemwatch/data/catalog.json";
  const source = config.mode === "remote" ? config.source || remoteCatalog : "./dist/data/catalog.json";
  const installTarget = config.agent === "custom"
    ? "--skill-dir " + shellQuote(config.skillDirectory || "./.agents/skills")
    : "--agent codex";
  const install = "curl -fsSL https://cynara517.github.io/chemwatch/install.sh | sh -s -- " + installTarget;
  const args = [cli, "follow", "--source", shellQuote(source)];
  for (const topic of config.topics) args.push("--topic", shellQuote(topic));
  if (config.delivery === "email") args.push("--email", shellQuote(config.email || "you@example.com"));
  const follow = args.join(" ");
  const topics = topicNames.length ? topicNames.join(english ? ", " : "、") : say("全部方向", "all topics");
  const watch = cli + " watch --background --interval 86400";
  const check = cli + " check --json";

  switch (codeMode) {
    case "install":
      return [
        install, "",
        say("# 安装后，把下面这句话交给你的 Agent。", "# After installing, give your agent this request."),
        say("# 使用 $chemwatch-monitor 每天监测", "# Use $chemwatch-monitor to check the following topics daily: ") + topics + say("。", "."),
        say("# 发现变化或检查失败时通知我。无变化时保持安静。", "# Notify me about changes or failed checks. Stay quiet when nothing changes."),
        "",
        say("# 用 harness 的调度器或 chemwatch watch --background 启动持续监测。",
            "# Start ongoing monitoring with your harness scheduler or chemwatch watch --background.")
      ].join("\n");
    case "cli":
      return [
        say("# 保存订阅并建立首次观测基线", "# Save the subscription and establish a baseline"), follow, "",
        say("# 每天在本机检查一次，电脑需保持开机", "# Check daily while this computer is on"), watch, "",
        say("# 手动检查", "# Check now"), check, "",
        say("# 查看后台监测状态", "# Show watcher status"), cli + " watch --status", "",
        say("# 停止后台监测", "# Stop the watcher"), cli + " watch --stop"
      ].join("\n");
    case "schedule":
      return [
        say("# 让 harness 的调度器每天运行", "# Run daily with your harness scheduler"), check, "",
        say("# 也可以在本机启动每日监测", "# Or start a daily local watcher"), watch, "",
        say("# 在自己的 GitHub 仓库中设置云端订阅", "# To schedule checks in your own GitHub repository"),
        "# templates/subscribe.yml → .github/workflows/subscribe.yml",
        say("# 设置主题和可选的 SMTP Secrets，然后启用 schedule。", "# Set your topics and optional SMTP secrets, then enable the schedule."),
        say("# 公开站点每日刷新。个人订阅使用你配置的调度方式。", "# The public site refreshes daily. Your subscription follows your own schedule.")
      ].join("\n");
    case "agent":
      return [
        say("请从 https://github.com/cynara517/chemwatch 安装 chemwatch-monitor Agent Skill。",
            "Install the chemwatch-monitor Agent Skill from https://github.com/cynara517/chemwatch."), install, "",
        say("请阅读 SKILL.md，并使用当前 harness 实际支持的 skills 目录。", "Read SKILL.md and use the skills directory supported by this harness."),
        say("我关注的主题是", "My topics are ") + topics + say("。", "."),
        say("运行以下命令保存订阅并建立基线。", "Run the following command to save my subscription and establish a baseline."), follow, "",
        say("请每天检查一次。优先使用 harness 的调度器。如果没有调度器，运行以下命令并告诉我启动了哪种机制。",
            "Check daily using the harness scheduler. If it has no scheduler, run the command below. Tell me which mechanism is active."), watch, "",
        say("出现目录新增、元数据变化、上游修订或检查失败时报告，并附原始来源。无变化时保持安静。把仓库提交标为修订，核实数据文件后再报告数据发布。",
            "Report catalog additions, metadata changes, upstream revisions, or failed checks. Link to the primary source. Stay quiet when nothing changes. Label repository commits as revisions and verify the data files before reporting a dataset release."),
        config.delivery === "email"
          ? say("通过运行环境中的 SMTP 配置发送邮件至 ", "Send email using the SMTP settings in the runtime environment. Recipient: ") +
            (config.email || say("待填写的地址", "address to be provided")) +
            say("。若缺少配置或收件地址，请明确说明。", ". Flag missing settings or a missing recipient.")
          : say("使用当前 harness 支持的通知方式。若只能保存本地报告，请告诉我报告位置。",
                "Use the notification channel supported by this harness. If it only supports local reports, tell me where to find them.")
      ].join("\n");
    default:
      throw new Error("Unknown ChemWatch command mode: " + codeMode);
  }
}
