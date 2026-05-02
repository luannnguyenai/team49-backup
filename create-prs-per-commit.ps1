$baseBranch = "main"
$sourceBranch = "deploy-plan"
$remote = "origin"
$progressFile = ".pr-cherry-pick-progress.json"

# Paste list từ git cherry -v vào đây
$commitLines = @"
+ 4351ccacbba7a2ca9ad1ac18be05d46145e1be52 translate(learning-path-profile): convert profile change summary copy to English
+ ac37bd3069ab204c5a1d5250434dc8b34df8392d translate(player-insights): convert roadmap insight labels to English
+ ea7b8251799f2ec81f07727cd4debc68a2329e38 translate(learning-path-store): convert shared store error copy to English
+ 0a69a11aebabb16ee5b45348e64e0b131bc9c483 translate(roadmap-model): convert roadmap fallback and subtitle copy to English
+ c088b7e196801a7feeb3702a0ece054d8d87ba1b translate(learning-path-presenters): convert presenter fallback copy to English
+ 371d692d259d2d7e37cc8a0943a9271c56b09396 translate(planner-reasons): convert roadmap reason descriptions to English
+ adda4a49484eea9336e2103ffed231d60679fd06 translate(roadmap-planner): convert lecture fallback copy to English
+ 4b4a539fd357d29fd991fee91619272f972452eb ui(assessment-page): align assessment page width with onboarding layout
+ 67ac0a416b17f95e5d36820674701a432934bc7c Update page.tsx
+ 1f043743d00a03b10f1e2adb5e4b0596b87ecadd Create PROPOSAL.md
+ 6e2ccc32bbbb3a448fb511a2b19cc69d82165b09 Update PROPOSAL.md
+ 2262bbd5aa9f96a8db9a838813472d6f2741b541 Update PROPOSAL.md
+ 3c76871d4b75cd739cadb3d038a9710b373c08a3 fix search 10
+ b4825a4f31e3577bb48e810c4a4f35ba318db55b Update unit.test.tsx
+ 203fc8a6adbb7ea699b60a628ef4f4aa0c1341d7 fix search 11
+ b9e92fce427f6ad57a7ad8a0ca9ace7afcaeb9ce fix search 12
+ 9a8f95e097ad040410fb5cd2b5f5f74d4e30c7a5 add back button
+ 5d56a0e91425c53ff155749e538a3f5e87dc71e0 add back to home
+ d0acf851191203c0da5244ebbfb0aa05452b2348 update copywriting
+ 6292e916bbe8d28ff1da1105348e776dfe200a78 fix tab name browser
+ 9a4924c195bcc37299edd9d7bca6588a2d179eb3 Update app-metadata.test.ts
+ 0d4488ed65d7b91244ed52c31bf97354e2b9c7ee Update page.tsx
+ 599df49c004d9acfdb6f0ada3bb37ae17e9d4a67 update page name navigation
+ fe3381c2fa5a742bfcbc152cc14a6c9ed3f353a5 update navigation name 1
+ 5a29a0ce503d33158984e485cd643d57870703e9 Update page.tsx
+ eb22a645777992768bf702239ebc061ee03c5a62 Update page.tsx
+ 14cd548355c7a706c225abc594b52fe135f23993 Update page.tsx
+ 410091708ec701013e066baefae6459c83128726 Update page.tsx
+ ca1f33a231a42fd9afc6a34808c4087063b4887c Update page.test.tsx
+ 9dda363c1c92c369c9d3fee891e772107a3d7b5d Update page.tsx
+ 0eeb72576b04e9911196421a1c155e945a50f235 Update page.test.tsx
+ 8cfc758db7b726553c7a6d6aa086293b11b21178 Update page.tsx
+ 5a2dfe10dc1cfa152bf7f6d017807499689c2d4e Update create-prs-per-commit.ps1
+ 0a8ec5239cceab82c94b007f52d8d78c0c224690 Update page.tsx
+ 39004c242756d0183e5fe4c62a469aacb8d1efe4 Update page.test.tsx
+ 3dbb345cc03a23fc27ab2263bba02510f9380ddc Update unit.test.tsx
+ 3418269c694c0574282f4f4861ecc9d1ac270c79 Update LearningUnitShell.tsx
+ 5055e70a671b7fd4644a67cf604727f7723824d4 Update unit.test.tsx
+ f56d9bde525b184b61157ad8006d122ac6e021b1 Update LearningUnitShell.tsx

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
# + 1f043743d00a03b10f1e2adb5e4b0596b87ecadd Create PROPOSAL.md
# + 6e2ccc32bbbb3a448fb511a2b19cc69d82165b09 Update PROPOSAL.md
# + 2262bbd5aa9f96a8db9a838813472d6f2741b541 Update PROPOSAL.md
# + 3c76871d4b75cd739cadb3d038a9710b373c08a3 fix search 10
# + b4825a4f31e3577bb48e810c4a4f35ba318db55b Update unit.test.tsx
# + 203fc8a6adbb7ea699b60a628ef4f4aa0c1341d7 fix search 11
# + b9e92fce427f6ad57a7ad8a0ca9ace7afcaeb9ce fix search 12
# + 9a8f95e097ad040410fb5cd2b5f5f74d4e30c7a5 add back button
# + 5d56a0e91425c53ff155749e538a3f5e87dc71e0 add back to home
# + d0acf851191203c0da5244ebbfb0aa05452b2348 update copywriting
# + 6292e916bbe8d28ff1da1105348e776dfe200a78 fix tab name browser
# + 9a4924c195bcc37299edd9d7bca6588a2d179eb3 Update app-metadata.test.ts
# + 0d4488ed65d7b91244ed52c31bf97354e2b9c7ee Update page.tsx
# + 599df49c004d9acfdb6f0ada3bb37ae17e9d4a67 update page name navigation
# + fe3381c2fa5a742bfcbc152cc14a6c9ed3f353a5 update navigation name 1
# + 5a29a0ce503d33158984e485cd643d57870703e9 Update page.tsx
# + eb22a645777992768bf702239ebc061ee03c5a62 Update page.tsx
# + 14cd548355c7a706c225abc594b52fe135f23993 Update page.tsx
# + 410091708ec701013e066baefae6459c83128726 Update page.tsx
# + ca1f33a231a42fd9afc6a34808c4087063b4887c Update page.test.tsx
# + 9dda363c1c92c369c9d3fee891e772107a3d7b5d Update page.tsx
# + 0eeb72576b04e9911196421a1c155e945a50f235 Update page.test.tsx
# + 8cfc758db7b726553c7a6d6aa086293b11b21178 Update page.tsx

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