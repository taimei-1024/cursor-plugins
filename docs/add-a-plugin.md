# Add a plugin

This repository supports both **Cursor** and **Claude Code**.

Add a new plugin under `plugins/` and register it in both `.cursor-plugin/marketplace.json` and `.claude-plugin/marketplace.json`.

## 1. Create plugin directory

Create a new folder:

```text
plugins/my-new-plugin/
```

Add the required manifests (create both):

```text
plugins/my-new-plugin/.cursor-plugin/plugin.json  # For Cursor
plugins/my-new-plugin/.claude-plugin/plugin.json  # For Claude Code
```

**Cursor manifest** (`.cursor-plugin/plugin.json`):

```json
{
  "name": "my-new-plugin",
  "displayName": "My New Plugin",
  "version": "0.1.0",
  "description": "Describe what this plugin does",
  "author": { "name": "Your Org" },
  "license": "MIT",
  "logo": "assets/logo.png"
}
```

**Claude Code manifest** (`.claude-plugin/plugin.json`):

```json
{
  "name": "my-new-plugin",
  "description": "Describe what this plugin does",
  "author": {
    "name": "Your Org"
  }
}
```

## 2. Add plugin components

Add only the components you need:

- `rules/` with `.mdc` files (YAML frontmatter required)
- `skills/<skill-name>/SKILL.md` (YAML frontmatter required)
- `agents/*.md` (YAML frontmatter required)
- `commands/*.(md|mdc|markdown|txt)` (frontmatter recommended)
- `hooks/hooks.json` and `scripts/*` for automation hooks
- `mcp.json` for MCP server definitions
- `assets/logo.png` for marketplace display

## 3. Register in marketplace manifests

**Cursor** (`.cursor-plugin/marketplace.json`):

```json
{
  "name": "taimei-plugins",
  "owner": { "name": "Your Org" },
  "metadata": {
    "description": "Plugin collection",
    "version": "0.1.0",
    "pluginRoot": "plugins"
  },
  "plugins": [
    {
      "name": "my-new-plugin",
      "source": "my-new-plugin",
      "description": "Describe your plugin"
    }
  ]
}
```

**Claude Code** (`.claude-plugin/marketplace.json`):

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "taimei-plugins",
  "description": "Plugin collection",
  "owner": { "name": "Your Org" },
  "plugins": [
    {
      "name": "my-new-plugin",
      "source": "./plugins/my-new-plugin",
      "description": "Describe your plugin"
    }
  ]
}
```

## 4. Validate

```bash
node scripts/validate-template.mjs
```

Fix all reported errors before committing.

## 5. Common pitfalls

- Plugin `name` not kebab-case.
- `source` path in marketplace manifest does not match folder name.
- Missing `.cursor-plugin/plugin.json` or `.claude-plugin/plugin.json` in plugin folder.
- Missing frontmatter keys (`name`, `description`) in skills, agents, or commands.
- Rule files missing frontmatter `description`.
- Broken relative paths for `logo`, `hooks`, or `mcpServers` in manifest files.
