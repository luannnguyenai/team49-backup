param(
    [string]$Branch = "save-ui",
    [string]$BaseBranch = "main",
    [string]$TargetFile = "docs/save-ui-heartbeat.md",
    [string]$CommitMessage
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}

function Ensure-PrePushHook {
    $hookPath = Join-Path ".git" "hooks\pre-push"
    if (Test-Path $hookPath) {
        return
    }

    $bash = Get-Command bash -ErrorAction SilentlyContinue
    if (-not $bash) {
        throw "Git pre-push hook is missing and 'bash' is not available to run scripts/setup_hooks.sh"
    }

    & $bash.Source "scripts/setup_hooks.sh"
}

function Ensure-Branch {
    param(
        [string]$Name,
        [string]$FallbackBase
    )

    $currentBranch = (git branch --show-current).Trim()
    if ($currentBranch -eq $Name) {
        return
    }

    $localExists = (git branch --list $Name).Trim()
    if ($localExists) {
        git checkout $Name | Out-Null
        return
    }

    $remoteExists = (git branch -r --list "origin/$Name").Trim()
    if ($remoteExists) {
        git checkout -b $Name --track "origin/$Name" | Out-Null
        return
    }

    git checkout -b $Name $FallbackBase | Out-Null
}

function Ensure-ParentDirectory {
    param([string]$Path)

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
}

function Append-HeartbeatLine {
    param([string]$Path)

    Ensure-ParentDirectory -Path $Path

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
    $line = "# save-ui heartbeat $timestamp"
    Add-Content -Path $Path -Value $line
    return $line
}

function Build-PrBody {
    param(
        [string]$Summary,
        [string[]]$Files
    )

    $changes = if ($Files.Count -gt 0) {
        ($Files | ForEach-Object { "- $_" }) -join [Environment]::NewLine
    } else {
        "- $TargetFile"
    }

    return @"
## Summary
$Summary

## Changes
$changes
"@
}

Require-Command git
Require-Command gh

Ensure-PrePushHook

git fetch origin --prune | Out-Null
Ensure-Branch -Name $Branch -FallbackBase "origin/$BaseBranch"

$lineAdded = Append-HeartbeatLine -Path $TargetFile

if (-not $CommitMessage) {
    $suffix = Get-Date -Format "yyyyMMdd-HHmmss"
    $CommitMessage = "chore: save-ui heartbeat $suffix"
}

git add -- $TargetFile

$stagedFiles = git diff --cached --name-only
if (-not $stagedFiles) {
    throw "No staged changes found after updating $TargetFile"
}

git commit -m $CommitMessage | Out-Null
git push -u origin $Branch | Out-Null

$openPrJson = gh pr list --head $Branch --base $BaseBranch --state open --json number,url --limit 1
$openPr = $openPrJson | ConvertFrom-Json

if ($openPr.Count -gt 0) {
    Write-Host "Open PR already exists: $($openPr[0].url)"
    Write-Host "Added line: $lineAdded"
    exit 0
}

$prTitle = $CommitMessage
$prBody = Build-PrBody -Summary "Append a save-ui heartbeat line to keep branch activity moving." -Files $stagedFiles
$prUrl = gh pr create --base $BaseBranch --head $Branch --title $prTitle --body $prBody

Write-Host "Created PR: $prUrl"
Write-Host "Added line: $lineAdded"
