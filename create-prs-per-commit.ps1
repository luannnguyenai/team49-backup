$baseBranch = "main"
$sourceBranch = "deploy-plan"
$remote = "origin"
$progressFile = Join-Path ".git" "pr-cherry-pick-progress.json"
# Paste list từ git cherry -v vào đây
$commitLines = @"
+ 887168eea021d7eeac866acb648c7227a0c519b1 Update start.sh
+ dd266d5e152945435a4812a074c9573c90555358 Update uv.lock
+ 715696b4588a39bfc69e37257a9e69fa5a44c5fb Update InContextTutor.tsx
+ bf79d3f6fbbbdabbafcfe0a8cd2a35bb88a20026 Update LearningUnitShell.tsx
+ 887168eea021d7eeac866acb648c7227a0c519b1 Update start.sh
+ dd266d5e152945435a4812a074c9573c90555358 Update uv.lock
+ 715696b4588a39bfc69e37257a9e69fa5a44c5fb Update InContextTutor.tsx
+ bf79d3f6fbbbdabbafcfe0a8cd2a35bb88a20026 Update LearningUnitShell.tsx
+ 95ebefc3771ed459647777dd38e12494e9e42cbf Update tutorSessionHistory.ts
+ b5f5cf5f985d21c6df9a65753191092544bcf83b Update unit.test.tsx
+ 9e44c8aa4ffe3fa0f13810c75da28295474e3e97 Create Eval-Qwen25VL-Adapters.ipynb
"@



