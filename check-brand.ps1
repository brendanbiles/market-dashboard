#Requires -Version 5.1
<#
  check-brand.ps1 - shared brand layer check for every site under brendanbiles.com

  CANONICAL SOURCE: personal-site/check-brand.ps1
  Other sites vendor a COPY of this file next to their vendored brand.css, the
  same way brand.css itself is vendored. It is deliberately identical across
  sites and finds its own paths, so a copy needs no edits.

  It never sits in a served directory. It is a tool, not a page.

  WHAT IT CHECKS, and why each check exists

  1. DRIFT. brand.css is copied, not linked, so nothing makes the copies agree.
     Compares this site's brand.css against the canonical one and reports any
     difference. -Apply overwrites the local copy with the canonical.

     Run inside personal-site the local copy IS canonical, so the same
     comparison against the published URL answers a different question:
     whether what is deployed matches what is in the repository.

  2. COLLISIONS. brand.css styles shared furniture - the header, the footer,
     the site switcher - through classes on ordinary elements. A bare element
     selector in a site's own stylesheet therefore lands on the shared
     furniture as well as on that site's own markup.

     This is not hypothetical. On 2026-09-17 market-dashboard carried
     "header { padding-bottom: 1.25rem; border-bottom: ... }" for its page
     title. It also matched <header class="site-head">, which made the markets
     header taller than the other two sites and gave it two stacked borders.
     That is the bug this check exists to catch.

  3. REDEFINITIONS. A site redefining a class or a token that brand.css already
     defines is how two copies stop matching without either file being edited.
     Class redefinitions are errors. Token overrides are reported and allowed,
     because market-dashboard overrides --wrap on purpose.

  USAGE
    .\check-brand.ps1                                  compare against the live URL
    .\check-brand.ps1 -Canonical ..\personal-site\public\brand.css
    .\check-brand.ps1 -Apply                           take the canonical copy
