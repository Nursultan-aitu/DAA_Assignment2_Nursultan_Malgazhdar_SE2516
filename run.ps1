param([ValidateSet('test','benchmark','all')][string]$Task = 'all')
$ErrorActionPreference = 'Stop'

# Select a JDK for this process only; do not modify the machine's Java setup.
$jdkCandidates = @()
if ($env:JAVA_HOME) { $jdkCandidates += $env:JAVA_HOME }
$jdkBase = Join-Path $env:USERPROFILE '.jdks'
if (Test-Path -LiteralPath $jdkBase) {
    $jdkCandidates += Get-ChildItem -LiteralPath $jdkBase -Directory |
        Sort-Object @{Expression = { if ($_.Name -match '21') { 0 } else { 1 } }}, Name |
        Select-Object -ExpandProperty FullName
}
$compiler = Get-Command javac.exe -ErrorAction SilentlyContinue
if ($compiler) { $jdkCandidates += Split-Path (Split-Path $compiler.Source -Parent) -Parent }
$selectedJdk = $null
foreach ($candidate in $jdkCandidates) {
    if (!(Test-Path -LiteralPath (Join-Path $candidate 'bin/javac.exe'))) { continue }
    $versionText = (& (Join-Path $candidate 'bin/java.exe') -version 2>&1 | Out-String)
    if ($versionText -match 'version "(\d+)' -and [int]$Matches[1] -ge 17) {
        $selectedJdk = $candidate
        break
    }
}
if (!$selectedJdk) { throw 'Install JDK 17 or newer and set JAVA_HOME to its directory.' }
$env:JAVA_HOME = $selectedJdk
Push-Location $PSScriptRoot
try {
    Write-Host "Using JDK: $selectedJdk"
    switch ($Task) {
        'test' { & './mvnw.cmd' -B clean verify }
        'benchmark' { & './mvnw.cmd' -B compile exec:java }
        'all' { & './mvnw.cmd' -B clean verify exec:java }
    }
    if ($LASTEXITCODE -ne 0) { throw "Maven failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}
