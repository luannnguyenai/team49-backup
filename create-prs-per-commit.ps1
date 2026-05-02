$baseBranch = "main"
$sourceBranch = "deploy-plan"
$remote = "origin"
$progressFile = ".pr-cherry-pick-progress.json"

# Paste list từ git cherry -v vào đây
$commitLines = @"
+ fd2a364d8c3368a23fecbc4697470ec1ccd7caaf Delete DESIGN_SUMMARY.md
+ 234bb49670797808d3259206f6dd8980a819a244 Delete opus-review.md
+ 9620e56113f18aeeabea19f7507e182cdb27c00a Delete PLAN.md
+ 0b81acf6e98b7d4742e82b82946e61d026df16a9 Delete .gitkeep
+ 519cc11343453fcab414e1370f6ac321ab3aace7 Create DEPLOYMENT_PLAN.md
+ dd215cb56e48e658fc47177298541018e8bcc605 Create ENVIRONMENT_MATRIX.md
+ 4b9bb9f561b1aa3383896494f384252a16b2ccdf Create PRODUCTION_CHECKLIST.md
+ 7bb814d1696ae198fe73411ee24ddcc524d7ae51 Create README.md
+ 8f7cbca7dc7c7adc27660cf60115e0c373bd1095 Create .env.production.example
+ 5e0b6e4835cb903391e0a000ca6ed7f5e7df3460 Create BACKUP_RESTORE_RUNBOOK.md
+ b17e727bf8d70c0f5113c869450351a5ae8f7552 Create Caddyfile
+ dc769aea4a16674459421ec0f4f4010afe153838 Create deploy.sh
+ 115e857e18d794fca86320b04569d00ec6b1568f Update Caddyfile
+ dcd9f695e674ac230a7bf3917938f1ff667e5e54 Create nginx.conf
+ 336c66442b90ed2670d3e602777891363aceaa25 Update PRODUCTION_CHECKLIST.md
+ 471bbec8b6027cef6e0691a8ca74ad5ccba345c7 Update ENVIRONMENT_MATRIX.md
+ d84ea034ddccf8fddeb486140d9141e3ef7d0645 Update DEPLOYMENT_PLAN.md
+ 10c20e5e6f1f9ea18b9e8dc69038a1539ad49cce Update README.md
+ c5061602ff8c9fba5139f30530a5903b9f7eed82 Update FinetuneLoRA-2.ipynb
+ 0d46135e41f1e04992e0a653b7db35bc2f9f21e7 Update PIPELINE.md
+ e4b40f9e33caa4eb82d9c389eeb19d1975749da5 Create 01-environment.md
+ 1eb56286806a38da85113afaffd4ffa7ae81a1f1 Create 02-data-pipeline.md
+ 16e8d6a7f3c37454f697f053815a893e51f7a156 Create 03-finetune.md
+ 753aeaa0a2f55515d594d8f164198ebb0081caae Update 04-eval-quantize.md
+ 677eb109a36570e9358a4a71cb0b07def2cf4724 Update 05-serving-vllm.md
+ 7c3242fe57f49788609052a892f17d566974ea27 Update 06-codebase-changes.md
+ 6426a1774d18d43e9bda36fe442798d262014ca7 Update 07-rollout.md
+ a941dc16e8d706f8833546cd7762e2506ad0c20c Update datasets.md
+ e38ae0134a56b981c1d154059a8b890a6e748236 Update README.md
+ 95b6b4aa189884158aeab78e27f27b7e721dbe07 Update PIPELINE.md
+ 64ca37321bba7bbc8f13781272bba4e7db3c59ff Update 01-environment.md
+ 1eb56286806a38da85113afaffd4ffa7ae81a1f1 Create 02-data-pipeline.md
+ 16e8d6a7f3c37454f697f053815a893e51f7a156 Create 03-finetune.md
+ 753aeaa0a2f55515d594d8f164198ebb0081caae Update 04-eval-quantize.md
+ 677eb109a36570e9358a4a71cb0b07def2cf4724 Update 05-serving-vllm.md
+ 7c3242fe57f49788609052a892f17d566974ea27 Update 06-codebase-changes.md
+ 6426a1774d18d43e9bda36fe442798d262014ca7 Update 07-rollout.md
+ a941dc16e8d706f8833546cd7762e2506ad0c20c Update datasets.md
+ e38ae0134a56b981c1d154059a8b890a6e748236 Update README.md
+ 95b6b4aa189884158aeab78e27f27b7e721dbe07 Update PIPELINE.md
+ 64ca37321bba7bbc8f13781272bba4e7db3c59ff Update 01-environment.md
+ 753aeaa0a2f55515d594d8f164198ebb0081caae Update 04-eval-quantize.md
+ 677eb109a36570e9358a4a71cb0b07def2cf4724 Update 05-serving-vllm.md
+ 7c3242fe57f49788609052a892f17d566974ea27 Update 06-codebase-changes.md
+ 6426a1774d18d43e9bda36fe442798d262014ca7 Update 07-rollout.md
+ a941dc16e8d706f8833546cd7762e2506ad0c20c Update datasets.md
+ e38ae0134a56b981c1d154059a8b890a6e748236 Update README.md
+ 95b6b4aa189884158aeab78e27f27b7e721dbe07 Update PIPELINE.md
+ 
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