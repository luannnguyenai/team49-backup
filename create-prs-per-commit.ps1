$baseBranch = "main"
$sourceBranch = "deploy-plan"
$remote = "origin"
$progressFile = Join-Path ".git" "pr-cherry-pick-progress.json"
# Paste list từ git cherry -v vào đây
$commitLines = @"
+ 679b6d92bc8eb87a57f4bd612c8abe9f50bf1e28 Delete Caddyfile
+ 416155e2a1a7e3d729eabe72d2a8c076cb60001a Delete deploy.sh
+ bbca047f82e6bf5bf1bc3c0c07240d20e3f74ca9 Update DEPLOYMENT_PLAN.md
+ ac2f804b49202e27795a34d938a1e516682f34c7 Update ENVIRONMENT_MATRIX.md
+ 7711ef8a6a3f6b39b7742a484ffc2f52b5c1369e Delete nginx.conf
+ f4b56155e1e8650ed3f16c70b8c74da7ea04c1c9 Update PRODUCTION_CHECKLIST.md
+ d84a8ad222a7322cf666549a91ca4ba0a589f48d Update README.md
"@



# + 53e68f094f334bef540aaa8e3ccd1093b31cac63 Update page.tsx
# + 29cf9a529ba4bd76cb86c0a541dac59e4f7fd5e9 Update page.tsx
# + cfff12b1ff03fc2c0d41e4f6f2fafca183c44705 Update page.tsx
# + b669b914fc7e9819c529d2698702396b0842fcea Update page.tsx
# + 0f5b47121d0d7fd51df2b7959a1208433637af20 Update KpiCard.tsx
# + 8fb4c906f285a95f94caa785414a8429233717cf Update InContextTutor.tsx
# + 5f9c3ecf26223793aba821fc142a6b0cfc0d75b2 Update admin-api.ts
# + 1b1330252830282c1b9303af504122cb8fcf1445 Update tutorSessionHistory.ts
# + 94238aa86376aa139c9a1fea983feeb16ae96966 Create llm.test.tsx
# + cba31f1a0f28c2e9143fb929589dda3f6ad187ce Update unit.test.tsx
# + f337bd5e4007bccbfd022a1b938f7e1025d74f58 Update in-context-tutor.test.tsx
# + 1e4e54896b298b023237e907d56f46b3868e19e8 Update app.py
# + 9e94e275e7a9f2a0625d97ee2dfce2af37ffa742 Update observability.py
# + 0cbfb6708567120e3340d4a5a26fa7c70b63121b Update admin.py
# + 39d0f3c652c8be1cbdcfd296c164dd830c71c37f Update llm_service.py
# + e5d29482dec8803f6bf9272c4a6303086440c326 Create test_admin_routes.py
# + 32368fd451d35bd95602e0c13af77dac0a74ff7e Update test_lecture_routes.py
# + 0121980a35cf5de9bff7be4abc016729433a7587 Create test_tutor_observability.py
# + 41d2b12cf426f765aa1f6fee041c501a84a386d5 Update plan.md
# + 81b3ab77b005ab2a4c627d84aa830bd9913194c9 Update page.tsx
# + 674d539468ff09c21055fc32c3a5a9231192e3df update .env
# + 6ced11c8435a9c728438239d1828e1bf41b8f1fa update uv
# + 5c3799a83b94e71d756a4ab771bdfdf54935e1f9 langfuse env
# + fe7976dea9743d0699e6c149e07deff5eac35c58 setup langfuse success
# + ede5cedbabc931c050b5010b4cf5a8bcf9df6379 Update README.md
# + a659558044115ca603cf4f597ae48fba19675ccc Create 20260503_add_langfuse_trace_fields.py
# + 9fc4f91b55bcea378b3c62615cb463fe48bc2604 Update .env.production.example
# + 02a0bbcb3aaa3e770c26b70a9fbcfa487b4f6e5b Update docker-compose.yml
# + 89522913fff452a3236e885a61b4728893da2204 Create 2026-05-03-langfuse-tracing-hardening.md
# + bdb31e696eadc809a2e2e849bc14b54dc9a4e5b6 Update .env.example
# + 7ec3ed2e3a972c507aa093785b074ffc67b18436 Create page.tsx
# + 44d528fd48093a6749d0094cfa4087e4fa204244 Update page.tsx
# + 8b4ea4e953a5cd2cdd158ae1379bcc63516b000c Update page.tsx
# + c7ea89bda7e2b738f29407bc5dd487f33cc574c3 Update page.tsx
# + 8c266bfbdb0b457c8871adfc2a2a349085cb286d Update page.tsx
# + cd79a9e62437da71ec1c787f002536f65e2e1b44 Update AdminSidebar.tsx
# + 766434eda3c624f35b76f0ee96e6181c1596e8b6 update langfuse
# + b0e0faef5f337fb9f5a6a3507c5946dc818c5fd8 Create PLATFORM_ANALYSIS.md
# + e757025a56f51de0fb2f7ffb743c0d875e0c653e Create admin_test_accounts.csv
# + 49bc55c9edde6a8fe975a4b9c346d4552ec76afd Create create_seed_accounts.py
# + a88dc38b26d61bbf47e504c712b41f9853012be7 Create current-state.md
# + da9ec3022ab0c185710ff825388f22029b177102 Create create_seed_accounts.py
# + 907bc0302a494e87fb9db5f7079c083ca05d444a update plan reset password
# + b62d0d2331866ab47f39ab58e381578944599aac Create Eval-Resume-Adapters.ipynb
# + ceb8f354fdeb4a3bd4b46800bb9b40ef60e83e83 learning path improvement ux

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