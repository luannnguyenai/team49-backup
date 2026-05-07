$baseBranch = "main"
$sourceBranch = "deploy-6 "
$remote = "origin"
$progressFile = Join-Path ".git" "pr-cherry-pick-progress.json"
# Paste list từ git cherry -v vào đây
$commitLines = @"
+ abeba6858d7582aeead9ac21a5ce150abb290c54 Update page.tsx
+ ee41381c5661fc3f24544ceda8e720204636889f Update PrerequisiteSuggestionDialog.tsx
+ 31e383c9074b0577bc4e067b4a8d5717c941fd8d Update ReplanKnowledgeClaimStep.tsx
+ 384a5a1552c2a80f86bb559ded4410f9fa8f86de Update admin-tooltips.ts
+ 20bf4ef6015e453f912a522878f2da1423bb0a5a Update page.tsx
+ 38f1b919c451b75982d64438b60d934843c93387 Update TopNav.tsx
+ d398fca67729c4444abbcf537f8bb73b40ac210b Update page.tsx
+ 3d8742659116000ffa4fa6021188f24cd941c418 Update InContextTutor.tsx
+ e45c59f66b69a94603c028a2e96d9f71a72e9dd9 Update next.config.mjs
+ 4ca2df9247016d50d4deb85c4622d1fab5d20261 Update app.py
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