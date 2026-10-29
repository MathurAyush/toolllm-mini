# Helpers for start_demo.bat and stop_demo.bat.
#
#   -Action check-key   exit 0 if .env holds a Gemini key (never prints it)
#   -Action free-port   print a port for the server: stops an old demo
#                       server on 8000, or picks the next free port
#   -Action open        wait for /api/health on -Port, then open the demo page
#   -Action stop        stop every running demo server
#
# Messages go to stderr so `for /f` in the .bat files only reads the port.

param(
    [Parameter(Mandatory = $true)][ValidateSet("check-key", "free-port", "open", "stop")][string]$Action,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$Pattern = "*uvicorn*server.app:app*"

function Say([string]$Text) { [Console]::Error.WriteLine($Text) }

function Get-DemoServers {
    Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" |
        Where-Object { $_.CommandLine -like $Pattern }
}

function Get-Listener([int]$P) {
    # The process id listening on port $P, or $null. Reads netstat because
    # Get-NetTCPConnection is missing or broken on some Windows installs.
    foreach ($line in (netstat -ano)) {
        if ($line -match "^\s*TCP\s+\S+:$P\s+\S+\s+LISTENING\s+(\d+)\s*$") { return [int]$Matches[1] }
    }
    return $null
}

function Stop-Tree([int]$ProcessId) {
    # The venv's python.exe is a launcher with the real interpreter as its
    # child, so stop the parent too when it runs the same command.
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId"
    if ($proc -and $proc.ParentProcessId) {
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)"
        if ($parent -and $parent.CommandLine -like $Pattern) {
            Stop-Process -Id $parent.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

switch ($Action) {
    "check-key" {
        if (-not (Test-Path ".env")) { exit 2 }
        $line = Get-Content ".env" | Where-Object { $_ -match '^\s*GEMINI_API_KEY\s*=' } | Select-Object -Last 1
        if (-not $line) { exit 1 }
        $value = ($line -replace '^\s*GEMINI_API_KEY\s*=\s*', '').Trim().Trim('"', "'")
        if ($value.Length -lt 10 -or $value -match '^(your|<|xxx)') { exit 1 }
        exit 0
    }

    "free-port" {
        $p = $Port
        while ($true) {
            $listener = Get-Listener $p
            if (-not $listener) { break }
            $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$listener"
            if ($owner -and $owner.CommandLine -like $Pattern) {
                Say "Port $p was used by an old demo server (process $listener); stopping it."
                Stop-Tree $listener
                for ($i = 0; $i -lt 20 -and (Get-Listener $p); $i++) { Start-Sleep -Milliseconds 250 }
                if (-not (Get-Listener $p)) { break }
            }
            else {
                $name = if ($owner) { $owner.Name } else { "another program" }
                Say "Port $p is in use by $name (process $listener); trying port $($p + 1)."
            }
            $p++
            if ($p -gt $Port + 20) { Say "No free port between $Port and $p."; exit 1 }
        }
        Write-Output $p
    }

    "open" {
        $url = "http://localhost:$Port"
        for ($i = 0; $i -lt 240; $i++) {
            try {
                $health = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 2
                if ($health.status -eq "ok") {
                    Say ""
                    Say "  Server ready. Opening $url/demo.html"
                    if (-not $health.live) { Say "  Warning: the server has no model key, so questions cannot be answered." }
                    Say ""
                    Start-Process "$url/demo.html"
                    exit 0
                }
            }
            catch { }
            Start-Sleep -Milliseconds 500
        }
        Say "The server did not answer on $url within 2 minutes; see the log above."
        exit 1
    }

    "stop" {
        $servers = @(Get-DemoServers)
        if (-not $servers.Count) { Say "No demo server is running."; exit 0 }
        foreach ($s in $servers) { Stop-Process -Id $s.ProcessId -Force -ErrorAction SilentlyContinue }
        Say "Stopped the demo server ($($servers.Count) process(es))."
    }
}
