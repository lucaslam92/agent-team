# Portable Skills

本仓库的 skill 开发源位于：

`skills/`

为了让 Codex 或 Claude Code 以“单独路径加载一组 skill”的方式使用，本仓库会导出一份独立 bundle 到：

`portable-skills/`

## 一键安装

最省事的方式是直接执行一条命令，自动完成导出和安装：

```bash
python scripts/publish_portable_skills.py --target <your_skill_dir>
```

如果希望目标目录里的 skill 以软链接方式指向 bundle，可加 `--mode link`：

```bash
python scripts/publish_portable_skills.py --target <your_skill_dir> --mode link
```

常见示例：

```bash
python scripts/publish_portable_skills.py --target ~/.codex/skills
python scripts/publish_portable_skills.py --target ~/.codex/skills --mode link
```

## 分步导出

运行：

```bash
python scripts/export_portable_skills.py
```

导出完成后，`portable-skills/` 下的每个一级子目录都是一个可加载 skill。

## 使用方式

将 `portable-skills/` 作为你的 skill 搜索路径，或把其中的 skill 目录复制 / 软链接到目标工具的技能目录中。

也可以先导出，再单独用安装脚本安装到目标技能目录：

```bash
python scripts/install_portable_skills.py --target <your_skill_dir>
```

如果你希望目标目录里的 skill 始终指向仓库中的 bundle，而不是复制一份静态副本，可使用软链接模式：

```bash
python scripts/install_portable_skills.py --target <your_skill_dir> --mode link
```

常见分步示例：

```bash
python scripts/install_portable_skills.py --target ~/.codex/skills
python scripts/install_portable_skills.py --target ~/.codex/skills --mode link
```

目录形态如下：

```text
portable-skills/
  prd-mission/
  prd-intake/
  context-build/
  platform-review/
  architect-converge/
  prd-compile/
  semantic-gate/
  graph-builder/
  graph-retrieve/
  code-to-knowledge-interpreter/
  graph-aware-resolver/
  architecture-sync/
  knowledge-collector/
  knowledge-promoter/
  coding-mission-mvp/
  coding-read-inputs/
  coding-select-task-batch/
  coding-resolve-task-context/
  coding-backend-execute-tasks/
  coding-frontend-execute-tasks/
  coding-verify/
  coding-compile-report/
  coding-run-verification-hooks/
```

## 约束

- 不要再包一层额外目录；工具的技能路径应该直接指向 `portable-skills/`
- 每个 skill 目录都应保留 `SKILL.md`
- 跨 skill 调用应依赖 bundle 内的相对路径，而不是仓库根目录
- 若修改了 `skills/` 开发源，重新执行 `python scripts/publish_portable_skills.py --target <your_skill_dir>`，或手动重新导出后再安装
