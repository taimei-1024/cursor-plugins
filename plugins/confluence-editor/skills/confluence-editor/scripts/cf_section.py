#!/usr/bin/env python3
"""Section/fragment editing tool for Confluence storage HTML.

Usage:
  python cf_section.py list    <input_file>
  python cf_section.py extract <input_file> <section_index>
  python cf_section.py replace <input_file> <output_file> <section_index> <replacement_file>
  python cf_section.py search  <input_file> <keyword>
  python cf_section.py locate  <input_file> <quoted_text>

Sections are split by h1-h4 heading tags (flat mode).
Content before the first heading is section 0.
"""

import json
import os
import re
import sys


def _find_excluded_ranges(html):
    """Find ranges inside <ac:plain-text-body> and <pre> tags to exclude."""
    ranges = []
    for pattern in [
        r"<ac:plain-text-body>[\s\S]*?</ac:plain-text-body>",
        r"<pre[\s>][\s\S]*?</pre>",
    ]:
        for m in re.finditer(pattern, html, re.IGNORECASE):
            ranges.append((m.start(), m.end()))
    return ranges


def _in_excluded(pos, excluded_ranges):
    """Check if a position falls within any excluded range."""
    for start, end in excluded_ranges:
        if start <= pos < end:
            return True
    return False


def _strip_html_tags(html):
    """Strip HTML tags and return plain text."""
    return re.sub(r"<[^>]+>", "", html)


def parse_sections(html):
    """Parse HTML into sections based on h1-h4 headings.

    Returns list of dicts: {index, level, heading_text, start, end}
    """
    excluded = _find_excluded_ranges(html)
    heading_pattern = re.compile(r"<h([1-4])(\s[^>]*)?>(.+?)</h\1>", re.IGNORECASE | re.DOTALL)

    headings = []
    for m in heading_pattern.finditer(html):
        if not _in_excluded(m.start(), excluded):
            level = int(m.group(1))
            raw_heading = m.group(3)
            heading_text = _strip_html_tags(raw_heading).strip()
            headings.append({
                "level": level,
                "heading_text": heading_text,
                "pos": m.start(),
            })

    sections = []

    if not headings:
        # No headings: entire page is section 0
        sections.append({
            "index": 0,
            "level": 0,
            "heading_text": "(entire page)",
            "start": 0,
            "end": len(html),
        })
        return sections

    # Section 0: content before first heading
    if headings[0]["pos"] > 0:
        sections.append({
            "index": 0,
            "level": 0,
            "heading_text": "(preamble)",
            "start": 0,
            "end": headings[0]["pos"],
        })

    for i, h in enumerate(headings):
        next_start = headings[i + 1]["pos"] if i + 1 < len(headings) else len(html)
        sections.append({
            "index": len(sections),
            "level": h["level"],
            "heading_text": h["heading_text"],
            "start": h["pos"],
            "end": next_start,
        })

    return sections


def _content_preview(html, max_len=40):
    """Get a short text preview of HTML content."""
    text = _strip_html_tags(html).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text if text else "(empty)"


def cmd_list(html):
    """List all sections with index, level, heading, length, and preview."""
    sections = parse_sections(html)
    for s in sections:
        content = html[s["start"]:s["end"]]
        length = len(content)
        preview = _content_preview(content)
        level_str = f"h{s['level']}" if s["level"] > 0 else "  "
        print(f"[{s['index']}] {level_str}: {s['heading_text']} | {length} chars | {preview}")


def cmd_extract(html, section_index, input_file):
    """Extract a section to a temp file."""
    sections = parse_sections(html)
    if section_index < 0 or section_index >= len(sections):
        print(f"Error: section_index {section_index} out of range (found {len(sections)} sections)", file=sys.stderr)
        sys.exit(1)

    s = sections[section_index]
    content = html[s["start"]:s["end"]]

    # Derive pageId from input filename if possible
    base = os.path.basename(input_file)
    m = re.search(r"cf_page_(\d+)", base)
    page_id = m.group(1) if m else "unknown"

    out_file = f"/tmp/cf_section_{page_id}_{section_index}.html"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)

    output = {
        "section_index": section_index,
        "heading": s["heading_text"],
        "level": s["level"],
        "file": out_file,
        "length": len(content),
        "start": s["start"],
        "end": s["end"],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_replace(html, section_index, replacement_file, output_file):
    """Replace a section's content with new content."""
    sections = parse_sections(html)
    if section_index < 0 or section_index >= len(sections):
        print(f"Error: section_index {section_index} out of range (found {len(sections)} sections)", file=sys.stderr)
        sys.exit(1)

    s = sections[section_index]
    with open(replacement_file, "r", encoding="utf-8") as f:
        new_content = f.read()

    result = html[:s["start"]] + new_content + html[s["end"]:]

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"Section {section_index} replaced. Output: {output_file}")
    print(f"  Original length: {s['end'] - s['start']}, New length: {len(new_content)}")


def cmd_search(html, keyword):
    """Search sections by keyword."""
    sections = parse_sections(html)
    keyword_lower = keyword.lower()
    matches = []

    for s in sections:
        content = html[s["start"]:s["end"]]
        text = _strip_html_tags(content).lower()
        if keyword_lower in text or keyword_lower in s["heading_text"].lower():
            preview = _content_preview(content)
            level_str = f"h{s['level']}" if s["level"] > 0 else "  "
            matches.append(s["index"])
            print(f"[{s['index']}] {level_str}: {s['heading_text']} | {preview}")

    if not matches:
        print(f"No sections found matching '{keyword}'")


