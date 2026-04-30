$baseBranch = "main"
$sourceBranch = "ed-fix-7"
$remote = "origin"
$progressFile = ".pr-cherry-pick-progress.json"

# Paste list từ git cherry -v vào đây
$commitLines = @"
+ 51db8a27c4b15e5deefc0fcb47adfc4c778a9a7d translate(learning-path-empty-state): convert empty state UI copy to English
+ 01d6bfee54b8fde276e64537bffa54e675aaf855 translate(learning-unit-card): convert card fallback and recommendation copy to English
+ 618db3befca9c8003eccd2bcb8824a64dacc35d4 translate(path-required-state): convert missing-path prompt UI copy to English
+ b9694243141937af39ad3c0164745387f920b7c9 translate(profile-change-banner): convert profile change banner UI copy to English
+ 97c6c875c0650f8ef08a0d87776f15cfc8957876 translate(planner-header): convert planner header and path switcher UI copy to English
+ f8e665d36dbf27344c240e4f5e57318e011168b6 translate(learning-path-status): convert shared learning path status labels to English
+ ff02973b9de11b96bc891997141ddab78ba00da1 translate(roadmap-node-card): convert recommendation badge copy to English
+ 8ee05808b07901a75cb58aa17be058274771112d translate(timeline-board): convert weekly timeline UI copy to English
+ ea17f6407cd0c4513059eb613709a49eab9aedac translate(learning-path-shell): convert shell error action copy to English
+ ebc493b262a1d0fdfb226562dc4e43438b7fe028 translate(learning-unit-drawer): convert drawer UI copy and CTA labels to English
+ 8c7548dc20400adf16d94af1c7d7f4de684863da translate(learning-path-duration): convert shared duration labels to English

"@

# + 4351ccacbba7a2ca9ad1ac18be05d46145e1be52 translate(learning-path-profile): convert profile change summary copy to English
# + ac37bd3069ab204c5a1d5250434dc8b34df8392d translate(player-insights): convert roadmap insight labels to English
# + ea7b8251799f2ec81f07727cd4debc68a2329e38 translate(learning-path-store): convert shared store error copy to English
# + 0a69a11aebabb16ee5b45348e64e0b131bc9c483 translate(roadmap-model): convert roadmap fallback and subtitle copy to English
# + c088b7e196801a7feeb3702a0ece054d8d87ba1b translate(learning-path-presenters): convert presenter fallback copy to English
# + 371d692d259d2d7e37cc8a0943a9271c56b09396 translate(planner-reasons): convert roadmap reason descriptions to English
# + adda4a49484eea9336e2103ffed231d60679fd06 translate(roadmap-planner): convert lecture fallback copy to English
# + 4b4a539fd357d29fd991fee91619272f972452eb ui(assessment-page): align assessment page width with onboarding layout
# + 67ac0a416b17f95e5d36820674701a432934bc7c Update page.tsx
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