#>
[CmdletBinding()]
param(
  # A path or an https URL. Default is the published canonical copy.
  [string] $Canonical = 'https://brendanbiles.com/brand.css',

  # Overwrite the local vendored brand.css with the canonical one.
  [switch] $Apply
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$errors = New-Object System.Collections.Generic.List[string]
$warns  = New-Object System.Collections.Generic.List[string]
$notes  = New-Object System.Collections.Generic.List[string]

# ---------------------------------------------------------------- locate files
# personal-site keeps its served files under public/; the other sites serve the
# repository root. Detect rather than configure, so the copies stay identical.
if (Test-Path 'public/brand.css') { $root = 'public' } else { $root = '.' }

$localBrand = Join-Path $root 'brand.css'
if (-not (Test-Path $localBrand)) {
  Write-Host "No brand.css found. Looked in '$root'." -ForegroundColor Red
  exit 1
}
$siteCss = @(Get-ChildItem -Path $root -Filter '*.css' |
             Where-Object { $_.Name -ne 'brand.css' })

Write-Host ""
Write-Host ("brand check - {0}" -f (Split-Path -Leaf $PSScriptRoot)) -ForegroundColor Cyan
Write-Host ("  brand layer : {0}" -f $localBrand)
Write-Host ("  site styles : {0}" -f (($siteCss | ForEach-Object { $_.Name }) -join ', '))
Write-Host ("  canonical   : {0}" -f $Canonical)
Write-Host ""

# -------------------------------------------------------------------- 1. drift
# Compare normalised text, not bytes. The copies travel between machines and a
# line-ending flip is not drift.
function Get-NormalisedText([string] $text) {
  $lf = [string][char]10
  $crlf = [string][char]13 + $lf
  # A byte-order mark is an encoding artifact, not a difference in the CSS.
  return ($text.TrimStart([char]0xFEFF).Replace($crlf, $lf)).TrimEnd()
}

$localText = Get-NormalisedText (Get-Content -LiteralPath $localBrand -Raw -Encoding UTF8)

# Windows PowerShell 5.1 decodes a response body as Latin-1 when the server
# sends no charset in Content-Type, which Cloudflare does not for text/css.
# Reading .Content directly turns every em dash in brand.css into mojibake and
# the drift check then fails on every run. Decode the raw bytes as UTF-8.
function Get-UrlTextUtf8([string] $url) {
  $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 20
  $bytes = $null
  if ($null -ne $resp.RawContentStream) {
    $ms = New-Object System.IO.MemoryStream
    $resp.RawContentStream.Position = 0
    $resp.RawContentStream.CopyTo($ms)
    $bytes = $ms.ToArray()
  }
  if ($null -eq $bytes) { return [string]$resp.Content }
  $text = [System.Text.Encoding]::UTF8.GetString($bytes)
  return $text.TrimStart([char]0xFEFF)
}

$canonText = $null
if ($Canonical -match '^https?://') {
  try {
    $canonText = Get-NormalisedText (Get-UrlTextUtf8 $Canonical)
  } catch {
    $warns.Add("Could not fetch $Canonical - " + $_.Exception.Message + ". Drift not checked.")
  }
} elseif (Test-Path -LiteralPath $Canonical) {
  $canonText = Get-NormalisedText (Get-Content -LiteralPath $Canonical -Raw -Encoding UTF8)
} else {
  $errors.Add("Canonical source not found: $Canonical")
}

# Is this the repository that owns brand.css? The public/ split is the tell.
$isCanonicalRepo = ($root -eq 'public')
$canonIsUrl = ($Canonical -match '^https?://')

if ($null -ne $canonText) {
  if ($localText -eq $canonText) {
    if ($isCanonicalRepo -and $canonIsUrl) {
      Write-Host "  [ok]    deployed brand.css matches this repository" -ForegroundColor Green
    } else {
      Write-Host "  [ok]    brand.css matches the canonical copy" -ForegroundColor Green
    }
  } else {
    $lf = [string][char]10
    $localArr = $localText -split $lf
    $canonArr = $canonText -split $lf
    $localLines = $localArr.Count
    $canonLines = $canonArr.Count

    # Name the first line that differs. A line count alone is no help when the
    # two files are the same length and one character apart.
    $where = ''
    $n = [Math]::Min($localLines, $canonLines)
    for ($i = 0; $i -lt $n; $i++) {
      if ($localArr[$i] -ne $canonArr[$i]) {
        $where = " First difference at line $($i + 1): here '$($localArr[$i].Trim())' / canonical '$($canonArr[$i].Trim())'."
        break
      }
    }
    if ($isCanonicalRepo -and $canonIsUrl) {
      # This repository is right by definition, so the deployment is the stale
      # side. -Apply here would overwrite the canonical file with an old copy.
      $warns.Add("Deployed brand.css differs from this repository ($canonLines lines live, $localLines here).$where This site needs a deploy. Do NOT run -Apply.")
    } elseif ($Apply) {
      Set-Content -LiteralPath $localBrand -Value $canonText -Encoding UTF8
      Write-Host "  [fixed] brand.css replaced with the canonical copy" -ForegroundColor Yellow
      $notes.Add("brand.css was updated. Redeploy this site.")
    } else {
      $errors.Add("brand.css has drifted from the canonical copy ($localLines lines here, $canonLines canonical).$where Re-run with -Apply to take the canonical version.")
    }
  }
}

# ------------------------------------------------------------- parse helpers
function Remove-CssComments([string] $css) {
  return [regex]::Replace($css, '/\*.*?\*/', '', 'Singleline')
}

function Get-Selectors([string] $css) {
  # Every selector list that opens a block, including rules nested inside
  # @media, which is where a collision is easiest to miss.
  $out = New-Object System.Collections.Generic.List[string]
  foreach ($m in [regex]::Matches($css, '(?m)^\s*([^{}@]+?)\s*\{')) {
    $out.Add($m.Groups[1].Value.Trim())
  }
  return ,$out
}

function Get-Classes([string] $css) {
  $set = New-Object System.Collections.Generic.HashSet[string]
  foreach ($sel in (Get-Selectors $css)) {
    foreach ($m in [regex]::Matches($sel, '\.([A-Za-z][\w-]*)')) {
      [void]$set.Add($m.Groups[1].Value)
    }
  }
  return ,$set
}

function Get-Tokens([string] $css) {
  $set = New-Object System.Collections.Generic.HashSet[string]
  foreach ($m in [regex]::Matches($css, '(--[A-Za-z][\w-]*)\s*:')) {
    [void]$set.Add($m.Groups[1].Value)
  }
  return ,$set
}

$brandCss     = Remove-CssComments $localText
$brandClasses = Get-Classes $brandCss
$brandTokens  = Get-Tokens   $brandCss

# Elements that carry shared furniture in the brand markup. A bare selector on
# any of these reaches the shared header, footer or site switcher.
$furniture = @('header', 'footer', 'nav', 'details', 'summary')

# --------------------------------------------------- 2 and 3, per stylesheet
foreach ($f in $siteCss) {
  $raw  = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8
  $css  = Remove-CssComments $raw
  $name = $f.Name

  # 2. collisions
  foreach ($sel in (Get-Selectors $css)) {
    foreach ($part in ($sel -split ',')) {
      $p = $part.Trim()
      if ($furniture -contains $p.ToLower()) {
        $errors.Add("$name - bare '$p' selector. brand.css puts shared furniture on <$p>, so this rule also restyles the shared header, footer or switcher. Scope it, for example '.container > $p'.")
      }
    }
  }

  # 3. redefinitions
  foreach ($c in (Get-Classes $css)) {
    if ($brandClasses.Contains($c)) {
      $errors.Add("$name - redefines '.$c', which brand.css already defines. Two definitions for one class is how the sites stop matching. Rename it, or change brand.css and re-vendor.")
    }
  }
  foreach ($t in (Get-Tokens $css)) {
    if ($brandTokens.Contains($t)) {
      $notes.Add("$name - overrides the shared token '$t'. Allowed; confirm it is deliberate.")
    }
  }
}

# --------------------------------------------------------------------- report
Write-Host ""
foreach ($n in $notes)  { Write-Host "  [note]  $n" -ForegroundColor DarkGray }
foreach ($w in $warns)  { Write-Host "  [warn]  $w" -ForegroundColor Yellow }
foreach ($e in $errors) { Write-Host "  [FAIL]  $e" -ForegroundColor Red }

Write-Host ""
if ($errors.Count -gt 0) {
  Write-Host ("brand check FAILED - {0} problem(s)" -f $errors.Count) -ForegroundColor Red
  exit 1
}
if ($warns.Count -gt 0) {
  Write-Host "brand check passed with warnings" -ForegroundColor Yellow
  exit 0
}
Write-Host "brand check passed" -ForegroundColor Green
exit 0
