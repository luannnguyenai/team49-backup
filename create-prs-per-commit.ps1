$baseBranch = "main"
$sourceBranch = "deploy-plan"
$remote = "origin"
$progressFile = ".pr-cherry-pick-progress.json"

# Paste list từ git cherry -v vào đây
$commitLines = @"
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

# 64ca37321bba7bbc8f13781272bba4e7db3c59ff Update 01-environment.md
# + 677eb109a36570e9358a4a71cb0b07def2cf4724 Update 05-serving-vllm.md
# + 7c3242fe57f49788609052a892f17d566974ea27 Update 06-codebase-changes.md
# + 6426a1774d18d43e9bda36fe442798d262014ca7 Update 07-rollout.md
# + a941dc16e8d706f8833546cd7762e2506ad0c20c Update datasets.md
# + e38ae0134a56b981c1d154059a8b890a6e748236 Update README.md
# + 95b6b4aa189884158aeab78e27f27b7e721dbe07 Update PIPELINE.md
# + 64ca37321bba7bbc8f13781272bba4e7db3c59ff Update 01-environment.md
# + 6426a1774d18d43e9bda36fe442798d262014ca7 Update 07-rollout.md
# + a941dc16e8d706f8833546cd7762e2506ad0c20c Update datasets.md
# + e38ae0134a56b981c1d154059a8b890a6e748236 Update README.md
# + 95b6b4aa189884158aeab78e27f27b7e721dbe07 Update PIPELINE.md
# + 64ca37321bba7bbc8f13781272bba4e7db3c59ff Update 01-environment.md
# + e38ae0134a56b981c1d154059a8b890a6e748236 Update README.md
# + 95b6b4aa189884158aeab78e27f27b7e721dbe07 Update PIPELINE.md
# + 64ca37321bba7bbc8f13781272bba4e7db3c59ff Update 01-environment.md
# + 64ca37321bba7bbc8f13781272bba4e7db3c59ff Update 01-environment.md
# + b2605cef4f26251a9b8ef122f2a55707ee10ffd5 Update 03-finetune.md
# + 8cc193f52489c1f19328537378be2f95adcd20bb Update 05-serving-vllm.md
# + 7e2c0a32dbd75eb7453ffc35fe08e2be99f9dcdd Update 06-codebase-changes.md
# + 8cc193f52489c1f19328537378be2f95adcd20bb Update 05-serving-vllm.md
# + 7e2c0a32dbd75eb7453ffc35fe08e2be99f9dcdd Update 06-codebase-changes.md
# + 7e2c0a32dbd75eb7453ffc35fe08e2be99f9dcdd Update 06-codebase-changes.md
# + 9d83b3a5c57fcf384645f986d452447158fc6cf5 Update 07-rollout.md
# + 84a2d2d97eb3c1b293647ef5670cbdaf07df2258 Update README.md
# + fb3c2fd38b27e73d98b3e6764b904de9031d7d26 Update PROPOSAL.md
# + 423bc27800d459add240716025f7dd190fe366bd Update LearningUnitShell.tsx
# + 332c710c82f595e3e990a8828944d863c16aaf9c Update unit.test.tsx
# + 5127b737cb241386ebcebeb39c76dc0a54e14aa7 Update .env.production.example
# + bca348a5cc72cc47bde854508631a340cc423e5a Delete BACKUP_RESTORE_RUNBOOK.md
# + 679b6d92bc8eb87a57f4bd612c8abe9f50bf1e28 Delete Caddyfile
# + 416155e2a1a7e3d729eabe72d2a8c076cb60001a Delete deploy.sh
# + bbca047f82e6bf5bf1bc3c0c07240d20e3f74ca9 Update DEPLOYMENT_PLAN.md
# + ac2f804b49202e27795a34d938a1e516682f34c7 Update ENVIRONMENT_MATRIX.md
# + 7711ef8a6a3f6b39b7742a484ffc2f52b5c1369e Delete nginx.conf
# + f4b56155e1e8650ed3f16c70b8c74da7ea04c1c9 Update PRODUCTION_CHECKLIST.md
# + ca3b284a4d55cdbbedc09ebb9da1edff28932317 Create railway.toml
# + d84a8ad222a7322cf666549a91ca4ba0a589f48d Update README.md
# + 9a2b4e736753b2f8e519e076d641cb96c77fc8c5 Update PIPELINE.md
# + e8c6fdf75c6aaaf3c1b8a301c3341f73268cc518 Update 02-data-pipeline.md
# + 0e22a7b49f88e18fdcebf4a9e3dfe2a1d84e8d13 Update README.md
# + e4497ee672663b20b8576bd85e3571ab4908465e Update quiz_service.py
# + 46c4113ed5443fab9894a44c0cf4afd725b8c71f Update test_inline_video_quiz_service.py
# + ce967813b5b64207aad08ccd43dfbf4b8cfe7c05 Update test_inline_video_quiz_service.py
# + ddd2d2733d2e201130d1c4be15335deb0d0fe052 Update quiz_service.py
# + 2dbe7f92be336c609b134b134231a2c41510e1fb Update test_inline_video_quiz_service.py
# + b5d8aee0426a54042b5aaeed3b2b0d6159231e5d Update quiz_service.py
# + 55c56a22e11db7263c2781989e5243cf9641ffc3 Update test_inline_video_quiz_service.py
# + 6df3583b38d1860d41abefa46e9a840227bb797a Update quiz_service.py
# + d420b11745d2d739a6a29bc8756ff505d7c86781 Update quiz_service.py
# + 198b861b23e02b5d3e85bd21532baa2f09525545 Update test_inline_video_quiz_service.py
# + 1ca66666ca0d0cfaf0ac70c18e468fcf0f158b62 Update create-prs-per-commit.ps1

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