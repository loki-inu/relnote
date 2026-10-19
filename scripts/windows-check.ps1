# Windows smoke check for the commands in docs/windows.html.
# Runs under PowerShell 7 (pwsh) and Windows PowerShell 5.1 (powershell).
#   ./scripts/windows-check.ps1 [-Relnote "python -m relnote"]
# Only ASCII in this file: Windows PowerShell 5.1 reads BOM-less scripts as ANSI.
param([string]$Relnote = "python -m relnote")
$ErrorActionPreference = "Stop"
$exe, $pre = $Relnote.Split(" ", 2)
$preArgs = if ($pre) { $pre.Split(" ") } else { @() }
function rn { & $exe @preArgs @args; if ($LASTEXITCODE -ne 0) { throw "relnote $args exited $LASTEXITCODE" } }

$arrow = [string][char]0x2192
$cafe = "caf" + [char]0xE9
$t = Join-Path ([IO.Path]::GetTempPath()) ("relnote-check-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory $t | Out-Null
git -C $t init -q -b main
git -C $t config user.name "Check"
git -C $t config user.email "check@example.com"
git -C $t config core.autocrlf false
git -C $t commit -q --allow-empty -m "chore: init"
git -C $t tag v1.0.0
git -C $t commit -q --allow-empty -m "feat: add $cafe support"

function Assert-Utf8Lf([string]$path) {
  $b = [IO.File]::ReadAllBytes($path)
  if ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) { throw "$path has a UTF-8 BOM" }
  if ($b -contains 13) { throw "$path has CR bytes" }
  $s = [Text.Encoding]::UTF8.GetString($b)
  if (-not $s.Contains($arrow) -or -not $s.Contains($cafe)) { throw "$path is not the expected UTF-8 text" }
}

"PowerShell $($PSVersionTable.PSVersion)"

# 1. --output writes UTF-8, no BOM, LF in any PowerShell version.
$notes = Join-Path $t "notes.md"
rn --repo $t --output $notes --quiet
Assert-Utf8Lf $notes
"ok  --output notes.md"

# 2. Capturing into a variable keeps the text.
$text = (rn --repo $t) -join "`n"
if (-not $text.Contains($cafe)) { throw "variable capture lost non-ASCII text" }
"ok  `$notes = relnote"

# 3. --next-version into a variable.
$next = rn --repo $t --next-version
if ($next -ne "v1.1.0") { throw "next-version: got '$next'" }
"ok  --next-version -> $next"

# 4. --changelog keeps an existing LF file LF.
$log = Join-Path $t "CHANGELOG.md"
[IO.File]::WriteAllBytes($log, [Text.Encoding]::UTF8.GetBytes("# Changelog`n`n## [v1.0.0] - 2026-01-01`n`n- first`n"))
rn --repo $t --changelog $log --changelog-title v1.1.0 --date 2026-10-19 --quiet
$b = [IO.File]::ReadAllBytes($log)
if ($b -contains 13) { throw "CHANGELOG.md was rewritten with CRLF" }
"ok  --changelog keeps LF"

# 5. Windows PowerShell 5.1: '>' re-encodes native output as UTF-16LE (documented pitfall).
if ($PSVersionTable.PSVersion.Major -lt 6) {
  rn --repo $t > (Join-Path $t "redirect.md")
  $r = [IO.File]::ReadAllBytes((Join-Path $t "redirect.md"))
  "info: Windows PowerShell '>' wrote first bytes {0:X2} {1:X2} (FF FE = UTF-16LE)" -f $r[0], $r[1]
}
Remove-Item -Recurse -Force $t
"windows-check: all good"
