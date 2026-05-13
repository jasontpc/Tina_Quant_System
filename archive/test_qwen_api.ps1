$body = @{
    model = "qwen3.5:4b"
    prompt = "解釋 Sharpe Ratio，用一句繁體中文話"
    options = @{
        temperature = 0.3
        num_predict = 80
    }
} | ConvertTo-Json -Compress

$headers = @{ "Content-Type" = "application/json" }
$response = Invoke-WebRequest -Uri "http://localhost:11434/api/generate" -Method POST -Body $body -Headers $headers -TimeoutSec 30
$response.Content | ConvertFrom-Json | Select-Object -ExpandProperty response