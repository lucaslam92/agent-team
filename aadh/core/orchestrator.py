"""
Orchestrator — The main control loop.

Flow per iteration:
  1. Planner:    task → plan.json + Maestro YAML
  2. Coder:      plan + file contents → modified files + diff
  3. BuildRunner: ./gradlew assembleDebug
  4. DeviceRunner: adb install + launch
  5. UIVerifier:  maestro test
  6. Evaluator:  all logs → EvaluationResult
  7. Decision:   pass → done | fail → next iteration (with feedback)

Feedback routing:
  - Evaluator.suggestion       → Coder (next round)
  - Evaluator.feedback_for_planner → Planner (next round, only if next_action == "fix_plan")
"""

from __future__ import annotations
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from aadh.core.llm import LLMClient, client_from_settings
from aadh.core.models import (
    Plan, CoderOutput, BuildResult, DeviceResult,
    VerificationResult, EvaluationResult, RunStatus, FinalReport,
)
from aadh.core.artifacts import ArtifactStore
from aadh.agents import planner as planner_agent
from aadh.agents import coder as coder_agent
from aadh.agents import evaluator as evaluator_agent
from aadh.runners import build_runner, device_runner, ui_verifier, git_pusher


def run(
    task: str,
    settings: dict,
    commands: dict,
    verbose: bool = True,
) -> FinalReport:
    console = Console() if verbose else None
    cfg      = settings
    proj_cfg = cfg["project"]
    h_cfg    = cfg["harness"]
    llm_cfg  = cfg["llm"]

    project_path  = Path(proj_cfg["path"]).expanduser().resolve()
    app_package   = proj_cfg["app_package"]
    main_activity = proj_cfg["main_activity"]
    max_iter      = int(h_cfg["max_iterations"])
    threshold     = float(h_cfg["pass_threshold"])
    max_files     = int(h_cfg.get("max_files_per_iteration", 5))
    artifacts_dir = Path(h_cfg["artifacts_dir"]).expanduser()

    store = ArtifactStore(artifacts_dir)
    run_id, run_dir = store.new_run(task)

    # Build per-agent LLM clients
    planner_llm   = client_from_settings(llm_cfg.get("planner",   {}), llm_cfg["default"])
    coder_llm     = client_from_settings(llm_cfg.get("coder",     {}), llm_cfg["default"])
    evaluator_llm = client_from_settings(llm_cfg.get("evaluator", {}), llm_cfg["default"])

    if console:
        console.print(Panel(
            f"[bold cyan]Android Auto Dev Harness[/bold cyan]\n"
            f"Task: {task}\n"
            f"Run ID: {run_id}  |  Max iterations: {max_iter}  |  Pass threshold: {threshold}",
            box=box.ROUNDED,
        ))

    current_plan:       Plan | None          = None
    previous_coder:     CoderOutput | None   = None
    coder_feedback:     str | None           = None
    planner_feedback:   str | None           = None
    last_eval:          EvaluationResult | None = None
    all_changed_files:  set[str]             = set()

    for iteration in range(1, max_iter + 1):
        if console:
            console.rule(f"[bold yellow]Iteration {iteration}/{max_iter}[/bold yellow]")

        # ── 1. PLAN ────────────────────────────────────────────────────────
        _log(console, "Planner", "generating plan…")
        current_plan = planner_agent.plan(
            planner_llm,
            task=task,
            project_path=str(project_path),
            app_package=app_package,
            main_activity=main_activity,
            feedback=planner_feedback,
        )
        store.save_plan(run_dir, current_plan)
        if console:
            console.print(f"  Files: {', '.join(current_plan.files) or '(none)'}")

        # Write Maestro flow for this iteration
        if current_plan.maestro_flow:
            flow_dir = run_dir / "maestro"
            flow_dir.mkdir(exist_ok=True)
            (flow_dir / "flow.yaml").write_text(current_plan.maestro_flow, encoding="utf-8")

        # ── 2. CODE ────────────────────────────────────────────────────────
        _log(console, "Coder", "reading files and applying changes…")
        try:
            coder_out = coder_agent.code(
                coder_llm,
                plan=current_plan,
                project_path=project_path,
                iteration=iteration,
                evaluator_feedback=coder_feedback,
                max_files=max_files,
            )
        except Exception as exc:
            if console:
                console.print(f"[red]Coder error: {exc}[/red]")
            break

        store.save_coder_output(run_dir, coder_out)
        all_changed_files.update(c.file_path for c in coder_out.changes)
        previous_coder = coder_out
        if console:
            console.print(f"  Changed: {', '.join(c.file_path for c in coder_out.changes)}")

        # ── 3. BUILD ───────────────────────────────────────────────────────
        _log(console, "Build", "running Gradle…")
        build_result = build_runner.build(
            project_path=project_path,
            assemble_cmd=commands["build"]["assemble"],
            apk_relative_path=commands["build"]["apk_output"],
        )
        store.save_build_log(run_dir, build_result)
        status_str = "[green]OK[/green]" if build_result.success else "[red]FAILED[/red]"
        if console:
            console.print(f"  Build: {status_str}")

        logcat = ""
        verification_result: VerificationResult | None = None

        if build_result.success:
            # ── 4. DEVICE ──────────────────────────────────────────────────
            _log(console, "Device", "installing and launching…")
            device_result, logcat = device_runner.run_on_device(
                apk_path=build_result.apk_path,
                main_activity=main_activity,
                wait_cmd=commands["device"]["wait"],
                install_cmd_tpl=commands["device"]["install"],
                launch_cmd_tpl=commands["device"]["launch"],
                logcat_cmd=commands["device"]["logcat"],
                clear_logcat_cmd=commands["device"]["clear_logcat"],
                run_dir=run_dir,
            )
            store.save_logcat(run_dir, logcat)

            # ── 5. UI VERIFY ───────────────────────────────────────────────
            _log(console, "Maestro", "running UI verification…")
            verification_result = ui_verifier.verify(
                maestro_flow_yaml=current_plan.maestro_flow,
                maestro_cmd_tpl=commands["ui_test"]["run"],
                run_dir=run_dir,
            )
            store.save_maestro_log(run_dir, verification_result)
            v_str = "[green]PASSED[/green]" if verification_result.success else "[red]FAILED[/red]"
            if console:
                console.print(f"  Maestro: {v_str}")

        # ── 6. EVALUATE ────────────────────────────────────────────────────
        _log(console, "Evaluator", "analysing results…")
        last_eval = evaluator_agent.evaluate(
            evaluator_llm,
            plan=current_plan,
            build_result=build_result,
            verification_result=verification_result,
            logcat=logcat,
            iteration=iteration,
        )
        store.save_evaluation(run_dir, last_eval)

        if console:
            _print_eval(console, last_eval)

        # ── 7. DECIDE ──────────────────────────────────────────────────────
        if last_eval.status == RunStatus.SUCCESS:
            _log(console, "✓ PASSED", f"iteration {iteration}", style="bold green")
            break

        if last_eval.next_action == "stop":
            _log(console, "✗ Stopping", "unrecoverable failure", style="bold red")
            break

        # Route feedback for next round
        coder_feedback   = last_eval.suggestion
        planner_feedback = last_eval.suggestion if last_eval.next_action == "fix_plan" else None

    else:
        if console:
            console.print(f"[bold red]✗ Max iterations ({max_iter}) reached.[/bold red]")

    # ── Final report ────────────────────────────────────────────────────────
    if last_eval is None:
        from aadh.core.models import FailureType
        last_eval = EvaluationResult(
            status=RunStatus.FAIL,
            failure_type=FailureType.BUILD_ERROR,
            reason="No iterations completed.",
            suggestion="",
            next_action="stop",
        )

    report = FinalReport(
        task=task,
        status=last_eval.status,
        total_iterations=iteration,
        changed_files=sorted(all_changed_files),
        evaluation=last_eval,
        run_dir=run_dir,
    )
    report_path = store.write_report(run_dir, report)
    if console:
        console.print(f"\n[dim]Report: {report_path}[/dim]")

    # ── Git push on success ───────────────────────────────────────────────────
    git_cfg = cfg.get("git", {})
    if last_eval.status == RunStatus.SUCCESS and git_cfg.get("auto_push", False):
        if previous_coder and current_plan:
            _log(console, "Git", "committing and pushing changes…")
            try:
                sha = git_pusher.commit_and_push(
                    project_path=project_path,
                    plan=current_plan,
                    coder_output=previous_coder,
                    branch=git_cfg.get("branch") or None,
                    remote=git_cfg.get("remote", "origin"),
                )
                _log(console, "Git", f"pushed {sha[:8]}", style="green")
            except git_pusher.GitPushError as exc:
                _log(console, "Git", f"push failed: {exc}", style="yellow")

    return report


def _log(console: Console | None, label: str, msg: str, style: str = "dim") -> None:
    if console:
        console.print(f"[{style}][{label}][/{style}] {msg}")


def _print_eval(console: Console, e: EvaluationResult) -> None:
    scores = e.scores or {}
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Dimension")
    table.add_column("Score", justify="right")
    for k, v in scores.items():
        colour = "green" if v >= 7.5 else "yellow" if v >= 5.0 else "red"
        table.add_row(k, f"[{colour}]{v:.1f}[/{colour}]")
    console.print(table)
    console.print(f"  Status: [bold]{e.status.value}[/bold]  |  "
                  f"Type: {e.failure_type.value}  |  {e.reason}")
