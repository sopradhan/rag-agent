# Ollama Environment Configuration
# Set this before starting Ollama to optimize memory usage

# Keep model loaded for 5 minutes (good balance)
$env:OLLAMA_KEEP_ALIVE = "5m"

# Alternative options:
# $env:OLLAMA_KEEP_ALIVE = "0"     # Unload immediately (may cause 404 errors during multi-step tasks)
# $env:OLLAMA_KEEP_ALIVE = "10m"   # Keep for 10 minutes (if you have more RAM)

# Restart Ollama service with new settings
Write-Host "Stopping Ollama..." -ForegroundColor Yellow
Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host "Starting Ollama with optimized settings..." -ForegroundColor Green
Write-Host "  OLLAMA_KEEP_ALIVE = $env:OLLAMA_KEEP_ALIVE" -ForegroundColor Cyan

# Start Ollama (it will run in background)
Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden

Start-Sleep -Seconds 3
Write-Host "Ollama started successfully" -ForegroundColor Green
Write-Host ""
Write-Host "Model will stay loaded for 5 minutes after last use" -ForegroundColor White
Write-Host "This balances memory usage with performance" -ForegroundColor White