# + 715696b4588a39bfc69e37257a9e69fa5a44c5fb Update InContextTutor.tsx
# + bf79d3f6fbbbdabbafcfe0a8cd2a35bb88a20026 Update LearningUnitShell.tsx
# + 95ebefc3771ed459647777dd38e12494e9e42cbf Update tutorSessionHistory.ts
# + b5f5cf5f985d21c6df9a65753191092544bcf83b Update unit.test.tsx
# + 9e44c8aa4ffe3fa0f13810c75da28295474e3e97 Create Eval-Qwen25VL-Adapters.ipynb
# + 95ebefc3771ed459647777dd38e12494e9e42cbf Update tutorSessionHistory.ts
# + b5f5cf5f985d21c6df9a65753191092544bcf83b Update unit.test.tsx
# + 9e44c8aa4ffe3fa0f13810c75da28295474e3e97 Create Eval-Qwen25VL-Adapters.ipynb
# + 9e44c8aa4ffe3fa0f13810c75da28295474e3e97 Create Eval-Qwen25VL-Adapters.ipynb
# + 53e68f094f334bef540aaa8e3ccd1093b31cac63 Update page.tsx
# + 29cf9a529ba4bd76cb86c0a541dac59e4f7fd5e9 Update page.tsx
# + cfff12b1ff03fc2c0d41e4f6f2fafca183c44705 Update page.tsx
# + b669b914fc7e9819c529d2698702396b0842fcea Update page.tsx
# + 53e68f094f334bef540aaa8e3ccd1093b31cac63 Update page.tsx
# + 29cf9a529ba4bd76cb86c0a541dac59e4f7fd5e9 Update page.tsx
# + cfff12b1ff03fc2c0d41e4f6f2fafca183c44705 Update page.tsx
# + b669b914fc7e9819c529d2698702396b0842fcea Update page.tsx
# + 29cf9a529ba4bd76cb86c0a541dac59e4f7fd5e9 Update page.tsx
# + cfff12b1ff03fc2c0d41e4f6f2fafca183c44705 Update page.tsx
# + b669b914fc7e9819c529d2698702396b0842fcea Update page.tsx
# + 0f5b47121d0d7fd51df2b7959a1208433637af20 Update KpiCard.tsx
# + 8fb4c906f285a95f94caa785414a8429233717cf Update InContextTutor.tsx
# + 5f9c3ecf26223793aba821fc142a6b0cfc0d75b2 Update admin-api.ts
# + 0f5b47121d0d7fd51df2b7959a1208433637af20 Update KpiCard.tsx
# + 8fb4c906f285a95f94caa785414a8429233717cf Update InContextTutor.tsx
# + 5f9c3ecf26223793aba821fc142a6b0cfc0d75b2 Update admin-api.ts
# + 8fb4c906f285a95f94caa785414a8429233717cf Update InContextTutor.tsx
# + 5f9c3ecf26223793aba821fc142a6b0cfc0d75b2 Update admin-api.ts
# + 1b1330252830282c1b9303af504122cb8fcf1445 Update tutorSessionHistory.ts
# + 94238aa86376aa139c9a1fea983feeb16ae96966 Create llm.test.tsx
# + 5f9c3ecf26223793aba821fc142a6b0cfc0d75b2 Update admin-api.ts
# + 1b1330252830282c1b9303af504122cb8fcf1445 Update tutorSessionHistory.ts
# + 94238aa86376aa139c9a1fea983feeb16ae96966 Create llm.test.tsx
# + cba31f1a0f28c2e9143fb929589dda3f6ad187ce Update unit.test.tsx
# + f337bd5e4007bccbfd022a1b938f7e1025d74f58 Update in-context-tutor.test.tsx
# + 1e4e54896b298b023237e907d56f46b3868e19e8 Update app.py
# + 9e94e275e7a9f2a0625d97ee2dfce2af37ffa742 Update observability.py
# + 0cbfb6708567120e3340d4a5a26fa7c70b63121b Update admin.py
# + 1b1330252830282c1b9303af504122cb8fcf1445 Update tutorSessionHistory.ts
# + 94238aa86376aa139c9a1fea983feeb16ae96966 Create llm.test.tsx
# + cba31f1a0f28c2e9143fb929589dda3f6ad187ce Update unit.test.tsx
# + f337bd5e4007bccbfd022a1b938f7e1025d74f58 Update in-context-tutor.test.tsx
# + 1e4e54896b298b023237e907d56f46b3868e19e8 Update app.py
# + 9e94e275e7a9f2a0625d97ee2dfce2af37ffa742 Update observability.py
# + 0cbfb6708567120e3340d4a5a26fa7c70b63121b Update admin.py
# + cba31f1a0f28c2e9143fb929589dda3f6ad187ce Update unit.test.tsx
# + f337bd5e4007bccbfd022a1b938f7e1025d74f58 Update in-context-tutor.test.tsx
# + 1e4e54896b298b023237e907d56f46b3868e19e8 Update app.py
# + 9e94e275e7a9f2a0625d97ee2dfce2af37ffa742 Update observability.py
# + 0cbfb6708567120e3340d4a5a26fa7c70b63121b Update admin.py
# + f337bd5e4007bccbfd022a1b938f7e1025d74f58 Update in-context-tutor.test.tsx
# + 1e4e54896b298b023237e907d56f46b3868e19e8 Update app.py
# + 9e94e275e7a9f2a0625d97ee2dfce2af37ffa742 Update observability.py
# + 0cbfb6708567120e3340d4a5a26fa7c70b63121b Update admin.py
# + 39d0f3c652c8be1cbdcfd296c164dd830c71c37f Update llm_service.py
# + e5d29482dec8803f6bf9272c4a6303086440c326 Create test_admin_routes.py
# + 32368fd451d35bd95602e0c13af77dac0a74ff7e Update test_lecture_routes.py
# + 0121980a35cf5de9bff7be4abc016729433a7587 Create test_tutor_observability.py
# + 39d0f3c652c8be1cbdcfd296c164dd830c71c37f Update llm_service.py
# + e5d29482dec8803f6bf9272c4a6303086440c326 Create test_admin_routes.py
# + 32368fd451d35bd95602e0c13af77dac0a74ff7e Update test_lecture_routes.py
# + 0121980a35cf5de9bff7be4abc016729433a7587 Create test_tutor_observability.py
# + 0121980a35cf5de9bff7be4abc016729433a7587 Create test_tutor_observability.py

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