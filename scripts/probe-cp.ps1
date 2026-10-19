$ErrorActionPreference = "Stop"
$t = Join-Path ([IO.Path]::GetTempPath()) ("cp-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory $t | Out-Null
git -C $t init -q -b main; git -C $t config user.name C; git -C $t config user.email c@example.com
git -C $t commit -q --allow-empty -m "chore: init"; git -C $t tag v1.0.0
git -C $t commit -q --allow-empty -m ("feat: add caf" + [char]0xE9 + " support")
$cafe = "caf" + [char]0xE9
foreach ($cp in 437, 65001) {
  [Console]::OutputEncoding = [Text.Encoding]::GetEncoding($cp)
  "== PS $($PSVersionTable.PSVersion) Console.OutputEncoding=$([Console]::OutputEncoding.WebName)"
  $v = (python -m relnote --repo $t) -join "`n"
  "variable-has-cafe=$($v.Contains($cafe))"
  python -m relnote --repo $t > "$t\r.md"
  $b = [IO.File]::ReadAllBytes("$t\r.md")
  "redirect first={0:X2} {1:X2} utf8-has-cafe={2} utf16-has-cafe={3}" -f $b[0], $b[1], ([Text.Encoding]::UTF8.GetString($b).Contains($cafe)), ([Text.Encoding]::Unicode.GetString($b).Contains($cafe))
  python -m relnote --repo $t | Out-File -Encoding utf8 "$t\o.md"
  $b = [IO.File]::ReadAllBytes("$t\o.md")
  "outfile first={0:X2} {1:X2} {2:X2} utf8-has-cafe={3}" -f $b[0], $b[1], $b[2], ([Text.Encoding]::UTF8.GetString($b).Contains($cafe))
  python -m relnote --repo $t --output "$t\n.md" -q
  "output utf8-has-cafe=" + ([Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes("$t\n.md")).Contains($cafe))
}
