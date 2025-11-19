# Clean Up Ollama Models
# Remove large models to free up disk space and prevent memory issues

Write-Host "Cleaning up large Ollama models..." -ForegroundColor Yellow
Write-Host ""

# List current models
Write-Host "Current models:" -ForegroundColor Cyan
ollama list

Write-Host ""
Write-Host "Removing large models..." -ForegroundColor Yellow

# Remove heavy models
$modelsToRemove = @(
    "qwen2.5:7b",     # 4.7GB
    "gemma3:4b"       # 3.3GB (no tool calling)
)

foreach ($model in $modelsToRemove) {
    Write-Host "  Removing $model..." -ForegroundColor Red
    ollama rm $model 2>$null
}

Write-Host ""
Write-Host "✓ Cleanup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Remaining models:" -ForegroundColor Cyan
ollama list

Write-Host ""
Write-Host "Recommended lightweight models:" -ForegroundColor White
Write-Host "  - phi3:mini (2.3GB) - Best for tool calling" -ForegroundColor Green
Write-Host "  - qwen2.5:3b (1.9GB) - Good balance" -ForegroundColor Green
Write-Host "  - qwen2.5:1.5b (1GB) - Smallest option" -ForegroundColor Green
