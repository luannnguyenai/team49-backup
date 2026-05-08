$baseBranch = "main"
$sourceBranch = "deploy-6 "
$remote = "origin"
$progressFile = Join-Path ".git" "pr-cherry-pick-progress.json"
# Paste list từ git cherry -v vào đây
$commitLines = @"
+ ac69f1cc0e5e08f3972977f377730a403c7cbedd Create hub_registry.json
+ 05e40de75cce6c223eeefadeba70fd21e104de62 Update .env.production.example
+ 776f8183e71be668416321bb6e75f1eecd98b5dd Create AWS_CICD_GUIDE.md
+ b6c0c206bb2c88f4a15a081c7f1e3522f4d27840 Create AWS_CONFIG_GUIDE.md
+ d71fddce2ea2058608c8abffb5ec97eca38962ab Update DEPLOYMENT_PLAN.md
+ ae97a1a684141cdd9803023b27cca42cb9b894b8 Update ENVIRONMENT_MATRIX.md
+ 9bf0a34a4bf2c52248a0361f2bd0a89882819729 Update MANUAL_DEPLOY_STEPS.md
+ cb09293032eb83d4d7f47202268cb3903fc7111e Update PLATFORM_ANALYSIS.md
+ 265cb2a99ddcc3db5212d684bd0bd8e3f67ffb9f Update PRODUCTION_CHECKLIST.md
+ f4b09e11f5222aa21cb2b0b930232db60bef03f3 Delete railway.toml
+ ff758a189b5764e0b99ff94b31ce56239047a992 Update README.md
+ ff60a577b50c739a38c179cb6b24a8384b563a99 Delete RENDER_AWS_CONFIG_GUIDE.md
+ 2002809bfa1e2e82d95633b74cab8196f3471ac6 Create 2026-05-07-predeploy-remediation.md
"@







function Save-Progress {
  param(
    [string]$LastMergedCommit,
    [string]$FailedCommit
  )

  @{
    baseBranch       = $baseBranch
    sourceBranch     = $sourceBranch
    lastMergedCommit = $LastMergedCommit
    failedCommit     = $FailedCommit
    updatedAt        = (Get-Date).ToString("s")
  } | ConvertTo-Json | Set-Content $progressFile
}

function Load-Progress {
  if (Test-Path $progressFile) {
    return Get-Content $progressFile | ConvertFrom-Json
  }
  return $null
}

function Abort-InProgressGitOps {
  git cherry-pick --abort 2>$null
  git merge --abort 2>$null
  git rebase --abort 2>$null
}

Write-Host "Cleaning unfinished git operations..." -ForegroundColor Cyan
Abort-InProgressGitOps

git fetch $remote

$baseRef = "$remote/$baseBranch"

# Chỉ lấy commit có dấu +
$commits = @(
  $commitLines -split "`n" |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ -match '^\+\s+[0-9a-f]{7,40}\s+' } |
    ForEach-Object {
      ($_ -split '\s+')[1]
    }
)

if ($commits.Count -eq 0) {
  Write-Host "No unmerged commits found in provided list." -ForegroundColor Yellow
  exit 0
}

Write-Host "Commits to process:" -ForegroundColor Cyan
$commits | ForEach-Object { Write-Host "  $_" }

$progress = Load-Progress
$startIndex = 0

if ($progress -ne $null -and $progress.sourceBranch -eq $sourceBranch -and $progress.baseBranch -eq $baseBranch) {
  if ($progress.failedCommit) {
    $idx = [array]::IndexOf($commits, $progress.failedCommit)
    if ($idx -ge 0) {
      $startIndex = $idx
      Write-Host "Resuming from failed commit: $($progress.failedCommit)" -ForegroundColor Yellow
    }
  }
  elseif ($progress.lastMergedCommit) {
    $idx = [array]::IndexOf($commits, $progress.lastMergedCommit)
    if ($idx -ge 0) {
      $startIndex = $idx + 1
      Write-Host "Resuming after last merged commit: $($progress.lastMergedCommit)" -ForegroundColor Yellow
    }
  }
}

for ($i = $startIndex; $i -lt $commits.Count; $i++) {
  $commit = $commits[$i]

  Write-Host "`n=============================="
  Write-Host "Processing commit $commit"
  Write-Host "==============================" -ForegroundColor Cyan

  Save-Progress -LastMergedCommit $null -FailedCommit $commit

  git checkout $baseBranch
  if ($LASTEXITCODE -ne 0) { exit 1 }

  git pull $remote $baseBranch
  if ($LASTEXITCODE -ne 0) { exit 1 }

  $subject = git log -1 --pretty=%s $commit

  $safeName = $subject.ToLower() `
    -replace '[^a-z0-9]+','-' `
    -replace '^-|-$',''

  if ([string]::IsNullOrWhiteSpace($safeName)) {
    $safeName = "commit"
  }

  $shortCommit = $commit.Substring(0, 8)
  $branchName = "pr/$shortCommit-$safeName"

  git checkout -B $branchName $baseRef
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Cannot create branch $branchName. Rerun will resume from $commit." -ForegroundColor Red
    exit 1
  }

  git cherry-pick -X theirs $commit

if ($LASTEXITCODE -ne 0) {
  $statusText = git status 2>&1 | Out-String

  if ($statusText -match "previous cherry-pick is now empty" -or $statusText -match "nothing to commit") {
    Write-Host "Commit $commit is already applied / empty. Skipping..." -ForegroundColor Yellow
    git cherry-pick --skip 2>$null
    Save-Progress -LastMergedCommit $commit -FailedCommit $null
    continue
  }

  Write-Host "Conflict remained. Trying forced incoming changes..." -ForegroundColor Yellow

  git checkout --theirs .
  git add .
  git cherry-pick --continue

  if ($LASTEXITCODE -ne 0) {
    $statusText = git status 2>&1 | Out-String

    if ($statusText -match "previous cherry-pick is now empty" -or $statusText -match "nothing to commit") {
      Write-Host "Commit $commit became empty after conflict resolution. Skipping..." -ForegroundColor Yellow
      git cherry-pick --skip 2>$null
      Save-Progress -LastMergedCommit $commit -FailedCommit $null
      continue
    }

    Write-Host "Cannot auto-resolve commit $commit. Rerun will resume from this commit." -ForegroundColor Red
    Save-Progress -LastMergedCommit $null -FailedCommit $commit
    exit 1
  }
}

  git push -u $remote $branchName --force
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Push failed for $branchName. Rerun will resume from $commit." -ForegroundColor Red
    exit 1
  }

  gh pr create `
    --base $baseBranch `
    --head $branchName `
    --title "$subject" `
    --body "Auto cherry-pick commit $commit from $sourceBranch into $baseBranch."

  if ($LASTEXITCODE -ne 0) {
    Write-Host "PR create failed. Maybe PR already exists. Continuing to merge..." -ForegroundColor Yellow
  }

  gh pr merge $branchName --merge --delete-branch

  if ($LASTEXITCODE -ne 0) {
    Write-Host "Merge failed for $branchName. Rerun will resume from $commit." -ForegroundColor Red
    Save-Progress -LastMergedCommit $null -FailedCommit $commit
    exit 1
  }

  Write-Host "Merged $commit successfully." -ForegroundColor Green

  Save-Progress -LastMergedCommit $commit -FailedCommit $null
  git fetch $remote
}

git checkout $baseBranch
git pull $remote $baseBranch

Remove-Item $progressFile -ErrorAction SilentlyContinue

Write-Host "`nAll provided unmerged commits processed and merged." -ForegroundColor Green