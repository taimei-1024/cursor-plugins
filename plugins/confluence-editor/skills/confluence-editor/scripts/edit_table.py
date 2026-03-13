#!/usr/bin/env python3
"""Table editing tool for Confluence storage HTML.

Usage:
  python edit_table.py remove-column <input_file> <output_file> <table_index> <col_index>
  python edit_table.py add-column <input_file> <output_file> <table_index> <col_index> <header_text>
  python edit_table.py list-tables <input_file>

Indexes are 0-based.
"""

import re
import sys


def find_tables(html):
    """Find all <table>...</table> regions with their positions.

    Returns list of (start, end, table_html) tuples.
    """
    tables = []
    depth = 0
    start = None

    i = 0
    while i < len(html):
        # Look for <table or </table
        if html[i:i+6].lower() == "<table":
            if depth == 0:
                start = i
            depth += 1
            i += 6
        elif html[i:i+8].lower() == "</table>":
            depth -= 1
            if depth == 0 and start is not None:
                end = i + 8
                tables.append((start, end, html[start:end]))
                start = None
            i += 8
        else:
            i += 1

    return tables


def find_cells_in_row(row_html):
    """Find all <th>...</th> and <td>...</td> cells in a row.

    Handles nested tables by tracking depth.
    Returns list of (start, end, cell_html) tuples relative to row_html.
    """
    cells = []
    # Match opening <td or <th tags
    pattern = re.compile(r"<(t[hd])[\s>]", re.IGNORECASE)
    i = 0

    while i < len(row_html):
        m = pattern.search(row_html, i)
        if not m:
            break

        tag_name = m.group(1).lower()
        cell_start = m.start()
        close_tag = f"</{tag_name}>"
        open_pattern = re.compile(rf"<{tag_name}[\s>]", re.IGNORECASE)

        # Find matching close tag with depth tracking
        depth = 1
        pos = m.end()
        while depth > 0 and pos < len(row_html):
            # Find next open or close of same tag
            next_open = open_pattern.search(row_html, pos)
            close_idx = row_html.lower().find(close_tag.lower(), pos)

            if close_idx == -1:
                break

            if next_open and next_open.start() < close_idx:
                depth += 1
                pos = next_open.end()
            else:
                depth -= 1
                if depth == 0:
                    cell_end = close_idx + len(close_tag)
                    cells.append((cell_start, cell_end, row_html[cell_start:cell_end]))
                pos = close_idx + len(close_tag)

        i = pos if pos > i else m.end()

    return cells


def find_rows(table_html):
    """Find all <tr>...</tr> rows in a table.

    Returns list of (start, end, row_html) tuples relative to table_html.
    """
    rows = []
    pattern = re.compile(r"<tr[\s>]", re.IGNORECASE)
    i = 0

    while i < len(table_html):
        m = pattern.search(table_html, i)
        if not m:
            break

        row_start = m.start()
        close_idx = table_html.lower().find("</tr>", m.end())
        if close_idx == -1:
            break

        row_end = close_idx + 5
        rows.append((row_start, row_end, table_html[row_start:row_end]))
        i = row_end

    return rows


def find_col_tags(table_html):
    """Find all <col .../> tags in colgroup.

    Uses <col\\s[^>]*/> to avoid matching <colgroup>.
    Returns list of (start, end, tag) tuples relative to table_html.
    """
    cols = []
    # Match <col followed by whitespace (not <colgroup)
    for m in re.finditer(r"<col\s[^>]*/>", table_html):
        cols.append((m.start(), m.end(), m.group()))
    return cols


def remove_column(html, table_index, col_index):
    """Remove a column from the specified table."""
    tables = find_tables(html)
    if table_index >= len(tables):
        print(f"Error: table_index {table_index} out of range (found {len(tables)} tables)", file=sys.stderr)
        sys.exit(1)

    table_start, table_end, table_html = tables[table_index]

    # Collect all edits as (start, end) pairs to remove, relative to table_html
    edits = []  # list of (start, end) to remove from table_html

    # 1. Remove col tag from colgroup
    col_tags = find_col_tags(table_html)
    if col_index < len(col_tags):
        edits.append((col_tags[col_index][0], col_tags[col_index][1]))

    # 2. Remove cell from each row
    rows = find_rows(table_html)
    for row_start, row_end, row_html in rows:
        cells = find_cells_in_row(row_html)
        if col_index < len(cells):
            cell_start, cell_end, _ = cells[col_index]
            # Convert to table_html coordinates
            abs_start = row_start + cell_start
            abs_end = row_start + cell_end
            edits.append((abs_start, abs_end))

    # Apply edits from back to front to preserve positions
    edits.sort(key=lambda x: x[0], reverse=True)
    new_table = table_html
    for start, end in edits:
        new_table = new_table[:start] + new_table[end:]

    # Replace table in full HTML
    new_html = html[:table_start] + new_table + html[table_end:]
    return new_html


