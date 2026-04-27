$baseBranch = "main"
$sourceBranch = "ed-fix-2"
$remote = "origin"

$commits = @(
  "03239da",
  "1f1135a",
  "0d61509"
)

# Tránh file script bị Git add nhầm
git reset create-prs-per-commit.ps1 2>$null
if (Test-Path ".git/info/exclude") {
  if (-not (Select-String -Path ".git/info/exclude" -Pattern "^create-prs-per-commit\.ps1$" -Quiet)) {
    Add-Content ".git/info/exclude" "create-prs-per-commit.ps1"
  }
}

git fetch $remote

foreach ($commit in $commits) {
  Write-Host "`n=============================="
  Write-Host "Processing commit $commit"
  Write-Host "==============================" -ForegroundColor Cyan

  # Luôn update main trước mỗi commit để PR sau dựa trên main mới nhất
  git checkout $baseBranch
  git pull $remote $baseBranch

  $subject = git log -1 --pretty=%s $commit
  $safeName = $subject.ToLower() `
    -replace '[^a-z0-9]+','-' `
    -replace '^-|-$',''

  $branchName = "pr/$commit-$safeName"

  git checkout -B $branchName "$remote/$baseBranch"

  # Cherry-pick, ưu tiên code từ commit ed-fix nếu conflict
  git cherry-pick -X theirs $commit

  if ($LASTEXITCODE -ne 0) {
    Write-Host "Conflict remained. Forcing incoming changes..." -ForegroundColor Yellow

    git checkout --theirs .
    git add .
    git cherry-pick --continue

    if ($LASTEXITCODE -ne 0) {
      Write-Host "Cannot auto-resolve commit $commit. Stopping." -ForegroundColor Red
      exit 1
    }
  }

  git push -u $remote $branchName --force

  # Tạo PR
  gh pr create `
    --base $baseBranch `
    --head $branchName `
    --title "$subject" `
    --body "Auto cherry-pick commit $commit from $sourceBranch into $baseBranch."

  if ($LASTEXITCODE -ne 0) {
    Write-Host "PR create failed. Maybe PR already exists. Continuing to merge..." -ForegroundColor Yellow
  }

  # Merge PR ngay
  gh pr merge $branchName --merge --delete-branch

  if ($LASTEXITCODE -ne 0) {
    Write-Host "Merge failed for $branchName. Stopping." -ForegroundColor Red
    exit 1
  }

  Write-Host "Merged $commit successfully." -ForegroundColor Green
}

git checkout $baseBranch
git pull $remote $baseBranch

Write-Host "`nAll commits processed and merged." -ForegroundColor Green