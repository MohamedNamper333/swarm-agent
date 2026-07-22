#!/usr/bin/env python3
"""Summarize all .md files in the current directory with line and word counts."""

import glob
import os

def summarize_markdown_files():
    """Read all .md files and produce a summary markdown file."""
    md_files = sorted(glob.glob("*.md"))

    if not md_files:
        print("No .md files found in the current directory.")
        return

    lines = []
    lines.append("# Markdown Files Summary\n")
    lines.append(f"Generated from: `{os.getcwd()}`\n")
    lines.append(f"Total files found: **{len(md_files)}**\n")
    lines.append("| File | Lines | Words |")
    lines.append("|------|------:|------:|")

    total_lines = 0
    total_words = 0

    for filepath in md_files:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        word_count = len(content.split())
        total_lines += line_count
        total_words += word_count
        lines.append(f"| {filepath} | {line_count} | {word_count} |")

    lines.append(f"| **TOTAL** | **{total_lines}** | **{total_words}** |")

    output_path = "md_summary.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Summary written to {output_path}")
    print(f"  {len(md_files)} files | {total_lines} total lines | {total_words} total words")

if __name__ == "__main__":
    summarize_markdown_files()
