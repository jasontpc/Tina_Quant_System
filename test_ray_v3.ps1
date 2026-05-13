$input = "VOO is at 478.50 dollars. Output pure JSON with action, confidence, logic_bridge, orders (entry/stop_loss/take_profit):"
$result = ollama run ray-v3 $input --verbose 2>&1
Write-Output $result
