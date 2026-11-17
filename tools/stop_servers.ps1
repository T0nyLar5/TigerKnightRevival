# Stops fake lobby / battle servers (python from tools\.venv listening on 3010-3019/7777).
# Add -Game to also stop Kingdom-Win64/Win32-Shipping.exe. ASCII only.
param([switch]$Game)
$venv = (Join-Path $PSScriptRoot '.venv').ToLower()
$ports = 3010..3019 + 7777 + 7791
$pids = @{}
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $ports -contains $_.LocalPort } | ForEach-Object { $pids[[int]$_.OwningProcess] = $_.LocalPort }
foreach ($id in @($pids.Keys)) {
  $p = Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue
  if (-not $p) { continue }
  $own = (($p.ExecutablePath + ' ' + $p.CommandLine).ToLower()).Contains($venv)
  if (-not $own -and $p.ParentProcessId) {
    $pp = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)" -ErrorAction SilentlyContinue
    if ($pp) { $own = (($pp.ExecutablePath + ' ' + $pp.CommandLine).ToLower()).Contains($venv) }
  }
  if ($own -and $p.Name -like 'python*') {
    taskkill /F /T /PID $id | Out-Null
    Write-Host "stopped python pid $id (port $($pids[$id]))"
  } else { Write-Host "skip pid $id ($($p.Name)) on port $($pids[$id]): not from tools\.venv" }
}
if ($Game) {
  foreach ($n in 'Kingdom-Win64-Shipping','Kingdom-Win32-Shipping') {
    Get-Process -Name $n -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.Id -Force; Write-Host "stopped $n pid $($_.Id)" }
  }
}
