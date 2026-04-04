#!/usr/bin/env bash
# Quick smoke test for the full pipeline
set -euo pipefail

echo "=== OpenRaven Smoke Test ==="

WORKING_DIR=$(mktemp -d)
echo "Working dir: $WORKING_DIR"

cat > "$WORKING_DIR/test_doc.md" << 'EOF'
# Technical Decision: Migrate to Kubernetes

We decided to migrate from EC2 instances to Kubernetes (EKS) for container orchestration.
Key reasons: auto-scaling, self-healing, and declarative infrastructure.
Trade-off: increased operational complexity and learning curve for the team.
EOF

echo ""
echo "1. Initialize knowledge base..."
raven init "$WORKING_DIR/kb"

echo ""
echo "2. Check status..."
raven status -w "$WORKING_DIR/kb"

echo ""
echo "=== Smoke Test Complete ==="
rm -rf "$WORKING_DIR"
