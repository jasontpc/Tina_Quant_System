Get-ChildItem -Path . -Filter "*.py" -File | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -match "ray-v1|ray-deep|qwen2\.5:3b|qwen3\.5:4b|qwen2\.5:7b|MODEL_FAST|MODEL_DEEP") {
        Write-Host "=== $($_.Name) ==="
        Select-String -Path $_.FullName -Pattern "ray-v1|ray-deep|qwen2\.5:3b|qwen3\.5:4b|qwen2\.5:7b|MODEL_FAST|MODEL_DEEP" | ForEach-Object {
            Write-Host "  $($_.Line): $($_.Line.Trim())"
        }
    }
}
