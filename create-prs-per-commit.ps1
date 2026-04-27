$baseBranch = "main"
$sourceBranch = "ed-fix"
$remote = "origin"

$commits = @(
#   "827b7cb",
#   "8130073",
#   "d91200c",
#   "12526d5",
#   "69d34ed",
#   "623f49a",
#   "2f13cb6",
#   "269e8ee",
#   "e9601a0",
  "6d1f2c0",
  "7e31550",
  "f245a5f",
  "434e902",
  "2159dc3",
  "34c9ba9",
  "94f36b9",
  "1134abc",
  "76ff9ed",
  "fc5bef1",
  "ab4243f",
  "f105313"
)

git fetch $remote

foreach ($commit in $commits) {
  Write-Host "`n=============================="
  Write-Host "Processing commit $commit"
  Write-Host "==============================" -ForegroundColor Cyan

  $subject = git log -1 --pretty=%s $commit
  $safeName = $subject.ToLower() `
    -replace '[^a-z0-9]+','-' `
    -replace '^-|-$',''

  $branchName = "pr/$commit-$safeName"

  git checkout -B $branchName "$remote/$baseBranch"

  git cherry-pick -X theirs $commit

  if ($LASTEXITCODE -ne 0) {
    Write-Host "`nStill conflicted at commit $commit" -ForegroundColor Red
    Write-Host "Force-resolve by taking cherry-picked version:"
    Write-Host "  git checkout --theirs ."
    Write-Host "  git add ."
    Write-Host "  git cherry-pick --continue"
    Write-Host "  git push -u $remote $branchName"
    exit 1
  }

  git push -u $remote $branchName --force

  gh pr create `
    --base $baseBranch `
    --head $branchName `
    --title "$subject" `
    --body "Cherry-pick commit $commit from $sourceBranch into $baseBranch."
}

Write-Host "`nDone." -ForegroundColor Green