def _build_text_to_html_map(html):
    """Build a mapping from plain text positions to HTML positions.

    Returns (plain_text, mapping) where mapping[text_pos] = html_pos.
    """
    mapping = []  # mapping[i] = html position for plain_text[i]
    plain_chars = []
    i = 0
    while i < len(html):
        if html[i] == "<":
            # Skip entire tag
            end = html.find(">", i)
            if end == -1:
                break
            i = end + 1
        else:
            mapping.append(i)
            plain_chars.append(html[i])
            i += 1

    return "".join(plain_chars), mapping


def _normalize_whitespace(text):
    """Normalize whitespace for fuzzy matching."""
    return re.sub(r"\s+", " ", text).strip()


def cmd_locate(html, quoted_text):
    """Locate quoted text in HTML, returning position info."""
    plain_text, mapping = _build_text_to_html_map(html)

    norm_quote = _normalize_whitespace(quoted_text)
    norm_plain = _normalize_whitespace(plain_text)

    # Try exact match in normalized space first
    matches = []

    # Build normalized-to-plain position map
    norm_chars = []
    norm_to_plain = []
    for i, ch in enumerate(plain_text):
        if ch in " \t\n\r":
            if norm_chars and norm_chars[-1] != " ":
                norm_chars.append(" ")
                norm_to_plain.append(i)
        else:
            norm_chars.append(ch)
            norm_to_plain.append(i)

    # Strip leading/trailing space from built norm
    norm_built = "".join(norm_chars).strip()
    # Adjust norm_to_plain for stripped leading spaces
    strip_offset = len("".join(norm_chars)) - len("".join(norm_chars).lstrip())
    if strip_offset > 0:
        norm_to_plain = norm_to_plain[strip_offset:]

    # Search in normalized text
    search_start = 0
    while True:
        idx = norm_built.find(norm_quote, search_start)
        if idx == -1:
            break

        # Map back to plain text positions
        plain_start = norm_to_plain[idx] if idx < len(norm_to_plain) else 0
        end_idx = idx + len(norm_quote) - 1
        plain_end = norm_to_plain[end_idx] + 1 if end_idx < len(norm_to_plain) else len(plain_text)

        # Map to HTML positions
        html_start = mapping[plain_start] if plain_start < len(mapping) else 0
        # For html_end, find the position after the last matched char
        if plain_end - 1 < len(mapping):
            # Scan forward from the last char's HTML position to include the full char
            last_html_pos = mapping[plain_end - 1]
            # Move past this character (could be multi-byte but in HTML context it's single)
            html_end = last_html_pos + 1
            # Extend to include any trailing tags that are part of the content
            # Find the nearest tag boundary after html_end
        else:
            html_end = len(html)

        # Expand html_end to include closing tags right after the last text char
        while html_end < len(html) and html[html_end] == "<":
            tag_end = html.find(">", html_end)
            if tag_end == -1:
                break
            tag_content = html[html_end:tag_end + 1]
            # Only include closing tags
            if tag_content.startswith("</"):
                html_end = tag_end + 1
            else:
                break

        # Determine which section this belongs to
        sections = parse_sections(html)
        section_index = 0
        section_heading = ""
        for s in sections:
            if s["start"] <= html_start < s["end"]:
                section_index = s["index"]
                section_heading = s["heading_text"]
                break

        # Context
        ctx_len = 50
        context_before = _strip_html_tags(html[max(0, html_start - 200):html_start])[-ctx_len:]
        context_after = _strip_html_tags(html[html_end:html_end + 200])[:ctx_len]

        matches.append({
            "match_index": len(matches),
            "section_index": section_index,
            "section_heading": section_heading,
            "html_start": html_start,
            "html_end": html_end,
            "html_fragment": html[html_start:html_end][:200],
            "context_before": context_before,
            "context_after": context_after,
        })

        search_start = idx + 1

    if not matches:
        print(json.dumps({"error": "Quoted text not found", "quoted_text": quoted_text}, ensure_ascii=False, indent=2))
        sys.exit(1)

    print(json.dumps({"matches": matches, "total": len(matches)}, ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    input_file = sys.argv[2]

    with open(input_file, "r", encoding="utf-8") as f:
        html = f.read()

    if command == "list":
        cmd_list(html)

    elif command == "extract":
        if len(sys.argv) < 4:
            print("Usage: python cf_section.py extract <input_file> <section_index>", file=sys.stderr)
            sys.exit(1)
        section_index = int(sys.argv[3])
        cmd_extract(html, section_index, input_file)

    elif command == "replace":
        if len(sys.argv) < 6:
            print("Usage: python cf_section.py replace <input_file> <output_file> <section_index> <replacement_file>", file=sys.stderr)
            sys.exit(1)
        output_file = sys.argv[3]
        section_index = int(sys.argv[4])
        replacement_file = sys.argv[5]
        cmd_replace(html, section_index, replacement_file, output_file)

    elif command == "search":
        if len(sys.argv) < 4:
            print("Usage: python cf_section.py search <input_file> <keyword>", file=sys.stderr)
            sys.exit(1)
        keyword = sys.argv[3]
        cmd_search(html, keyword)

    elif command == "locate":
        if len(sys.argv) < 4:
            print("Usage: python cf_section.py locate <input_file> <quoted_text>", file=sys.stderr)
            sys.exit(1)
        quoted_text = sys.argv[3]
        cmd_locate(html, quoted_text)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
