#!/bin/bash

# Test script for architecture endpoint with query parameter filtering
# Demonstrates the new view and format filters

API_BASE="https://x7xqq42tpj.execute-api.us-east-1.amazonaws.com/Prod"
REPO_ID="your-repo-id-here"  # Replace with actual repo ID

echo "=========================================="
echo "Architecture Endpoint Filter Tests"
echo "=========================================="
echo ""

# Test 1: Full response (default)
echo "1. Full Response (no filters)"
echo "GET /repos/${REPO_ID}/architecture"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture" | jq -r '.schema_version, .repo_id' | head -2
echo ""

# Test 2: Summary view only
echo "2. Summary View Only"
echo "GET /repos/${REPO_ID}/architecture?view=summary"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=summary" | jq 'keys'
echo ""

# Test 3: Visualizations only
echo "3. Visualizations Only"
echo "GET /repos/${REPO_ID}/architecture?view=visualizations"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=visualizations" | jq '.visualizations | keys'
echo ""

# Test 4: Patterns only
echo "4. Patterns Only"
echo "GET /repos/${REPO_ID}/architecture?view=patterns"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=patterns" | jq '.patterns | length'
echo ""

# Test 5: Layers only
echo "5. Layers Only"
echo "GET /repos/${REPO_ID}/architecture?view=layers"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=layers" | jq '.layers | length'
echo ""

# Test 6: Metrics only
echo "6. Metrics Only"
echo "GET /repos/${REPO_ID}/architecture?view=metrics"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=metrics" | jq '.metrics.health_score'
echo ""

# Test 7: Recommendations only
echo "7. Recommendations Only"
echo "GET /repos/${REPO_ID}/architecture?view=recommendations"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=recommendations" | jq '.recommendations | length'
echo ""

# Test 8: Tech Stack only
echo "8. Tech Stack Only"
echo "GET /repos/${REPO_ID}/architecture?view=tech_stack"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=tech_stack" | jq '.tech_stack | length'
echo ""

# Test 9: Dependencies only
echo "9. Dependencies Only"
echo "GET /repos/${REPO_ID}/architecture?view=dependencies"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=dependencies" | jq '.dependencies | keys'
echo ""

# Test 10: Data Flows only
echo "10. Data Flows Only"
echo "GET /repos/${REPO_ID}/architecture?view=data_flows"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=data_flows" | jq '.data_flows | length'
echo ""

# Test 11: Mermaid format only
echo "11. Visualizations - Mermaid Format Only"
echo "GET /repos/${REPO_ID}/architecture?view=visualizations&format=mermaid"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=visualizations&format=mermaid" | jq '.visualizations.system_architecture | keys'
echo ""

# Test 12: Interactive format only
echo "12. Visualizations - Interactive Format Only"
echo "GET /repos/${REPO_ID}/architecture?view=visualizations&format=interactive"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=visualizations&format=interactive" | jq '.visualizations.system_architecture | keys'
echo ""

# Test 13: D3 format only
echo "13. Visualizations - D3 Format Only"
echo "GET /repos/${REPO_ID}/architecture?view=visualizations&format=d3"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=visualizations&format=d3" | jq '.visualizations.system_architecture | keys'
echo ""

# Test 14: Cytoscape format only
echo "14. Visualizations - Cytoscape Format Only"
echo "GET /repos/${REPO_ID}/architecture?view=visualizations&format=cytoscape"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?view=visualizations&format=cytoscape" | jq '.visualizations.system_architecture | keys'
echo ""

# Test 15: Advanced level with patterns view
echo "15. Advanced Level + Patterns View"
echo "GET /repos/${REPO_ID}/architecture?level=advanced&view=patterns"
curl -s "${API_BASE}/repos/${REPO_ID}/architecture?level=advanced&view=patterns" | jq '.patterns[0].name'
echo ""

echo "=========================================="
echo "All tests completed!"
echo "=========================================="
