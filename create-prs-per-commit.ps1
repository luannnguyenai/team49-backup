$baseBranch = "main"
$sourceBranch = "ed-fix-7"
$remote = "origin"
$progressFile = ".pr-cherry-pick-progress.json"

# Paste list từ git cherry -v vào đây
$commitLines = @"
+ 41d29bbd25e88aa6906dedd198a3d3371f65456e change languaugge
+ bafddf9e4ac64063c688c7d6b69d62bef5c1d07f translate(landing-page): convert LandingPage UI copy to English
+ 490e063d82b619d088ee957646833d364d75687f translate(tutor-page): convert tutor hub UI copy to English
+ c0692ed0e13c64e0f4ae6284b4257a3ee1c462aa translate(course-catalog): convert CourseCatalog UI copy to English
+ 325445869b9241ec2b0a86d6ad3cdac22b99a504 translate(course-overview): convert CourseOverview UI copy to English
+ acb0e40c46b0704d999483b9641260d89f78e4ea translate(mock-course-catalog): convert coming-soon catalog copy to English
+ 4c2c7da0b4c6f4eac45be79ea5772851a1f89d53 translate(dashboard-presenters): convert dashboard card copy to English
+ 5a2e12131cab80188d545a8496155bd0f69a64fc translate(dashboard-page): convert dashboard screen UI copy to English
+ 65673aa03d63d11c56ca3efb3cfab9eca3584151 translate(profile-page): convert profile screen UI copy to English
+ 375b4213c3aa175ee746380e567c55f97dcf5b45 translate(history-page): convert learning history screen UI copy to English
+ 475244a193521e0c0e8de7ad07a07439823243a3 translate(step-goal-selection): convert onboarding goal step copy to English
+ b824b3a049ae954777bff4b230f6fc7970ec46ef translate(step-assessment-depth): convert onboarding assessment depth copy to English
+ b8a7233a29772dcf40dc16ffd3e19133083a152a translate(step-prior-knowledge-input): convert onboarding prior knowledge step copy to English
+ a0cb94e385b8c1d7f2f141e598344e0af85bfab1 translate(step-experience-level): convert onboarding experience step copy to English
+ a3b205237bac6e6b50400bdc6303020f1f1d8c0b translate(step-desired-sections): convert onboarding course selection step copy to English
+ cc7960916fc0497e2b5efb606b8a8a1bb7f3a40d translate(step-known-units): convert onboarding known topics step copy to English
+ 53805a46cd40f71c662921a0e717e17dcc8786f5 translate(step-known-topics-filtered): convert onboarding topic confirmation step copy to English
+ 8a9a74dcbbc6b21562d9ad1c9985283c288848bf translate(onboarding-page): convert onboarding wizard shell copy to English
+ 381a8865d3231b9650f1b27f9ce55e1591a6af1a translate(in-context-tutor): convert tutor chat and status copy to English
+ c0bd2e25f97be4c4392b9cd9a82d2cd1256f5ee3 translate(learning-unit-shell): convert lesson shell, quiz overlay, and timestamp copy to English
+ 4a26db4f5ef82a5e89862241e267884c5b70160d translate(assessment-page): convert assessment flow UI copy to English
+ fbdcbbc200ba6dc26fbfdd5c7bbe2dfbd0d1ad02 translate(assessment-results-page): convert assessment results UI copy to English
+ 7ce487aa0d89e2cb0b94deabccf3f3b62fcc2bde translate(learn-page): convert learning path page title to English
+ 387c2fd1be60f0a220b88e76c122902dc8b7bdde translate(quiz-page): convert quiz flow UI copy to English
+ c13434e584d4f2d8fea695e38e39571bc0d50ae3 translate(quiz-results-page): convert quiz results UI copy to English
+ 2a59c951e4cb5982eaa97035966876e5fe1a787a translate(learn-unit-page): convert learning unit content UI copy to English
+ b464614af3c2a0e32c7efd8e67a7696b12520c6d translate(course-start-page): convert course start loading copy to English
+ dbffd23514a4635152ff96c440b7206f5c9ef432 translate(learning-path-page): convert learning path UI copy to English
+ 37cfea9775bd231eba50f983fcf19c2dc9b0f2aa translate(root-page-metadata): convert landing metadata copy to English
+ 372277f1335a139d4ef451c5ee8e37b1ffc9ab3a translate(module-test-page): convert module test exam UI copy to English
+ 3560d9dc1bb5e3d7968f496b2d99fe412299a146 translate(module-test-results-page): convert module test results UI copy to English

"@
# + 51db8a27c4b15e5deefc0fcb47adfc4c778a9a7d translate(learning-path-empty-state): convert empty state UI copy to English
# + 01d6bfee54b8fde276e64537bffa54e675aaf855 translate(learning-unit-card): convert card fallback and recommendation copy to English
# + 618db3befca9c8003eccd2bcb8824a64dacc35d4 translate(path-required-state): convert missing-path prompt UI copy to English
# + b9694243141937af39ad3c0164745387f920b7c9 translate(profile-change-banner): convert profile change banner UI copy to English
# + 97c6c875c0650f8ef08a0d87776f15cfc8957876 translate(planner-header): convert planner header and path switcher UI copy to English
# + f8e665d36dbf27344c240e4f5e57318e011168b6 translate(learning-path-status): convert shared learning path status labels to English
# + ff02973b9de11b96bc891997141ddab78ba00da1 translate(roadmap-node-card): convert recommendation badge copy to English
# + 8ee05808b07901a75cb58aa17be058274771112d translate(timeline-board): convert weekly timeline UI copy to English
# + ea17f6407cd0c4513059eb613709a49eab9aedac translate(learning-path-shell): convert shell error action copy to English
# + ebc493b262a1d0fdfb226562dc4e43438b7fe028 translate(learning-unit-drawer): convert drawer UI copy and CTA labels to English
# + 8c7548dc20400adf16d94af1c7d7f4de684863da translate(learning-path-duration): convert shared duration labels to English
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