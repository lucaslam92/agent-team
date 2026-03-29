"""
Harness Engineering demo — build a complete music software tool.

This mirrors the Anthropic example from the video: using the 3-agent
harness (planner → generator → evaluator) to produce reliable software
that a single agent would produce as brittle/broken code.

Usage:
    python example.py

    # Or with a custom goal:
    python example.py --goal "Build a CLI task manager with priorities and due dates"

    # Adjust quality bar:
    python example.py --threshold 8.0 --iterations 5
"""

import argparse
import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

from harness.orchestrator import run
from harness.evaluator import Dimension

load_dotenv()

MUSIC_GOAL = """\
Build a self-contained Python CLI music sequencer. A user should be able to:
  - Define a short melodic pattern using note names (e.g. C4, D4, E4)
  - Set a tempo (BPM)
  - Play the pattern in a loop using the system speaker (no external audio files)
  - Save and load patterns to/from JSON files
The tool must work without installing any audio library beyond the Python stdlib.
"""

# Custom dimensions for a music tool — shows that dimensions are swappable
MUSIC_DIMENSIONS = [
    Dimension("runnable",      "Can this code run without modification? No import errors, no NameErrors.", 0.35),
    Dimension("completeness",  "All four features present and usable: define, play, save, load.",          0.30),
    Dimension("cli_ux",        "Is the CLI intuitive? Good help text, sensible defaults, clear errors.",    0.20),
    Dimension("code_quality",  "Readable, well-structured, handles edge cases (invalid notes, bad BPM).",   0.15),
]


def main():
    parser = argparse.ArgumentParser(description="Harness Engineering demo")
    parser.add_argument("--goal",       default=MUSIC_GOAL, help="What to build")
    parser.add_argument("--threshold",  type=float, default=7.5, help="Pass score (0-10)")
    parser.add_argument("--iterations", type=int,   default=4,   help="Max attempts")
    parser.add_argument("--output",     default="output.py", help="Write artifact to file")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    console = Console()

    result = run(
        goal=args.goal,
        max_iterations=args.iterations,
        pass_threshold=args.threshold,
        dimensions=MUSIC_DIMENSIONS,
        verbose=True,
    )

    # Write artifact to file
    with open(args.output, "w") as f:
        f.write(result.artifact)

    console.print(Panel(
        f"[bold]Artifact written to[/bold] [cyan]{args.output}[/cyan]\n"
        f"Final score: [bold]{result.final_score:.1f}/10[/bold]  "
        f"Iterations: {result.iterations}  "
        f"Status: {'[green]PASSED[/green]' if result.passed else '[red]DID NOT PASS[/red]'}",
        title="Result",
    ))

    # Show a preview
    console.print("\n[dim]--- Artifact preview (first 40 lines) ---[/dim]")
    preview = "\n".join(result.artifact.splitlines()[:40])
    console.print(Syntax(preview, "python", theme="monokai", line_numbers=True))


if __name__ == "__main__":
    main()
