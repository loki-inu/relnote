# Probe how relnote output survives PowerShell redirection on Windows.
# Usage: windows-probe.ps1 -Label <name>
param([string]$Label = "shell")
$ErrorActionPreference = "Stop"
$root = (Get-Location).Path
$t = Join-Path $env:RUNNER_TEMP "probe-$Label"
if (Test-Path $t) { Remove-Item -Recurse -Force $t }
New-Item -ItemType Directory $t | Out-Null
git -C $t init -q -b main
git -C $t config user.name "Probe"
git -C $t config user.email "probe@example.com"
git -C $t commit -q --allow-empty -m "chore: init"
git -C $t tag v1.0.0
git -C $t commit -q --allow-empty -m "feat: add caf$([char]0xE9) $([char]0x2713) support"
git -C $t commit -q --allow-empty -m "fix: handle na$([char]0xEF)ve dates"

function Show-Bytes([string]$path) {
  $b = [IO.File]::ReadAllBytes($path)
  $hex = ($b[0..3] | ForEach-Object { $_.ToString("X2") }) -join " "
  $utf8 = [Text.Encoding]::UTF8.GetString($b)
  $bom = if ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) { "utf8-bom" } elseif ($b.Length -ge 2 -and $b[0] -eq 0xFF -and $b[1] -eq 0xFE) { "utf16le-bom" } else { "none" }
  "{0}: {1} bytes, first={2}, bom={3}, utf8-has-arrow={4}, utf8-has-cafe={5}" -f (Split-Path $path -Leaf), $b.Length, $hex, $bom, $utf8.Contains([string][char]0x2192), $utf8.Contains("caf" + [char]0xE9)
}

$env:PYTHONPATH = $root
"== $Label  PSVersion=$($PSVersionTable.PSVersion)  Console.OutputEncoding=$([Console]::OutputEncoding.WebName)  OutputEncoding=$($OutputEncoding.WebName)"
python -m relnote --repo $t --output (Join-Path $t "a-output.md") --quiet
Show-Bytes (Join-Path $t "a-output.md")
python -m relnote --repo $t > (Join-Path $t "b-redirect.md")
Show-Bytes (Join-Path $t "b-redirect.md")
python -m relnote --repo $t | Out-File -Encoding utf8 (Join-Path $t "c-outfile-utf8.md")
Show-Bytes (Join-Path $t "c-outfile-utf8.md")
$notes = python -m relnote --repo $t
"variable-has-arrow={0} variable-has-cafe={1}" -f (($notes -join "`n").Contains([string][char]0x2192)), (($notes -join "`n").Contains("caf" + [char]0xE9))
$next = python -m relnote --repo $t --next-version
"next-version=$next"
