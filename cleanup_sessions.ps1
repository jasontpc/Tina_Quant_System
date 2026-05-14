$dir = "C:\Users\USER\.openclaw\agents\main\sessions\"

# 1. Clear usage-cost-cache (12.8MB)
$uc = Join-Path $dir ".usage-cost-cache.json"
if (Test-Path $uc) {
    $s = (Get-Item $uc).Length / 1MB
    Remove-Item $uc -Force
    Write-Output "[DEL] .usage-cost-cache.json ($([math]::Round($s,1)) MB)"
}

# 2. Delete sessions.json.bak older than 7 days
$bakFiles = Get-ChildItem $dir -Filter "sessions.json.bak.*" -ErrorAction SilentlyContinue
$cutoff = (Get-Date).AddDays(-7)
$bakDeleted = 0
foreach ($f in $bakFiles) {
    if ($f.LastWriteTime -lt $cutoff) {
        $s = $f.Length / 1MB
        Remove-Item $f.FullName -Force
        Write-Output "[DEL] $($f.Name) ($([math]::Round($s,1)) MB, age=$(($cutoff - $f.LastWriteTime).Days)d)"
        $bakDeleted++
    }
}
Write-Output "[INFO] Deleted $bakDeleted old sessions.json.bak files"

# 3. Delete checkpoint files older than 7 days (keep recent)
$cpFiles = Get-ChildItem $dir -Filter "*.checkpoint.*.jsonl" -ErrorAction SilentlyContinue
$cpDeleted = 0
$cpFreed = 0
foreach ($f in $cpFiles) {
    if ($f.LastWriteTime -lt $cutoff) {
        $s = $f.Length / 1MB
        $cpFreed += $s
        Remove-Item $f.FullName -Force
        $cpDeleted++
    }
}
Write-Output "[DEL] $cpDeleted old checkpoint files, freed $([math]::Round($cpFreed,1)) MB"

# 4. Keep only active sessions (last 3 days)
$activeCutoff = (Get-Date).AddDays(-3)
$activeFiles = Get-ChildItem $dir -File -ErrorAction SilentlyContinue | Where-Object {
    $_.LastWriteTime -gt $activeCutoff -and $_.Name -notmatch "sessions.json"
}
Write-Output "[INFO] Active files (last 3 days): $($activeFiles.Count)"

# Summary
$remaining = Get-ChildItem $dir -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum
$remainingMB = [math]::Round($remaining.Sum / 1MB, 1)
Write-Output ""
Write-Output "=== Cleanup Complete ==="
Write-Output "Remaining sessions size: $remainingMB MB"