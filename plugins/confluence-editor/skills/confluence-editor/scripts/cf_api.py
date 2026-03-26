#!/usr/bin/env python3
"""Confluence REST API wrapper for getting and updating pages.

Usage:
  python cf_api.py get <page_id>
  python cf_api.py update <page_id> <title> <content_file> <version> [message]

Credentials are auto-discovered from the running mcp-atlassian process environment,
or can be set via CONFLUENCE_URL and CONFLUENCE_PERSONAL_TOKEN env vars.
"""

import json
import os
import re
import ssl
import subprocess
import sys
import urllib.request
import urllib.error


def get_credentials():
    """Get Confluence credentials from env vars or mcp-atlassian process."""
    url = os.environ.get("CONFLUENCE_URL")
    token = os.environ.get("CONFLUENCE_PERSONAL_TOKEN")

    if url and token:
        return url, token

    # Try to read from mcp-atlassian process command line args
    try:
        ps_output = subprocess.check_output(
            ["ps", "aux"], text=True, stderr=subprocess.DEVNULL
        )
        # First pass: prefer processes with --confluence-url in command line
        # (some processes may be wrapper/child processes without args)
        best_line = None
        fallback_line = None
        for line in ps_output.splitlines():
            if "mcp-atlassian" not in line:
                continue
            if "--confluence-url" in line or "--confluence-personal-token" in line:
                best_line = line
                break
            elif fallback_line is None:
                fallback_line = line

        chosen_line = best_line or fallback_line

        if chosen_line:
            # Try to extract credentials directly from command line args
            url_match = re.search(r"--confluence-url[= ](\S+)", chosen_line)
            token_match = re.search(r"--confluence-personal-token[= ](\S+)", chosen_line)
            if url_match:
                url = url_match.group(1)
            if token_match:
                token = token_match.group(1)

            # Fallback to ps -E if command line parsing didn't work
            if not (url and token):
                pid = chosen_line.split()[1]
                env_output = subprocess.check_output(
                    ["ps", "-E", "-p", pid], text=True, stderr=subprocess.DEVNULL
                )
                for match in re.finditer(r"(\w+)=(\S+)", env_output):
                    key, val = match.group(1), match.group(2)
                    if key == "CONFLUENCE_URL" and not url:
                        url = val
                    elif key == "CONFLUENCE_PERSONAL_TOKEN" and not token:
                        token = val
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback: check Claude MCP settings files
    if not (url and token):
        settings_paths = [
            os.path.expanduser("~/.claude/settings.local.json"),
            os.path.expanduser("~/.claude/settings.json"),
        ]
        for path in settings_paths:
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        data = json.load(f)
                    servers = data.get("mcpServers", {})
                    for name, server in servers.items():
                        if "jira" in name.lower() or "confluence" in name.lower() or "atlassian" in name.lower():
                            env = server.get("env", {})
                            if not url:
                                url = env.get("CONFLUENCE_URL")
                            if not token:
                                token = env.get("CONFLUENCE_PERSONAL_TOKEN")
                            if url and token:
                                break
                except (json.JSONDecodeError, KeyError):
                    pass

    if not url or not token:
        print("Error: Cannot find Confluence credentials.", file=sys.stderr)
        print("Set CONFLUENCE_URL and CONFLUENCE_PERSONAL_TOKEN env vars,", file=sys.stderr)
        print("or ensure mcp-atlassian is running.", file=sys.stderr)
        sys.exit(1)

    return url, token


def make_ssl_context():
    """Create SSL context that skips verification (for internal Confluence)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def ensure_https(url):
    """Convert http:// to https:// to avoid 301 redirect issues with PUT."""
    return re.sub(r"^http://", "https://", url)


def api_request(method, url, token, data=None):
    """Make an API request to Confluence."""
    ctx = make_ssl_context()
    url = ensure_https(url)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    else:
        body = None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, context=ctx)
    except urllib.error.HTTPError as e:
        err_text = e.read().decode("utf-8", errors="replace")
        print(
            f"Confluence API HTTP {e.code} {e.reason}: {method} {url}",
            file=sys.stderr,
        )
        print(err_text, file=sys.stderr)
        if e.code == 409:
            print(
                "提示: 409 多为版本冲突，请先执行 get 取最新 version 再 update。",
                file=sys.stderr,
            )
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Confluence API 请求失败: {e.reason}", file=sys.stderr)
        sys.exit(1)
    return json.loads(resp.read().decode("utf-8"))


def get_page(page_id):
    """Get page content, version, and title."""
    url, token = get_credentials()
    base_url = ensure_https(url)
    api_url = f"{base_url}/rest/api/content/{page_id}?expand=body.storage,version"

    result = api_request("GET", api_url, token)

    title = result["title"]
    version = result["version"]["number"]
    content = result["body"]["storage"]["value"]

    # Save content to temp file
    tmp_file = f"/tmp/cf_page_{page_id}.html"
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(content)

    output = {
        "title": title,
        "version": version,
        "content_file": tmp_file,
        "content_length": len(content),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return output


def update_page(page_id, title, content_file, version, message="Updated by AI"):
    """Update page content."""
    url, token = get_credentials()
    base_url = ensure_https(url)
    api_url = f"{base_url}/rest/api/content/{page_id}"

    with open(content_file, "r", encoding="utf-8") as f:
        content = f.read()

    new_version = int(version) + 1

    data = {
        "id": page_id,
        "type": "page",
        "title": title,
        "version": {
            "number": new_version,
            "message": message,
        },
        "body": {
            "storage": {
                "value": content,
                "representation": "storage",
            }
        },
    }

    result = api_request("PUT", api_url, token, data)

    output = {
        "success": True,
        "new_version": result["version"]["number"],
        "title": result["title"],
        "url": f"{base_url}/pages/viewpage.action?pageId={page_id}",
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return output


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "get":
        page_id = sys.argv[2]
        get_page(page_id)
    elif command == "update":
        if len(sys.argv) < 6:
            print("Usage: python cf_api.py update <page_id> <title> <content_file> <version> [message]")
            sys.exit(1)
        page_id = sys.argv[2]
        title = sys.argv[3]
        content_file = sys.argv[4]
        version = sys.argv[5]
        message = sys.argv[6] if len(sys.argv) > 6 else "Updated by AI"
        update_page(page_id, title, content_file, version, message)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
