"""
prd-intake-check Skill

职责（v3 §9.1）：task 分类 / requirement 提取 / completeness 检查

输入：
  --input   normalized_input.json 路径
  --output  intake_result.json 路径

输出关键字段：
  task_type        : new_feature | enhancement | bug_fix | breaking_change | config_change | skip_prd
  affected_platforms: list[str]
  completeness     : complete | incomplete
  missing_info     : list[str]
  status           : proceed | blocked | skip_prd
"""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic

SYSTEM_PROMPT = """你是一个专业的产品需求分析师。你的任务是分析输入的需求描述，完成以下工作：

1. **task_type 分类**（从以下类型中选一个）：
   - new_feature：全新功能
   - enhancement：已有功能的增强
   - bug_fix：缺陷修复
   - breaking_change：会破坏已有接口/行为的变更
   - config_change：纯配置/文案/样式等低风险变更
   - skip_prd：无需撰写 PRD 的微小改动（如错别字修正、颜色微调）

2. **affected_platforms 识别**：从以下范围选择实际受影响的平台：
   android, ios, web, backend, cross（跨端）

3. **completeness 判断**：
   - complete：需求描述完整，可直接进入 PRD 生成
   - incomplete：关键信息缺失，无法撰写 PRD

4. **missing_info 提取**：若 completeness=incomplete，列出缺失的具体信息项

5. **status 决策**：
   - proceed：信息完整，可继续
   - blocked：信息不完整，需用户补充（对应 completeness=incomplete）
   - skip_prd：无需生成 PRD

请以 JSON 格式输出，包含以下字段：
{
  "task_type": "...",
  "affected_platforms": [...],
  "completeness": "complete|incomplete",
  "missing_info": [...],
  "status": "proceed|blocked|skip_prd",
  "summary": "一句话需求摘要（不超过100字）",
  "domains": ["payment", "order", ...],
  "signals": {
    "mentions_backend": true/false,
    "mentions_ui": true/false,
    "mentions_state_flow": true/false
  }
}

只输出 JSON，不要添加任何其他文字。"""


def run_intake_check(normalized_input: dict) -> dict:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    # 构造输入文本
    input_text = json.dumps(normalized_input, ensure_ascii=False, indent=2)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"请分析以下需求输入：\n\n{input_text}",
            }
        ],
    )

    raw = message.content[0].text.strip()

    # 提取 JSON（防止模型在 JSON 前后加了说明文字）
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"模型返回内容中未找到 JSON：{raw[:200]}")

    result = json.loads(raw[start:end])

    # 补齐必要字段（防御性处理）
    result.setdefault("task_type", "new_feature")
    result.setdefault("affected_platforms", [])
    result.setdefault("completeness", "incomplete")
    result.setdefault("missing_info", [])
    result.setdefault("status", "blocked" if result["completeness"] == "incomplete" else "proceed")
    result.setdefault("domains", [])
    result.setdefault("signals", {})

    # v3 §3.1: skip_prd 时强制 status=skip_prd
    if result["task_type"] == "skip_prd":
        result["status"] = "skip_prd"

    return result


def main():
    p = argparse.ArgumentParser(description="PRD Intake Check Skill")
    p.add_argument("--input", required=True, help="normalized_input.json 路径")
    p.add_argument("--output", required=True, help="intake_result.json 输出路径")
    a = p.parse_args()

    normalized_input = json.loads(Path(a.input).read_text(encoding="utf-8"))
    result = run_intake_check(normalized_input)

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # 早退出信号：将 status 打印到 stdout，供调用方检测
    print(json.dumps({"status": result["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
