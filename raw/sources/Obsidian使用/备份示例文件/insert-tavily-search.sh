#!/bin/bash

# ========== 请在这里替换成你的 Tavily API Key ==========
TAVILY_API_KEY="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"
# =====================================================

# 1. 安装并添加 Tavily MCP 全局生效
echo "===== 正在安装 Tavily MCP ====="
claude mcp add --transport http tavily https://mcp.tavily.com/mcp/?tavilyApiKey=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 --scope user

# 2. 配置 Claude Code 禁用原生 WebSearch / WebFetch
echo "===== 禁用 Claude Code 原生联网工具 ====="
CLAUDE_SETTINGS="$HOME/.claude/settings.json"

# 写入禁用配置
cat > "$CLAUDE_SETTINGS" <<EOF
{
  "permissions": {
    "deny": ["WebSearch", "WebFetch"]
  }
}
EOF

# 3. 全局 CLAUDE.md 强制要求只用 Tavily 搜索
echo "===== 写入全局规则：强制使用 Tavily MCP ====="
CLAUDE_GLOBAL_MD="$HOME/.claude/CLAUDE.md"

cat > "$CLAUDE_GLOBAL_MD" <<EOF
# 全局联网规则
1. 禁止使用 Claude Code 原生 WebSearch、WebFetch 工具
2. 所有网络搜索、查文档、查资料、查报错 必须使用 tavily-search MCP 插件
3. 优先用 tavily-search 做全网检索，再解析页面内容
EOF

echo "===== 配置完成 ====="
echo "请重启 Claude Code 生效：claude"
echo "验证命令：claude mcp list 查看 tavily-search 是否正常连接"