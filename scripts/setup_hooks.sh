#!/bin/bash
# Install git pre-push hook for AI log submission
set -e

HOOK_FILE=".git/hooks/pre-push"

cat > "$HOOK_FILE" << 'EOF'
#!/bin/bash
# Submit AI logs to grading server before push
python3 scripts/submit_log.py
exit 0  # Never block push
EOF

chmod +x "$HOOK_FILE"
echo "[ai-log] Git pre-push hook installed."

# Create .ai-log directory if not exists
mkdir -p .ai-log
touch .ai-log/.gitkeep

echo "[ai-log] Setup complete. Configure AI_LOG_SERVER in your .env file."
