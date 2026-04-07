"""
resolve_resources.py

v3 设计说明（§3 执行流程）：
  本脚本是 [MCP + scripts] 协同步骤的 Script 侧实现。
  职责：协调 MCP 调用，将 linked_resources 中的外部资源（Figma / GDoc / GSheet / Confluence）
  实际 fetch 并写入 artifact 文件，供后续 context enrichment 步骤使用。

当前状态：STUB
  MCP 调用部分（fetch_via_mcp）尚未实现，标注为 NotImplemented。
  Script 侧逻辑（路径构建、状态追踪、artifact 写入）已实现。

MCP 接口约定（待接入）：
  每种 source_type 对应一个 MCP 工具：
    - gdoc      → mcp_gdoc_fetch(doc_id: str) -> dict
    - gsheet    → mcp_gsheet_fetch(sheet_id: str) -> dict
    - figma     → mcp_figma_fetch(file_url: str) -> dict
    - confluence → mcp_confluence_fetch(page_url: str) -> dict
  MCP 工具返回标准结构：
    {
      "title": str,
      "content": str,        # 主体文本
      "metadata": dict,      # 来源平台的元数据
      "fetched_at": str      # ISO 8601 时间戳
    }
  接入方式：在 fetch_via_mcp 中替换 raise NotImplementedError，调用对应 MCP 工具即可。
"""

import argparse, json
from pathlib import Path
from datetime import datetime, timezone

def fetch_via_mcp(source_type: str, source_ref: str, source_id: str) -> dict:
    """
    [MCP STUB] 实际 fetch 外部资源。
    接入对应 MCP 工具后，替换此函数体。
    返回标准 MCP 结果结构，失败时抛出异常。
    """
    raise NotImplementedError(
        f"MCP fetch 未实现: source_type={source_type}, source_ref={source_ref}. "
        f"请接入对应 MCP 工具（参见文件头部接口约定）。"
    )

def build_artifact_name(res: dict) -> str:
    return f"{res['resource_type']}_{res['resource_id']}.json"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="normalized_input.json 路径")
    p.add_argument("--resources-dir", required=True, help="artifact 文件存放目录")
    p.add_argument("--output", required=True, help="resource_index.json 输出路径")
    a = p.parse_args()

    normalized = json.loads(Path(a.input).read_text(encoding="utf-8"))
    resources = normalized.get("linked_resources", [])
    raw_dir = Path(a.resources_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    index = []

    for res in resources:
        artifact_name = build_artifact_name(res)
        raw_path = raw_dir / artifact_name

        # 已有 artifact（上次 fetch 缓存），跳过重新 fetch
        if raw_path.exists():
            index.append({
                "resource_id": res["resource_id"],
                "resource_type": res["resource_type"],
                "source_type": res.get("source_type", ""),
                "source_ref": res["source_ref"],
                "artifact_path": str(raw_path),
                "status": "resolved",
                "fetched_at": json.loads(raw_path.read_text(encoding="utf-8")).get("fetched_at", ""),
            })
            continue

        # 尝试 MCP fetch
        try:
            mcp_result = fetch_via_mcp(
                source_type=res.get("source_type", ""),
                source_ref=res["source_ref"],
                source_id=res.get("resource_id", ""),
            )
            artifact = {
                **mcp_result,
                "resource_id": res["resource_id"],
                "resource_type": res["resource_type"],
                "source_type": res.get("source_type", ""),
                "source_ref": res["source_ref"],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            raw_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
            index.append({
                "resource_id": res["resource_id"],
                "resource_type": res["resource_type"],
                "source_type": res.get("source_type", ""),
                "source_ref": res["source_ref"],
                "artifact_path": str(raw_path),
                "status": "resolved",
                "fetched_at": artifact["fetched_at"],
            })
        except NotImplementedError as e:
            # MCP 未实现：标记为 pending_mcp，不阻塞流程
            index.append({
                "resource_id": res["resource_id"],
                "resource_type": res["resource_type"],
                "source_type": res.get("source_type", ""),
                "source_ref": res["source_ref"],
                "artifact_path": str(raw_path),
                "status": "pending_mcp",
                "error": str(e),
            })
        except Exception as e:
            # MCP fetch 失败：标记为 fetch_failed，记录错误，不阻塞流程
            index.append({
                "resource_id": res["resource_id"],
                "resource_type": res["resource_type"],
                "source_type": res.get("source_type", ""),
                "source_ref": res["source_ref"],
                "artifact_path": str(raw_path),
                "status": "fetch_failed",
                "error": str(e),
            })

    result = {
        "resources": index,
        "summary": {
            "total": len(index),
            "resolved": sum(1 for r in index if r["status"] == "resolved"),
            "pending_mcp": sum(1 for r in index if r["status"] == "pending_mcp"),
            "fetch_failed": sum(1 for r in index if r["status"] == "fetch_failed"),
        },
    }

    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
