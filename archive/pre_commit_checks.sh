#!/bin/bash
# IQC Pro Max Pre-Commit Quality Gates
# Prevents recurring issues BEFORE they reach codebase

echo "🔍 IQC Pro Max Pre-Commit Verification..."
echo ""

# Track overall status
STATUS=0

# ═══════════════════════════════════════════════════════════════
# CHECK 1: Syntax validation (Catches 80% of Python errors)
# ═══════════════════════════════════════════════════════════════
echo "1️⃣  Syntax Check..."
python3 -m py_compile src/verify_ui.py 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   ❌ FAILED: Syntax error in verify_ui.py"
    echo "   💡 Run: python3 -m py_compile src/verify_ui.py"
    STATUS=1
else
    echo "   ✅ PASSED"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 2: Decimal precision (Catches 3-decimal bugs)
# ═══════════════════════════════════════════════════════════════
echo "2️⃣  Decimal Precision Check..."
BAD_PRECISION=$(grep -rn "round.*, *3)" src/ 2>/dev/null)
if [ ! -z "$BAD_PRECISION" ]; then
    echo "   ❌ FAILED: Found round(x, 3) - should be round(x, 2)"
    echo "   💡 Locations:"
    echo "$BAD_PRECISION" | sed 's/^/      /'
    STATUS=1
else
    echo "   ✅ PASSED"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 3: Orphaned finally blocks (Catches syntax errors)
# ═══════════════════════════════════════════════════════════════
echo "3️⃣  Finally Block Structure Check..."
ORPHANED_FINALLY=$(grep -A2 "if.*:" src/verify_ui.py 2>/dev/null | grep -B1 "finally:")
if [ ! -z "$ORPHANED_FINALLY" ]; then
    echo "   ❌ FAILED: Orphaned finally block detected"
    echo "   💡 finally: must be sibling to try:, not inside if:"
    echo "$ORPHANED_FINALLY" | sed 's/^/      /'
    STATUS=1
else
    echo "   ✅ PASSED"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 4: Helper function placement (Catches NameError)
# ═══════════════════════════════════════════════════════════════
echo "4️⃣  Helper Function Placement Check..."
HELPER_COUNT=$(sed -n '35,240p' src/verify_ui.py | grep -c "def create_" 2>/dev/null)
if [ "$HELPER_COUNT" -lt 5 ]; then
    echo "   ❌ FAILED: Chart functions may be misplaced (found $HELPER_COUNT, expected 5-6)"
    echo "   💡 Helper functions must stay at lines 35-240"
    STATUS=1
else
    echo "   ✅ PASSED (found $HELPER_COUNT helper functions)"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 5: API token compatibility (Catches OCR failures)
# ═══════════════════════════════════════════════════════════════
echo "5️⃣  API Token Compatibility Check..."
if [ -f .env ]; then
    TOKEN=$(grep OCR_API_KEY .env | cut -d= -f2 | cut -c1-2)
    if [ "$TOKEN" = "ey" ]; then
        echo "   ⚠️  WARNING: JWT token detected - verify issuer"
        echo "   💡 Run: python3 -c 'import json,base64; print(json.loads(base64.b64decode(open(\".env\").read().split(\"=\")[1].strip().split(\".\")[1]+\"==\")).get(\"iss\"))'"
        # Don't fail commit, just warn
    else
        echo "   ✅ PASSED"
    fi
else
    echo "   ⏭️  SKIPPED (no .env file)"
fi

# ═══════════════════════════════════════════════════════════════
# CHECK 6: Mock data fallbacks (Catches silent failures)
# ═══════════════════════════════════════════════════════════════
echo "6️⃣  Mock Data Fallback Check..."
MOCK_FALLBACK=$(grep -rn "mock_data\|_get_mock" src/ocr_service.py 2>/dev/null | grep -v "def _get_mock_data_multi" | grep -v "No mock data fallbacks")
if [ ! -z "$MOCK_FALLBACK" ]; then
    echo "   ❌ FAILED: Mock data fallback detected (should fail gracefully)"
    echo "$MOCK_FALLBACK" | sed 's/^/      /'
    STATUS=1
else
    echo "   ✅ PASSED"
fi

# ═══════════════════════════════════════════════════════════════
# FINAL RESULT
# ═══════════════════════════════════════════════════════════════
echo ""
if [ $STATUS -eq 0 ]; then
    echo "✅ All checks passed! Safe to commit."
    exit 0
else
    echo ""
    echo "❌ PRE-COMMIT CHECKS FAILED"
    echo ""
    echo "Please fix the issues above before committing."
    echo "💡 See CLAUDE.md 'Pre-Commit Verification Commands' for help."
    exit 1
fi
