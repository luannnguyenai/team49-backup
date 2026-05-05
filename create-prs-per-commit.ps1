$baseBranch = "main"
$sourceBranch = "deploy-3"
$remote = "origin"
$progressFile = Join-Path ".git" "pr-cherry-pick-progress.json"
# Paste list từ git cherry -v vào đây
$commitLines = @"
+ d24edce891a8aab4b358657bd7c0e9a2c73deda7 Update AGENTS.md
+ 9f16e7f65da47d1ce2fec5b789e3edb45cf86b1c Update page.tsx
+ f3b53fc594640a43909366c87dada5bcd79b96dd Update layout.tsx
+ 65b46b39d04046801d71c15b5e719011e4c76bc3 Update page.tsx
+ b8c049b3d6ac06f17f7e3079fa0f37de585da707 Update page.tsx
+ 9c0c9c0fb753d86114a77e5bef32fb352f97e0eb Update page.tsx
+ c9660531f4da30868c8cf365edfd240eefcc43d6 Update page.tsx
+ 4aee4cc72017db8b2077fa2e013cb57e9b1906ef Update page.tsx
+ b03bcd77df133bcddfeceb0a36880a844175ec31 Update page.tsx
+ 8b24f13f8b7f0c8cfcbfa7b4a4fd5b0a0f07cfe7 Update page.tsx
+ 3576a27b5445db893f3c3743c7a05497dc1a0f23 Update page.tsx
+ b7197d5a11e100b0c655a0731b6360e6b3f8345c Update page.tsx
+ d618d2f819bad586f957acadc8a3e03900f5be8e Update page.tsx
+ bcd337a60624d9f5cf5f6694e8e18895a7363684 Update page.tsx
+ add707d1974c0b71c97193c643154f39269bdc0c Update globals.css
+ eae8cb002a8d45599015f06114e10a21c67274ed Update page.tsx
+ 55904f57c8f93ea043d24d5d5ece844aa928b670 Update page.tsx
+ 90c734decc347ffbb37083e8bbdf3dacda1bbe2c Update page.tsx
+ d2124fe69881df3ff513447e6321e582a6a5ea50 Update page.tsx
+ cfe3c2c1bc6d1ac56859b905d24d32f8e0f60fd0 Update page.tsx
+ 0c416fa5dda5f238f88c3a1da03d2b9d82d2310f Update ChartCard.tsx
+ 0137e813f521443add5ebba6134103fd80b07674 Update KpiCard.tsx
+ b1608f1c82695e984fb967e4812e0763a8514a3d Update AuthBackLink.tsx
+ 1c0d5683bcd91139f01806196d639bff04513ffc Update ForgotPasswordForm.tsx
+ 853a149c07d046060342611c6af09b3a699fe0bf Update LoginForm.tsx
+ f1b94392492c04d5f678dfc1a2264dcbb278feeb Update RegisterForm.tsx
+ 399bb067334ed04587bfaf334c779f8ebc59e22e Update LandingPage.tsx
+ 838cc650abc12dfaa148bb2fa9d44e503a29beb2 Update PublicTopNav.tsx
+ 5a48ab3da96847726de0c222713e02a2d23e13d2 Update AgentChatPage.tsx
+ b0b7fc7599aef5c314ab9927dbbb69b868fe2d26 Create chart-theme.ts
+ 15aa24412da57d757fc3ca8a65a8fc767267e44b Update feedbackStyles.ts
+ 61d3c9c51f9856d239cb332e6dde25855ea3402d Update tailwind.config.ts
+ 20858127a6917163c22b0adc22269632fc096b54 Update page.test.tsx
+ 83b750b3adcfa82dc4f6a394615c9d233a408955 Create chart-theme.test.ts
+ 7dae8d0c45b831acde4e546b5f10d265f3f7f850 Create agent-chat-theme.test.ts
+ 54ac8a18ae9298508629db0a3453e9c8a537aeea Create bloom-badge.test.ts
+ 0c4ca018825ac5c9d02b11695e3542178d38a0d6 Create auth-pages-theme.test.tsx
+ 85125481270735d665769e4ae2596d913a0fb801 Create type-colors.test.ts
+ 00504e95783cbbe500083a2bdb766bea8a453926 Create landing-cta.test.tsx
+ 74a4e9b060b1921249205c1d45bcee78656c2c91 Create achievement-tier.test.ts
+ ca274b5a6a453bff40871c5f51c6a7320f716a62 Create decorative-tokens.test.tsx
+ e9dc8b44611a6644b814343633abfd2b844048f4 Create phase-0-retint-buttons.md
+ aff655254bb87e30e9cc6539d1f22a9505eeb825 Create phase-1-public-cta-unify.md
+ 7c3bdcf97d762341b060731ced48fd9b8d5556b0 Create phase-2-auth-pages-refactor.md
+ 99fe84c365a194e81b747983f0bef8719b4279db Create phase-3-decorative-tokens.md
+ 96a15141ec7ea13aeaecf113e21ca702a21b20ab Create phase-4-bloom-session-migrate.md
+ 0f889ad21914369c75961c7a7e832e24547e0b5a Create phase-5-admin-chart-palette.md
+ 6b0af69f63a0d9fa557cf941f1f41d39afb77978 Create README.md
+ 6b20c46865aedd75dad4e25eb0bbc2d36eddc312 Create REVIEW.md
+ 147121f4d30b970d0d3cff23a065fe39059c0b48 Update create-prs-per-commit.ps1
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