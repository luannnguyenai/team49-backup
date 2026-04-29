$baseBranch = "main"
$sourceBranch = "ed-fix-6"
$remote = "origin"
$progressFile = ".pr-cherry-pick-progress.json"

# Paste list từ git cherry -v vào đây
$commitLines = @"
+ bdf48db07ea755d8a1e2f3debfa2c1f1dc3d5096 Delete search_box.md
+ 53d595f6f05fa73c3d2596b6aac09b39ceefc188 Create redesign.md
+ ba220c65926a0652abff8a898cef86bea8085772 Update redesign.md
+ 41e38c4dcd68eb8dcafc63faa9f3d5fc29ae1701 Create button-theme.test.tsx
+ 46f42dea9957ce02f7fc0aca1318754a0849c087 design: add semantic brand tokens and tailwind utilities
+ 835cf1f664323ffaeb13523c0c0539fc4330fc70 design: re-theme shared ui primitives with semantic utilities
+ f9c68857f853fdb29db95adc9a90dccba286ee65 design: align navigation shells with semantic brand utilities
+ 0c80531b318588c721c7cac0e43006d126e33e93 design: refresh status badge presentation without changing semantics
+ 6642d50e840024976cf599028c92b771defd0f88 design: converge landing neutrals with shared color system
+ 372c91e562647b73f686f7c60bbbf7022fa45e29 design: repaint dashboard with semantic color utilities
+ 670f726e948eeb9d2c47bb29f215f18df0ba8558 design: repaint tutor profile and history with semantic utilities
+ 72fbdc1e37406bebf94b782eb9463d9a7577af5f docs: finalize phase 1 color-system rebrand plan
+ 2ff59fed36b25445e1a939cb1e7e01f6dc8a96ca fix button learning transfer
+ fc6caef762cb3cfa03b06707b3bfa0eb4a6c4cf5 Update LearningUnitDrawer.tsx
+ 01c803fecf7af32a2e2686638299f4eaf6af1db3 fix width sync
+ 683ed70b4815bbdb3037c823b8930d7bbd9078c6 Update tailwind.config.ts
+ 1b28a03e311191d4958b1106d87c7a6b63d78875 Update PIPELINE.md
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
    Write-Host "Conflict remained. Trying forced incoming changes..." -ForegroundColor Yellow

    git checkout --theirs .
    git add .
    git cherry-pick --continue

    if ($LASTEXITCODE -ne 0) {
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