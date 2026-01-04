#!/bin/bash
echo "🛡️  STARTING PHASE 1 REGRESSION SUITE 🛡️"
echo "========================================"
export PYTHONPATH=$PYTHONPATH:.

echo "1. [Step 1] SQL AST Security (Unit)..."
python3 tests/security/test_sql_ast.py
if [ $? -eq 0 ]; then echo "✅ PASS"; else echo "❌ FAIL"; exit 1; fi
echo "----------------------------------------"

echo "2. [Step 1] SQL Security Integration..."
python3 tests/manual_security_integration.py
if [ $? -eq 0 ]; then echo "✅ PASS"; else echo "❌ FAIL"; exit 1; fi
echo "----------------------------------------"

echo "3. [Step 2] Circuit Breakers (Unit)..."
python3 tests/unit/test_circuit_breaker.py
if [ $? -eq 0 ]; then echo "✅ PASS"; else echo "❌ FAIL"; exit 1; fi
echo "----------------------------------------"

echo "4. [Step 2] Connector Resilience (Integration)..."
python3 tests/integration/test_connector_resilience.py
if [ $? -eq 0 ]; then echo "✅ PASS"; else echo "❌ FAIL"; exit 1; fi
echo "----------------------------------------"

echo "5. [Step 3] API Rate Limiting (Integration)..."
python3 tests/api/test_rate_limit.py
if [ $? -eq 0 ]; then echo "✅ PASS"; else echo "❌ FAIL"; exit 1; fi
echo "----------------------------------------"

echo "6. [Step 3] API Validation (Integration)..."
python3 tests/api/test_validation.py
if [ $? -eq 0 ]; then echo "✅ PASS"; else echo "❌ FAIL"; exit 1; fi
echo "========================================"
echo "🎉 ALL SECURITY CHECKS PASSED 🎉"