def add_column(html, table_index, col_index, header_text):
    """Add a column to the specified table."""
    tables = find_tables(html)
    if table_index >= len(tables):
        print(f"Error: table_index {table_index} out of range (found {len(tables)} tables)", file=sys.stderr)
        sys.exit(1)

    table_start, table_end, table_html = tables[table_index]

    edits = []  # list of (position, text_to_insert)

    # 1. Add col tag to colgroup
    col_tags = find_col_tags(table_html)
    if col_tags:
        if col_index < len(col_tags):
            insert_pos = col_tags[col_index][0]
        else:
            insert_pos = col_tags[-1][1]
        # Copy style from adjacent col tag
        ref_col = col_tags[min(col_index, len(col_tags) - 1)][2]
        edits.append((insert_pos, ref_col))

    # 2. Add cell to each row
    rows = find_rows(table_html)
    for row_idx, (row_start, row_end, row_html) in enumerate(rows):
        cells = find_cells_in_row(row_html)
        if not cells:
            continue

        # Determine tag type from first cell
        first_cell = cells[0][2] if cells else ""
        is_header_row = first_cell.lower().startswith("<th")

        if is_header_row:
            new_cell = f"<th><p>{header_text}</p></th>"
        else:
            new_cell = "<td><p></p></td>"

        if col_index < len(cells):
            insert_pos = row_start + cells[col_index][0]
        else:
            insert_pos = row_start + cells[-1][1]

        edits.append((insert_pos, new_cell))

    # Apply insertions from back to front
    edits.sort(key=lambda x: x[0], reverse=True)
    new_table = table_html
    for pos, text in edits:
        new_table = new_table[:pos] + text + new_table[pos:]

    new_html = html[:table_start] + new_table + html[table_end:]
    return new_html


def list_tables(html):
    """List tables found in HTML with column headers."""
    tables = find_tables(html)
    for idx, (start, end, table_html) in enumerate(tables):
        rows = find_rows(table_html)
        if rows:
            first_row = rows[0][2]
            cells = find_cells_in_row(first_row)
            headers = []
            for _, _, cell_html in cells:
                # Extract text content
                text = re.sub(r"<[^>]+>", "", cell_html).strip()
                headers.append(text)
            print(f"Table {idx}: {len(rows)} rows, {len(cells)} columns")
            print(f"  Headers: {headers}")
        else:
            print(f"Table {idx}: (empty)")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "list-tables":
        input_file = sys.argv[2]
        with open(input_file, "r", encoding="utf-8") as f:
            html = f.read()
        list_tables(html)

    elif command == "remove-column":
        if len(sys.argv) < 5:
            print("Usage: python edit_table.py remove-column <input_file> <output_file> <table_index> <col_index>")
            sys.exit(1)
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        table_index = int(sys.argv[4])
        col_index = int(sys.argv[5])

        with open(input_file, "r", encoding="utf-8") as f:
            html = f.read()

        result = remove_column(html, table_index, col_index)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Column {col_index} removed from table {table_index}. Output: {output_file}")

    elif command == "add-column":
        if len(sys.argv) < 7:
            print("Usage: python edit_table.py add-column <input_file> <output_file> <table_index> <col_index> <header_text>")
            sys.exit(1)
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        table_index = int(sys.argv[4])
        col_index = int(sys.argv[5])
        header_text = sys.argv[6]

        with open(input_file, "r", encoding="utf-8") as f:
            html = f.read()

        result = add_column(html, table_index, col_index, header_text)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Column added at index {col_index} in table {table_index}. Output: {output_file}")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
