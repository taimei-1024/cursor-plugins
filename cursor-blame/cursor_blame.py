#!/usr/bin/env python3
"""
Cursor Blame - 本地版 Cursor AI 代码归因工具

通过 git commit 反查产生该 commit 的 Cursor 对话。

数据链路:
  git commit hash
    → scored_commits (AI 行数统计)
    → ai_code_hashes (行级归因 + conversationId)
    → state.vscdb composerData (对话元数据)
    → state.vscdb bubbleId (消息内容)
"""

import argparse
import json
import os
import platform
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# --- DB Paths ---

AI_TRACKING_DB = Path.home() / ".cursor" / "ai-tracking" / "ai-code-tracking.db"

if platform.system() == "Darwin":
    STATE_VSCDB = Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
elif platform.system() == "Linux":
    STATE_VSCDB = Path.home() / ".config" / "Cursor" / "User" / "globalStorage" / "state.vscdb"
else:
    # Windows
    STATE_VSCDB = Path(os.environ.get("APPDATA", "")) / "Cursor" / "User" / "globalStorage" / "state.vscdb"


def open_db(path, check=True):
    """Open a SQLite database in read-only mode."""
    if check and not path.exists():
        print(f"Error: Database not found: {path}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def git(*args, cwd=None):
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, cwd=cwd
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def parse_git_date(date_str):
    """Parse git date string to datetime."""
    if not date_str:
        return None
    # Try ISO format first
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%a %b %d %H:%M:%S %Y %z"]:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def ts_to_dt(ts_ms):
    """Convert millisecond timestamp to datetime."""
    if not ts_ms:
        return None
    return datetime.fromtimestamp(ts_ms / 1000)


def format_dt(dt):
    """Format datetime for display."""
    if not dt:
        return "unknown"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# --- Core: commit → conversation lookup ---

def get_scored_commit(tracking_db, commit_hash):
    """Look up a commit in scored_commits table."""
    cur = tracking_db.execute(
        "SELECT * FROM scored_commits WHERE commitHash LIKE ? || '%'",
        (commit_hash,)
    )
    return cur.fetchone()


def get_commit_files_fullpath(commit_hash):
    """Get list of changed files in a commit as full absolute paths."""
    toplevel = git("rev-parse", "--show-toplevel")
    if not toplevel:
        return [], None
    output = git("diff-tree", "--no-commit-id", "-r", "--name-only", commit_hash)
    if not output:
        return [], toplevel
    return [os.path.join(toplevel, f) for f in output.splitlines()], toplevel


def get_commit_timestamp_ms(commit_hash):
    """Get commit timestamp as milliseconds."""
    output = git("log", "-1", "--format=%at", commit_hash)
    if not output:
        return None
    return int(output) * 1000


def _build_file_match_sql(fpath, relpath, repo_name):
    """Build SQL WHERE clauses for matching a file path in ai_code_hashes.

    Match priority: exact path > repo-scoped > deep-suffix (3+ path segments).
    """
    clauses = ["fileName = ?"]
    params = [fpath]

    if repo_name:
        clauses.append("fileName LIKE ?")
        params.append(f"%/{repo_name}/{relpath}")

    if relpath.count("/") >= 2:
        clauses.append("fileName LIKE ?")
        params.append(f"%/{relpath}")

    return clauses, params


def find_conversations_for_commit(tracking_db, commit_hash, scored):
    """Find conversationIds associated with a commit via ai_code_hashes.

    Strategy:
    1. Match commit's changed files in ai_code_hashes (repo-scoped paths)
    2. Start with a tight 24h window; widen to 3d then 7d only if nothing found
    3. Rank results by time proximity to the commit
    """
    full_paths, toplevel = get_commit_files_fullpath(commit_hash)
    commit_ts = get_commit_timestamp_ms(commit_hash)

    if not full_paths:
        return []

    repo_name = os.path.basename(toplevel) if toplevel else None

    # Search with a wide window to collect all candidates
    # Use 30 days to find both primary and related conversations
    conversations, source_summary = _search_conversations_in_window(
        tracking_db, full_paths, toplevel, repo_name, commit_ts, 30 * 24
    )

    if not conversations:
        return [], {}

    conversations.sort(key=lambda c: c["min_time_delta_ms"])

    # Split into primary (high confidence) and related (lower confidence)
    # Primary: within 2h of commit, or within 10x of the closest match
    best_delta = conversations[0]["min_time_delta_ms"]
    threshold = max(best_delta * 10, 2 * 3600 * 1000)  # at least 2h
    for c in conversations:
        c["is_primary"] = c["min_time_delta_ms"] <= threshold

    return conversations, source_summary


def _search_conversations_in_window(tracking_db, full_paths, toplevel, repo_name, commit_ts, window_hours):
    """Search for conversations within a specific time window before the commit."""
    window_ms = window_hours * 3600 * 1000
    ts_start = (commit_ts - window_ms) if commit_ts else 0
    ts_end = commit_ts if commit_ts else 0

    conversations = {}
    source_summary = {}

    for fpath in full_paths:
        if toplevel:
            relpath = os.path.relpath(fpath, toplevel)
        else:
            relpath = os.path.basename(fpath)

        match_clauses, match_params = _build_file_match_sql(fpath, relpath, repo_name)
        where = " OR ".join(match_clauses)

        if ts_end:
            cur = tracking_db.execute(
                f"SELECT hash, source, fileName, conversationId, model, timestamp "
                f"FROM ai_code_hashes WHERE ({where}) "
                f"AND timestamp >= ? AND timestamp <= ?",
                match_params + [ts_start, ts_end]
            )
        else:
            cur = tracking_db.execute(
                f"SELECT hash, source, fileName, conversationId, model, timestamp "
                f"FROM ai_code_hashes WHERE ({where})",
                match_params
            )

        for row in cur:
            src = row["source"]
            source_summary[src] = source_summary.get(src, 0) + 1
            cid = row["conversationId"]
            if cid:
                if cid not in conversations:
                    conversations[cid] = {
                        "conversationId": cid,
                        "sources": {},
                        "files": set(),
                        "models": set(),
                        "matched_hashes": 0,
                        "min_time_delta_ms": float("inf"),
                        "latest_timestamp": 0,
                    }
                info = conversations[cid]
                info["sources"][src] = info["sources"].get(src, 0) + 1
                if row["fileName"]:
                    info["files"].add(row["fileName"])
                if row["model"]:
                    info["models"].add(row["model"])
                info["matched_hashes"] += 1
                ts = row["timestamp"] or 0
                delta = abs(commit_ts - ts) if commit_ts and ts else float("inf")
                if delta < info["min_time_delta_ms"]:
                    info["min_time_delta_ms"] = delta
                if ts > info["latest_timestamp"]:
                    info["latest_timestamp"] = ts

    return list(conversations.values()), source_summary


def get_ai_info_for_file(tracking_db, filepath, toplevel=None):
    """Get all ai_code_hashes entries for a given file path."""
    if toplevel:
        relpath = os.path.relpath(filepath, toplevel)
    else:
        relpath = os.path.basename(filepath)

    repo_name = os.path.basename(toplevel) if toplevel else None

    match_clauses = ["fileName = ?"]
    match_params = [filepath]

    if repo_name:
        match_clauses.append("fileName LIKE ?")
        match_params.append(f"%/{repo_name}/{relpath}")

    if relpath.count("/") >= 2:
        match_clauses.append("fileName LIKE ?")
        match_params.append(f"%/{relpath}")

    where = " OR ".join(match_clauses)
    cur = tracking_db.execute(
        f"SELECT hash, source, conversationId, model, timestamp "
        f"FROM ai_code_hashes WHERE ({where})",
        match_params
    )
    return cur.fetchall()


def build_scored_commits_cache(tracking_db, commit_hashes):
    """Batch-load scored_commits for a set of commit hashes."""
    cache = {}
    for h in commit_hashes:
        cur = tracking_db.execute(
            "SELECT * FROM scored_commits WHERE commitHash LIKE ? || '%'",
            (h,)
        )
        row = cur.fetchone()
        if row:
            cache[h] = row
            cache[row["commitHash"]] = row
    return cache


def classify_commit(scored):
    """Classify a commit's AI attribution. Returns (source_label, ai_pct)."""
    if not scored:
        return "unknown", None
    composer = scored["composerLinesAdded"] or 0
    tab = scored["tabLinesAdded"] or 0
    human = scored["humanLinesAdded"] or 0
    total = composer + tab + human
    pct = scored["v2AiPercentage"]
    if total == 0:
        return "unknown", pct
    if composer > 0 and composer >= tab and composer >= human:
        return "composer", pct
    if tab > 0 and tab >= composer and tab >= human:
        return "tab", pct
    return "human", pct


# --- ANSI colors ---

USE_COLOR = sys.stdout.isatty()

def _c(code, text):
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"

def c_ai(text):     return _c("36", text)    # cyan for AI/composer
def c_tab(text):    return _c("35", text)    # magenta for tab
def c_human(text):  return _c("33", text)    # yellow for human
def c_dim(text):    return _c("2", text)     # dim
def c_bold(text):   return _c("1", text)     # bold


def hyperlink(url, text):
    """Render an OSC 8 terminal hyperlink (clickable in iTerm2, macOS Terminal, etc.)."""
    if not USE_COLOR:
        return text
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


# --- Git remote → web URL ---

_remote_web_url_cache = {}

def get_remote_web_url():
    """Convert git remote origin URL to a web base URL for linking commits."""
    if "result" in _remote_web_url_cache:
        return _remote_web_url_cache["result"]

    remote = git("remote", "get-url", "origin")
    if not remote:
        _remote_web_url_cache["result"] = None
        return None

    # git@host:group/project.git → https://host/group/project
    # https://host/group/project.git → https://host/group/project
    url = remote
    if url.startswith("git@"):
        url = url.replace(":", "/", 1).replace("git@", "https://", 1)
    if url.endswith(".git"):
        url = url[:-4]

    _remote_web_url_cache["result"] = url
    return url


def commit_link(commit_hash, display=None):
    """Render a commit hash as a clickable terminal hyperlink to the web UI."""
    short = display or commit_hash[:10]
    base = get_remote_web_url()
    if not base:
        return short
    # GitLab: /-/commit/HASH, GitHub: /commit/HASH — try GitLab style
    # (GitHub also accepts /-/commit/ via redirect for some setups)
    url = f"{base}/-/commit/{commit_hash}"
    return hyperlink(url, short)


def conversation_link(name):
    """Render a conversation name as a searchable label.
    Since there's no deep-link into Cursor, the name can be searched in
    Cursor's composer panel (Cmd+L → search).
    """
    return c_bold(name)
def c_green(text):  return _c("32", text)
def c_red(text):    return _c("31", text)


def render_bar(composer_pct, tab_pct, human_pct, width=30):
    """Render a simple text bar chart."""
    c = max(1, round(composer_pct / 100 * width)) if composer_pct > 0 else 0
    t = max(1, round(tab_pct / 100 * width)) if tab_pct > 0 else 0
    h = max(1, round(human_pct / 100 * width)) if human_pct > 0 else 0
    # Adjust to fit width
    total = c + t + h
    if total > width and total > 0:
        ratio = width / total
        c, t, h = round(c * ratio), round(t * ratio), round(h * ratio)
    bar = c_ai("█" * c) + c_tab("█" * t) + c_human("█" * h)
    pad = width - c - t - h
    if pad > 0:
        bar += c_dim("░" * pad)
    return bar


def get_conversation_metadata(state_db, conversation_id):
    """Get conversation metadata from state.vscdb."""
    cur = state_db.execute(
        "SELECT value FROM cursorDiskKV WHERE key = ?",
        (f"composerData:{conversation_id}",)
    )
    row = cur.fetchone()
    if not row:
        return None
    try:
        data = json.loads(row["value"])
        return {
            "composerId": data.get("composerId"),
            "name": data.get("name"),
            "createdAt": data.get("createdAt"),
            "modelConfig": data.get("modelConfig", {}),
            "bubbleHeaders": data.get("fullConversationHeadersOnly", []),
        }
    except (json.JSONDecodeError, TypeError):
        return None


def get_bubble_content(state_db, conversation_id, bubble_id):
    """Get a single bubble (message) content."""
    cur = state_db.execute(
        "SELECT value FROM cursorDiskKV WHERE key = ?",
        (f"bubbleId:{conversation_id}:{bubble_id}",)
    )
    row = cur.fetchone()
    if not row:
        return None
    try:
        data = json.loads(row["value"])
        return {
            "type": data.get("type"),  # 1=user, 2=AI
            "text": data.get("text", ""),
            "bubbleId": data.get("bubbleId"),
            "createdAt": data.get("createdAt"),
        }
    except (json.JSONDecodeError, TypeError):
        return None


def get_conversation_messages(state_db, conversation_id, metadata, max_messages=None):
    """Get all messages in a conversation."""
    headers = metadata.get("bubbleHeaders", [])
    if not headers:
        return []

    messages = []
    for h in headers:
        bid = h.get("bubbleId")
        if not bid:
            continue
        bubble = get_bubble_content(state_db, conversation_id, bid)
        if bubble and bubble.get("text"):
            messages.append(bubble)
        if max_messages and len(messages) >= max_messages:
            break
    return messages


# --- Commands ---

def cmd_blame(args):
    """Main blame command: commit → conversation."""
    commit_hash = args.commit
    tracking_db = open_db(AI_TRACKING_DB)
    state_db = open_db(STATE_VSCDB)

    # Step 1: Get scored commit info
    scored = get_scored_commit(tracking_db, commit_hash)

    # Get git commit info
    git_info = git("log", "-1", "--format=%H%n%s%n%ai", commit_hash)
    if not git_info:
        print(f"Error: Commit {commit_hash} not found in git history.")
        sys.exit(1)

    git_lines = git_info.splitlines()
    full_hash = git_lines[0]
    message = git_lines[1] if len(git_lines) > 1 else ""
    date_str = git_lines[2] if len(git_lines) > 2 else ""

    print(f"Commit: {commit_link(full_hash)} ({date_str})")
    print(f"Message: {message}")

    if scored:
        lines_added = scored["linesAdded"] or 0
        composer = scored["composerLinesAdded"] or 0
        tab = scored["tabLinesAdded"] or 0
        human = scored["humanLinesAdded"] or 0
        pct = scored["v2AiPercentage"] or "N/A"
        print(f"AI: {pct}% ({lines_added} lines: composer={composer}, tab={tab}, human={human})")
    else:
        print("AI: No scoring data found for this commit")

    print()

    # Step 2: Find conversations
    result = find_conversations_for_commit(tracking_db, commit_hash, scored)
    if not result:
        print("No AI code hashes matched for this commit.")
        tracking_db.close()
        state_db.close()
        return

    conversations, source_summary = result

    if source_summary:
        parts = [f"{src}={cnt}" for src, cnt in sorted(source_summary.items())]
        print(f"Matched lines by source: {', '.join(parts)}")
        print()

    if not conversations:
        print("No conversations found (lines may be from tab completion without conversationId).")
        tracking_db.close()
        state_db.close()
        return

    # Step 3: Show conversation details
    for conv in conversations:
        cid = conv["conversationId"]
        print(f"{'=' * 60}")
        print(f"Conversation: {cid}")

        sources = ", ".join(f"{k}={v}" for k, v in conv["sources"].items())
        models = ", ".join(conv["models"]) if conv["models"] else "unknown"
        print(f"  Matched hashes: {conv['matched_hashes']} ({sources})")
        print(f"  Model: {models}")

        # Get metadata from state.vscdb
        meta = get_conversation_metadata(state_db, cid)
        if meta:
            name = meta.get("name") or "(unnamed)"
            created = ts_to_dt(meta.get("createdAt"))
            model_config = meta.get("modelConfig", {})
            model_name = model_config.get("modelName", "unknown")
            print(f"  Name: {conversation_link(name)}")
            print(f"  Created: {format_dt(created)}")
            print(f"  Config model: {model_name}")
            print()

            # Show messages
            messages = get_conversation_messages(
                state_db, cid, meta,
                max_messages=args.max_messages if hasattr(args, "max_messages") else 20
            )
            if messages:
                print("  --- Messages ---")
                for msg in messages:
                    role = "User" if msg["type"] == 1 else "AI"
                    icon = "\U0001f464" if msg["type"] == 1 else "\U0001f916"
                    text = msg["text"]
                    if args.short and len(text) > 300:
                        text = text[:300] + "..."
                    # Indent message text
                    indented = "\n    ".join(text.splitlines()[:20])
                    if text.count("\n") > 20:
                        indented += "\n    ... (truncated)"
                    print(f"  {icon} {role}: {indented}")
                    print()
            else:
                print("  (no messages found - bubbles may not be loaded)")
        else:
            print("  (conversation not found in state.vscdb)")

        print()

    tracking_db.close()
    state_db.close()


def cmd_chat(args):
    """View a conversation by ID."""
    cid = args.conversation_id
    state_db = open_db(STATE_VSCDB)

    meta = get_conversation_metadata(state_db, cid)
    if not meta:
        print(f"Conversation {cid} not found in state.vscdb")
        state_db.close()
        sys.exit(1)

    name = meta.get("name") or "(unnamed)"
    created = ts_to_dt(meta.get("createdAt"))
    model_config = meta.get("modelConfig", {})
    print(f"Conversation: {cid}")
    print(f"Name: {name}")
    print(f"Created: {format_dt(created)}")
    print(f"Model: {model_config.get('modelName', 'unknown')}")
    print(f"Messages: {len(meta.get('bubbleHeaders', []))}")
    print()

    messages = get_conversation_messages(state_db, cid, meta)
    for msg in messages:
        role = "User" if msg["type"] == 1 else "AI"
        icon = "\U0001f464" if msg["type"] == 1 else "\U0001f916"
        text = msg["text"]
        if args.short and len(text) > 500:
            text = text[:500] + "..."
        print(f"{icon} {role} [{msg.get('createdAt', '')}]:")
        print(text)
        print()

    state_db.close()


def cmd_log(args):
    """List scored commits with AI attribution."""
    tracking_db = open_db(AI_TRACKING_DB)

    query = "SELECT * FROM scored_commits WHERE 1=1"
    params = []

    if args.since:
        query += " AND commitDate >= ?"
        params.append(args.since)
    if args.until:
        query += " AND commitDate <= ?"
        params.append(args.until)

    # Since commitDate is in git date format, we need a different approach
    # Use scoredAt timestamp for filtering
    if args.since or args.until:
        # Reset and use scoredAt
        query = "SELECT * FROM scored_commits WHERE 1=1"
        params = []
        if args.since:
            try:
                since_dt = datetime.strptime(args.since, "%Y-%m-%d")
                since_ts = int(since_dt.timestamp() * 1000)
                query += " AND scoredAt >= ?"
                params.append(since_ts)
            except ValueError:
                pass
        if args.until:
            try:
                until_dt = datetime.strptime(args.until, "%Y-%m-%d")
                # End of day
                until_ts = int((until_dt.timestamp() + 86400) * 1000)
                query += " AND scoredAt <= ?"
                params.append(until_ts)
            except ValueError:
                pass

    query += " ORDER BY scoredAt DESC"

    if args.limit:
        query += " LIMIT ?"
        params.append(args.limit)

    cur = tracking_db.execute(query, params)
    rows = cur.fetchall()

    if not rows:
        print("No scored commits found.")
        tracking_db.close()
        return

    total_lines = 0
    total_composer = 0
    total_tab = 0
    total_human = 0

    print(f"{'Hash':<12} {'AI%':>6} {'Lines':>6} {'Comp':>5} {'Tab':>4} {'Hum':>4}  Message")
    print("-" * 80)

    for row in rows:
        h = row["commitHash"][:10]
        lines = row["linesAdded"] or 0
        composer = row["composerLinesAdded"] or 0
        tab = row["tabLinesAdded"] or 0
        human = row["humanLinesAdded"] or 0
        pct = row["v2AiPercentage"] or "N/A"
        msg = (row["commitMessage"] or "")[:40]

        total_lines += lines
        total_composer += composer
        total_tab += tab
        total_human += human

        pct_str = f"{pct}%" if pct != "N/A" else "N/A"
        print(f"{h:<12} {pct_str:>6} {lines:>6} {composer:>5} {tab:>4} {human:>4}  {msg}")

    print("-" * 80)
    print(f"{'Total':<12} {'':>6} {total_lines:>6} {total_composer:>5} {total_tab:>4} {total_human:>4}  ({len(rows)} commits)")

    if total_lines > 0:
        ai_lines = total_composer + total_tab
        print(f"\nAI contribution: {ai_lines}/{total_lines} lines ({ai_lines/total_lines*100:.1f}%)")
        print(f"  Composer: {total_composer} ({total_composer/total_lines*100:.1f}%)")
        print(f"  Tab: {total_tab} ({total_tab/total_lines*100:.1f}%)")
        print(f"  Human: {total_human} ({total_human/total_lines*100:.1f}%)")

    tracking_db.close()


def cmd_stats(args):
    """Show overall statistics."""
    tracking_db = open_db(AI_TRACKING_DB)

    # Scored commits stats
    cur = tracking_db.execute("SELECT COUNT(*) as cnt FROM scored_commits")
    total_commits = cur.fetchone()["cnt"]

    cur = tracking_db.execute(
        "SELECT COUNT(*) as cnt FROM scored_commits "
        "WHERE (composerLinesAdded > 0 OR tabLinesAdded > 0)"
    )
    ai_commits = cur.fetchone()["cnt"]

    cur = tracking_db.execute(
        "SELECT SUM(linesAdded) as total, "
        "SUM(composerLinesAdded) as composer, "
        "SUM(tabLinesAdded) as tab, "
        "SUM(humanLinesAdded) as human "
        "FROM scored_commits"
    )
    sums = cur.fetchone()

    cur = tracking_db.execute(
        "SELECT MIN(scoredAt) as earliest, MAX(scoredAt) as latest FROM scored_commits"
    )
    times = cur.fetchone()

    print("=== Cursor Blame Statistics ===")
    print()
    print(f"Scored commits: {total_commits}")
    print(f"  AI-assisted: {ai_commits} ({ai_commits/total_commits*100:.1f}%)" if total_commits else "")
    print(f"  Time range: {format_dt(ts_to_dt(times['earliest']))} ~ {format_dt(ts_to_dt(times['latest']))}")
    print()

    total = sums["total"] or 0
    composer = sums["composer"] or 0
    tab = sums["tab"] or 0
    human = sums["human"] or 0
    ai_total = composer + tab

    print(f"Lines added: {total}")
    if total > 0:
        print(f"  Composer: {composer} ({composer/total*100:.1f}%)")
        print(f"  Tab:      {tab} ({tab/total*100:.1f}%)")
        print(f"  Human:    {human} ({human/total*100:.1f}%)")
        print(f"  AI total: {ai_total} ({ai_total/total*100:.1f}%)")
    print()

    # ai_code_hashes stats
    cur = tracking_db.execute("SELECT COUNT(*) as cnt FROM ai_code_hashes")
    total_hashes = cur.fetchone()["cnt"]

    cur = tracking_db.execute(
        "SELECT source, COUNT(*) as cnt FROM ai_code_hashes GROUP BY source ORDER BY cnt DESC"
    )
    sources = cur.fetchall()

    print(f"AI code hashes: {total_hashes}")
    for s in sources:
        print(f"  {s['source']}: {s['cnt']}")
    print()

    # Conversations
    cur = tracking_db.execute(
        "SELECT COUNT(DISTINCT conversationId) as cnt FROM ai_code_hashes "
        "WHERE conversationId IS NOT NULL"
    )
    conv_count = cur.fetchone()["cnt"]
    print(f"Unique conversations (in tracking): {conv_count}")

    # Top models
    cur = tracking_db.execute(
        "SELECT model, COUNT(*) as cnt FROM ai_code_hashes "
        "WHERE model IS NOT NULL GROUP BY model ORDER BY cnt DESC LIMIT 5"
    )
    models = cur.fetchall()
    if models:
        print()
        print("Top models:")
        for m in models:
            print(f"  {m['model']}: {m['cnt']} hashes")

    tracking_db.close()


def parse_git_blame_porcelain(output):
    """Parse `git blame --porcelain` output into structured data."""
    lines = output.splitlines()
    result = []
    i = 0
    commit_info = {}  # cache commit metadata

    while i < len(lines):
        line = lines[i]
        parts = line.split()
        if not parts:
            i += 1
            continue

        # Header line: <hash> <orig_lineno> <final_lineno> [<num_lines>]
        if len(parts) >= 3 and len(parts[0]) == 40:
            commit_hash = parts[0]
            final_lineno = int(parts[2])

            if commit_hash not in commit_info:
                commit_info[commit_hash] = {}

            # Read metadata lines until we hit the content line (starts with \t)
            i += 1
            while i < len(lines) and not lines[i].startswith("\t"):
                meta_line = lines[i]
                if meta_line.startswith("author "):
                    commit_info[commit_hash]["author"] = meta_line[7:]
                elif meta_line.startswith("author-time "):
                    commit_info[commit_hash]["author_time"] = int(meta_line[12:])
                elif meta_line.startswith("summary "):
                    commit_info[commit_hash]["summary"] = meta_line[8:]
                elif meta_line.startswith("filename "):
                    commit_info[commit_hash]["filename"] = meta_line[9:]
                i += 1

            # Content line (starts with \t)
            content = lines[i][1:] if i < len(lines) else ""
            result.append({
                "lineno": final_lineno,
                "commit": commit_hash,
                "content": content,
                "author": commit_info[commit_hash].get("author", ""),
                "author_time": commit_info[commit_hash].get("author_time", 0),
                "summary": commit_info[commit_hash].get("summary", ""),
            })
            i += 1
        else:
            i += 1

    return result


def cmd_file(args):
    """AI-enriched git blame for a file: line-level AI attribution."""
    filepath = args.file
    tracking_db = open_db(AI_TRACKING_DB)

    # Resolve to absolute path
    if not os.path.isabs(filepath):
        filepath = os.path.abspath(filepath)

    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    toplevel = git("rev-parse", "--show-toplevel")
    if not toplevel:
        print("Error: Not inside a git repository.", file=sys.stderr)
        sys.exit(1)

    relpath = os.path.relpath(filepath, toplevel)

    # Run git blame --porcelain
    blame_args = ["blame", "--porcelain", relpath]
    if args.lines:
        blame_args.extend(["-L", args.lines])
    blame_output = git(*blame_args)
    if not blame_output:
        print(f"Error: git blame failed for {relpath}", file=sys.stderr)
        sys.exit(1)

    blame_data = parse_git_blame_porcelain(blame_output)

    # Collect unique commit hashes and look up scoring
    unique_commits = set(b["commit"] for b in blame_data)
    scored_cache = build_scored_commits_cache(tracking_db, unique_commits)

    # Get AI code hashes for this file
    ai_entries = get_ai_info_for_file(tracking_db, filepath, toplevel)
    # Build a set of conversationIds and models for this file
    file_conversations = {}
    file_models = set()
    for entry in ai_entries:
        if entry["conversationId"]:
            cid = entry["conversationId"]
            if cid not in file_conversations:
                file_conversations[cid] = {"source": set(), "model": set(), "count": 0}
            file_conversations[cid]["source"].add(entry["source"])
            if entry["model"]:
                file_conversations[cid]["model"].add(entry["model"])
                file_models.add(entry["model"])
            file_conversations[cid]["count"] += 1

    # Classify each line
    total_lines = len(blame_data)
    ai_lines = 0
    tab_lines = 0
    human_lines = 0
    unknown_lines = 0
    commit_sources = {}  # commit_hash -> (source_label, ai_pct)

    for b in blame_data:
        ch = b["commit"]
        if ch not in commit_sources:
            scored = scored_cache.get(ch)
            commit_sources[ch] = classify_commit(scored)
        src, pct = commit_sources[ch]
        if src == "composer":
            ai_lines += 1
        elif src == "tab":
            tab_lines += 1
        elif src == "human":
            human_lines += 1
        else:
            unknown_lines += 1

    # --- Output ---

    # Header
    print(c_bold(f"File: {relpath}"))
    print(f"Lines: {total_lines}")
    print()

    # Contribution breakdown
    scored_total = ai_lines + tab_lines + human_lines
    if scored_total > 0:
        c_pct = ai_lines / scored_total * 100
        t_pct = tab_lines / scored_total * 100
        h_pct = human_lines / scored_total * 100
    else:
        c_pct = t_pct = h_pct = 0

    print(c_bold("Contribution Breakdown"))
    bar = render_bar(c_pct, t_pct, h_pct)
    print(f"  {bar}")
    legend = []
    if ai_lines:
        legend.append(c_ai(f"Composer: {ai_lines} ({c_pct:.0f}%)"))
    if tab_lines:
        legend.append(c_tab(f"Tab: {tab_lines} ({t_pct:.0f}%)"))
    if human_lines or unknown_lines:
        h_count = human_lines + unknown_lines
        h_pct_display = h_count / total_lines * 100 if total_lines else 0
        legend.append(c_human(f"Human: {h_count} ({h_pct_display:.0f}%)"))
    print(f"  {' | '.join(legend)}")

    # Model tracking
    if file_models:
        print()
        print(c_bold("Models Used"))
        for m in sorted(file_models):
            print(f"  - {m}")

    # --- AI Commit History for this file ---
    # Collect unique commits that touched this file, with their scoring and conversations
    ai_commit_hashes = set()
    for ch, (src, pct) in commit_sources.items():
        if src in ("composer", "tab"):
            ai_commit_hashes.add(ch)

    if ai_commit_hashes:
        state_db = open_db(STATE_VSCDB)
        print()
        print(c_bold("AI Commit History"))
        print(c_dim(f"  {'Hash':<12} {'AI%':>6} {'Source':<10} {'Date':<20} Message"))
        print(c_dim(f"  {'-'*75}"))

        # Get commit details from git
        commit_details = []
        for ch in ai_commit_hashes:
            info = git("log", "-1", "--format=%H|%ai|%s", ch)
            if info:
                parts = info.split("|", 2)
                full_h = parts[0]
                date = parts[1] if len(parts) > 1 else ""
                msg = parts[2] if len(parts) > 2 else ""
                src, pct = commit_sources[ch]
                commit_details.append((full_h, date, msg, src, pct))

        # Sort by date
        commit_details.sort(key=lambda x: x[1], reverse=True)

        for full_h, date, msg, src, pct in commit_details:
            linked_h = commit_link(full_h)
            pct_str = f"{pct}%" if pct is not None else "-"
            date_short = date[:19] if date else ""
            msg_short = msg[:35] + "..." if len(msg) > 35 else msg
            if src == "composer":
                print(f"  {linked_h:<12} {c_ai(f'{pct_str:>6}')} {c_ai(f'{src:<10}')} {date_short:<20} {msg_short}")
            else:
                print(f"  {linked_h:<12} {c_tab(f'{pct_str:>6}')} {c_tab(f'{src:<10}')} {date_short:<20} {msg_short}")

        # For each AI commit, find its conversation
        print()
        print(c_bold("Conversations"))
        seen_cids = set()
        for full_h, date, msg, src, pct in commit_details:
            result = find_conversations_for_commit(tracking_db, full_h, scored_cache.get(full_h))
            if result:
                conversations_list, _ = result
                for conv in conversations_list:
                    if not conv.get("is_primary"):
                        continue
                    cid = conv["conversationId"]
                    if cid in seen_cids:
                        continue
                    seen_cids.add(cid)

                    meta = get_conversation_metadata(state_db, cid)
                    if meta:
                        name = meta.get("name") or "(unnamed)"
                        models_str = ", ".join(conv["models"]) if conv["models"] else "unknown"
                        proximity = _format_proximity(conv.get("min_time_delta_ms", 0))

                        print(f"  {conversation_link(name)}")
                        print(f"    ID: {cid}")
                        print(f"    Commit: {commit_link(full_h)} | Model: {models_str} | {c_dim(proximity)}")

                        msgs = get_conversation_messages(state_db, cid, meta, max_messages=3)
                        user_msgs = [m for m in msgs if m.get("type") == 1]
                        if user_msgs:
                            summary = user_msgs[0]["text"].replace("\n", " ")
                            if len(summary) > 120:
                                summary = summary[:120] + "..."
                            print(f"    User: {c_dim(summary)}")
                        print()

        state_db.close()
    elif file_conversations:
        # Fallback: show conversations from ai_code_hashes even if no scored commits
        state_db = open_db(STATE_VSCDB)
        print()
        print(c_bold("Related Conversations"))
        for cid, info in file_conversations.items():
            meta = get_conversation_metadata(state_db, cid)
            name = "(unnamed)"
            if meta:
                name = meta.get("name") or "(unnamed)"
            sources = ", ".join(sorted(info["source"]))
            models = ", ".join(sorted(info["model"])) if info["model"] else "unknown"
            print(f"  [{sources}] {name}")
            print(f"    ID: {cid}")
            print(f"    Model: {models} | Tracked lines: {info['count']}")
            if meta:
                msgs = get_conversation_messages(state_db, cid, meta, max_messages=3)
                user_msgs = [m for m in msgs if m.get("type") == 1]
                if user_msgs:
                    summary = user_msgs[0]["text"].replace("\n", " ")
                    if len(summary) > 120:
                        summary = summary[:120] + "..."
                    print(f"    Summary: {c_dim(summary)}")
        state_db.close()

    # Line-by-line blame (unless --no-lines)
    if not args.no_lines:
        print()
        print(c_bold("Line Attribution"))
        print(c_dim(f"{'Line':>5}  {'Source':>8}  {'AI%':>5}  {'Commit':>10}  {'Author':<16}  Content"))
        print(c_dim("-" * 90))

        for b in blame_data:
            ch = b["commit"]
            src, pct = commit_sources[ch]
            lineno = b["lineno"]
            author = b["author"][:16]
            content = b["content"]
            if len(content) > 60:
                content = content[:60] + "..."

            pct_str = f"{pct}%" if pct is not None else "  -"

            if src == "composer":
                src_colored = c_ai("composer")
                pct_colored = c_ai(f"{pct_str:>5}")
            elif src == "tab":
                src_colored = c_tab("     tab")
                pct_colored = c_tab(f"{pct_str:>5}")
            elif src == "human":
                src_colored = c_human("   human")
                pct_colored = c_human(f"{pct_str:>5}")
            else:
                src_colored = c_dim(" unknown")
                pct_colored = c_dim(f"{'  -':>5}")

            print(f"{lineno:>5}  {src_colored}  {pct_colored}  {commit_link(ch)}  {author:<16}  {content}")

    tracking_db.close()


def _format_proximity(delta_ms):
    """Format a time delta in ms into a human-readable proximity string."""
    if delta_ms < 3600000:
        return f"{delta_ms/60000:.0f}min before commit"
    elif delta_ms < 86400000:
        return f"{delta_ms/3600000:.1f}h before commit"
    else:
        return f"{delta_ms/86400000:.1f}d before commit"


def _print_conversations(conversations, state_db, args, compact=False):
    """Print a list of conversations with metadata and optional messages."""
    for conv in conversations:
        cid = conv["conversationId"]
        meta = get_conversation_metadata(state_db, cid)
        if meta:
            name = meta.get("name") or "(unnamed)"
            created = ts_to_dt(meta.get("createdAt"))
            model_config = meta.get("modelConfig", {})
            model_name = model_config.get("modelName", "unknown")
            models_str = ", ".join(conv["models"]) if conv["models"] else model_name
            proximity = _format_proximity(conv.get("min_time_delta_ms", 0))

            if compact:
                print(f"  {c_dim(name)}")
                print(f"    {c_dim(f'ID: {cid} | {proximity}')}")
            else:
                print(f"  {conversation_link(name)}")
                print(f"    ID: {cid}")
                print(f"    Created: {format_dt(created)} | Model: {models_str} | {c_dim(proximity)}")

            # Show first user message as summary
            msgs = get_conversation_messages(state_db, cid, meta, max_messages=6)
            user_msgs = [m for m in msgs if m.get("type") == 1]
            if user_msgs:
                summary = user_msgs[0]["text"].replace("\n", " ")
                max_len = 100 if compact else 150
                if len(summary) > max_len:
                    summary = summary[:max_len] + "..."
                print(f"    User: {c_dim(summary)}")

            if not compact and hasattr(args, "verbose") and args.verbose:
                print()
                for msg in msgs[:10]:
                    role = "User" if msg["type"] == 1 else "AI"
                    icon = "\U0001f464" if msg["type"] == 1 else "\U0001f916"
                    text = msg["text"]
                    if len(text) > 300:
                        text = text[:300] + "..."
                    indented = "\n      ".join(text.splitlines()[:10])
                    print(f"    {icon} {role}: {indented}")
                    print()
        else:
            print(f"  {c_dim(cid)} (not found in state.vscdb)")
        print()


def cmd_commit(args):
    """Enhanced commit view with per-file breakdown and conversation context."""
    commit_hash = args.commit
    tracking_db = open_db(AI_TRACKING_DB)
    state_db = open_db(STATE_VSCDB)

    # Get git commit info
    git_info = git("log", "-1", "--format=%H%n%s%n%ai%n%an%n%P", commit_hash)
    if not git_info:
        print(f"Error: Commit {commit_hash} not found in git history.")
        sys.exit(1)

    git_lines = git_info.splitlines()
    full_hash = git_lines[0]
    message = git_lines[1] if len(git_lines) > 1 else ""
    date_str = git_lines[2] if len(git_lines) > 2 else ""
    author = git_lines[3] if len(git_lines) > 3 else ""
    parents = git_lines[4].split() if len(git_lines) > 4 else []

    is_merge = len(parents) > 1

    # For merge commits, find and analyze the merged commits
    if is_merge:
        merge_children_output = git("log", "--oneline", f"{parents[0]}..{parents[1]}", "--no-merges")
        child_hashes = []
        if merge_children_output:
            for line in merge_children_output.splitlines():
                child_hashes.append(line.split()[0])

        print(c_bold(f"Merge Commit {commit_link(full_hash)}") + f" ({date_str})")
        print(f"Author: {author}")
        print(f"Message: {message}")
        if child_hashes:
            print(f"Contains: {len(child_hashes)} commit(s)")
        print()

        # Analyze each child commit
        for child_hash in child_hashes:
            print(c_dim("=" * 60))
            # Recursively show commit info
            child_args = argparse.Namespace(commit=child_hash, verbose=args.verbose)
            cmd_commit(child_args)

        if not child_hashes:
            print(c_dim("No child commits found in merge."))

        tracking_db.close()
        state_db.close()
        return

    # Get scored commit
    scored = get_scored_commit(tracking_db, commit_hash)

    # --- Header ---
    print(c_bold(f"Commit {commit_link(full_hash)}") + f" ({date_str})")
    print(f"Author: {author}")
    print(f"Message: {message}")
    print()

    # --- Contribution Breakdown ---
    if scored:
        lines_added = scored["linesAdded"] or 0
        lines_deleted = scored["linesDeleted"] or 0
        composer = scored["composerLinesAdded"] or 0
        composer_del = scored["composerLinesDeleted"] or 0
        tab = scored["tabLinesAdded"] or 0
        tab_del = scored["tabLinesDeleted"] or 0
        human = scored["humanLinesAdded"] or 0
        human_del = scored["humanLinesDeleted"] or 0
        pct = scored["v2AiPercentage"] or "0"

        print(c_bold("Contribution Breakdown"))
        total_scored = composer + tab + human
        if total_scored > 0:
            c_pct = composer / total_scored * 100
            t_pct = tab / total_scored * 100
            h_pct = human / total_scored * 100
        else:
            c_pct = t_pct = h_pct = 0

        bar = render_bar(c_pct, t_pct, h_pct)
        print(f"  {bar}  AI: {pct}%")
        print()

        rows = []
        if composer:
            rows.append(("Composer (Agent)", f"+{composer}", f"-{composer_del}", f"{c_pct:.0f}%"))
        if tab:
            rows.append(("Tab (Autocomplete)", f"+{tab}", f"-{tab_del}", f"{t_pct:.0f}%"))
        if human:
            rows.append(("Human", f"+{human}", f"-{human_del}", f"{h_pct:.0f}%"))

        if rows:
            print(f"  {'Contributor':<22} {'Added':>8} {'Deleted':>8} {'Share':>8}")
            print(f"  {'-'*50}")
            for name, added, deleted, share in rows:
                if "Composer" in name:
                    print(f"  {c_ai(f'{name:<22}')} {c_green(f'{added:>8}')} {c_red(f'{deleted:>8}')} {share:>8}")
                elif "Tab" in name:
                    print(f"  {c_tab(f'{name:<22}')} {c_green(f'{added:>8}')} {c_red(f'{deleted:>8}')} {share:>8}")
                else:
                    print(f"  {c_human(f'{name:<22}')} {c_green(f'{added:>8}')} {c_red(f'{deleted:>8}')} {share:>8}")
            print(f"  {'-'*50}")
            added_str = f"+{lines_added}"
            deleted_str = f"-{lines_deleted}"
            print(f"  {'Total':<22} {c_green(f'{added_str:>8}')} {c_red(f'{deleted_str:>8}')}")
    else:
        print(c_dim("No AI scoring data found for this commit."))

    # --- Per-file breakdown ---
    full_paths, toplevel = get_commit_files_fullpath(commit_hash)
    if full_paths:
        print()
        print(c_bold("Changed Files"))

        for fpath in full_paths:
            relpath = os.path.relpath(fpath, toplevel) if toplevel else fpath
            ai_entries = get_ai_info_for_file(tracking_db, fpath, toplevel)

            sources = {}
            models = set()
            for e in ai_entries:
                s = e["source"]
                sources[s] = sources.get(s, 0) + 1
                if e["model"]:
                    models.add(e["model"])

            if sources:
                src_str = ", ".join(f"{k}:{v}" for k, v in sorted(sources.items()))
                model_str = ", ".join(sorted(models)) if models else ""
                tag = c_ai("[AI]") if "composer" in sources else (c_tab("[TAB]") if "tab" in sources else c_human("[HUM]"))
                print(f"  {tag} {relpath}")
                print(f"       {c_dim(f'{src_str}')}{c_dim(f' | {model_str}') if model_str else ''}")
            else:
                print(f"  {c_dim('[---]')} {relpath}")

    # --- Conversation Context ---
    result = find_conversations_for_commit(tracking_db, commit_hash, scored)
    if result:
        conversations, source_summary = result
        primary = [c for c in conversations if c.get("is_primary")]
        related = [c for c in conversations if not c.get("is_primary")]

        if primary:
            print()
            print(c_bold("Conversation Context"))
            _print_conversations(primary, state_db, args)

        if related:
            print()
            print(c_bold("Related Conversations") + c_dim(" (same files, earlier edits)"))
            _print_conversations(related, state_db, args, compact=True)

    tracking_db.close()
    state_db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Cursor Blame - trace git commits back to Cursor AI conversations"
    )
    subparsers = parser.add_subparsers(dest="command")

    # commit (enhanced blame with breakdown)
    commit_parser = subparsers.add_parser("commit", help="AI attribution for a commit with contribution breakdown")
    commit_parser.add_argument("commit", help="Git commit hash")
    commit_parser.add_argument("--verbose", "-v", action="store_true", help="Show full conversation messages")

    # file (line-level AI blame)
    file_parser = subparsers.add_parser("file", help="Line-level AI attribution for a file")
    file_parser.add_argument("file", help="File path")
    file_parser.add_argument("--lines", "-L", help="Line range (e.g., 1,20 or 10,+5)")
    file_parser.add_argument("--no-lines", action="store_true", help="Hide per-line output, show only summary")

    # blame (original: commit → conversation lookup)
    blame_parser = subparsers.add_parser("blame", help="Trace a commit to its Cursor conversation (messages)")
    blame_parser.add_argument("commit", help="Git commit hash")
    blame_parser.add_argument("--short", "-s", action="store_true", help="Truncate long messages")
    blame_parser.add_argument("--max-messages", "-n", type=int, default=20, help="Max messages to show")

    # log
    log_parser = subparsers.add_parser("log", help="List scored commits")
    log_parser.add_argument("--since", help="Start date (YYYY-MM-DD)")
    log_parser.add_argument("--until", help="End date (YYYY-MM-DD)")
    log_parser.add_argument("--limit", "-n", type=int, default=50, help="Max commits to show")

    # chat
    chat_parser = subparsers.add_parser("chat", help="View a conversation by ID")
    chat_parser.add_argument("conversation_id", help="Conversation/Composer ID")
    chat_parser.add_argument("--short", "-s", action="store_true", help="Truncate long messages")

    # stats
    subparsers.add_parser("stats", help="Show overall statistics")

    args = parser.parse_args()

    # If no subcommand but args look like a commit hash, treat as commit
    if not args.command:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            candidate = sys.argv[1]
            # Check if it looks like a file path
            if os.path.exists(candidate):
                args.command = "file"
                args.file = candidate
                args.lines = None
                args.no_lines = False
            else:
                args.command = "commit"
                args.commit = candidate
                args.verbose = "-v" in sys.argv or "--verbose" in sys.argv
        else:
            parser.print_help()
            sys.exit(1)

    if args.command == "commit":
        cmd_commit(args)
    elif args.command == "file":
        cmd_file(args)
    elif args.command == "blame":
        cmd_blame(args)
    elif args.command == "log":
        cmd_log(args)
    elif args.command == "chat":
        cmd_chat(args)
    elif args.command == "stats":
        cmd_stats(args)


if __name__ == "__main__":
    main()
