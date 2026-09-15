# setup_fred_key.ps1 -- store the FRED API key on this machine, once.
#
# Run it once on each machine you work on. It prompts for the key and writes it
# to the current user's persistent environment, where fetch_data.py and
# backfill_historical_data.py read it.
#
# This covers LOCAL runs only. The scheduled refresh runs inside GitHub Actions
# and reads the FRED_API_KEY repository secret instead, which is set separately
# under Settings -> Secrets and variables -> Actions. Rotating the key means
# updating both, plus any other machine.
#
# WHY THIS EXISTS INSTEAD OF THE USUAL ADVICE
#
#   set FRED_API_KEY=abc123        session only, gone when the shell closes
#   setx FRED_API_KEY "abc123"     persists, and leaks
#
# Both put the key on a command line. A command line is written to PowerShell
# history in plaintext and stays there indefinitely, is echoed back to the
# console, and passes through the transcript of any agent session that runs it
# -- which means the key has been transmitted to a third party and stored on
# their infrastructure. Read-Host -AsSecureString takes the value without it
# ever reaching a command line, so nothing enters history and nothing is
# transcribed. setx carries a second defect: it silently truncates at 1024
# characters, producing a credential that looks set and does not work.
#
# This script contains no credentials. It is safe to commit and safe to read.
#
# The variable is plain FRED_API_KEY with no project prefix, and the same
# variable is read by other projects on the same machine. That is deliberate:
# FRED issues one account-wide, read-only key with no billing attached, so
# splitting it per project would create a second copy to rotate and contain
# nothing. Object-store tokens are the opposite case and stay prefixed.
#
# Usage:  powershell -ExecutionPolicy Bypass -File setup_fred_key.ps1

$ErrorActionPreference = "Stop"

$Name = "FRED_API_KEY"

Write-Host ""
Write-Host "FRED API key" -ForegroundColor Cyan
Write-Host "Get one at: https://fredaccount.stlouisfed.org/apikeys"
Write-Host ""
Write-Host "The key is free, read-only, and has no billing attached. It is still"
Write-Host "a credential: it identifies your account and can be rate-limited or"
Write-Host "revoked. Do not paste it into a chat, a file, or a command line."
Write-Host ""

$existing = [Environment]::GetEnvironmentVariable($Name, "User")
if ($existing) {
    Write-Host "  $Name is already set ($($existing.Length) chars, value hidden)" -ForegroundColor DarkGray
    $reply = Read-Host "  Replace it? (y/N)"
    if ($reply -ne "y") {
        Write-Host "  left unchanged" -ForegroundColor DarkGray
        Write-Host ""
        exit 0
    }
}

# -AsSecureString keeps the value off the console and out of history.
$secure = Read-Host "  FRED API key (input hidden)" -AsSecureString
$bstr   = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $value = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
} finally {
    # Zero the unmanaged copy rather than leaving it in memory.
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

if ([string]::IsNullOrWhiteSpace($value)) {
    Write-Host "  skipped (nothing entered)" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

$value = $value.Trim()

# A FRED key is 32 lowercase alphanumeric characters. Checking the shape here
# catches a truncated or partial paste now, rather than as an authentication
# failure later that looks like a network problem.
if ($value -notmatch '^[0-9a-z]{32}$') {
    Write-Host ""
    Write-Host "  WARNING: that does not look like a FRED key." -ForegroundColor Yellow
    Write-Host "  Expected 32 lowercase alphanumeric characters; got $($value.Length)." -ForegroundColor Yellow
    $anyway = Read-Host "  Save it anyway? (y/N)"
    if ($anyway -ne "y") {
        Write-Host "  not saved" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
}

# SetEnvironmentVariable rather than setx: setx truncates silently at 1024
# characters and echoes the value back to the console.
[Environment]::SetEnvironmentVariable($Name, $value, "User")

# Report state without ever printing the value. A length is enough to tell
# configured from missing, and enough to catch a truncated paste.
$saved = [Environment]::GetEnvironmentVariable($Name, "User")
Write-Host ""
Write-Host "Current state:" -ForegroundColor Cyan
if ([string]::IsNullOrWhiteSpace($saved)) {
    Write-Host "  $Name : MISSING" -ForegroundColor Red
} else {
    Write-Host "  $Name : set ($($saved.Length) chars)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Open a NEW terminal, then verify with:" -ForegroundColor Cyan
Write-Host "  python fetch_data.py"
Write-Host ""
Write-Host "A newly set variable is invisible to anything already running: a"
Write-Host "shell, an editor, or an agent session keeps the environment it was"
Write-Host "born with until it restarts."
Write-Host ""
Write-Host "IF YOU ARE ROTATING THE KEY, there are three places to update:" -ForegroundColor Yellow
Write-Host "  1. this machine (done)"
Write-Host "  2. your other machine (run this script there)"
Write-Host "  3. the FRED_API_KEY repository secret on GitHub, under Settings ->"
Write-Host "     Secrets and variables -> Actions. The scheduled refresh in"
Write-Host "     .github/workflows/ breaks quietly without it."
Write-Host ""
Write-Host "The key is stored in your Windows user environment, not in this"
Write-Host "repository. Nothing credential-shaped is ever committed, and no"
Write-Host "secret passes through an agent session."
Write-Host ""
