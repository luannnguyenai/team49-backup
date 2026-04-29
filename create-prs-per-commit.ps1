$baseBranch = "main"
$sourceBranch = "ed-fix-5"
$remote = "origin"

git fetch $remote
$sourceRef = "$remote/$sourceBranch"

# Lấy short commit ID theo thứ tự cũ nhất -> mới nhất từ git log --oneline.
$commits = @(git log --reverse --format="%h" "$baseBranch..$sourceRef")

if ($commits.Count -eq 0) {
  Write-Host "No commits found between $baseBranch and $sourceRef." -ForegroundColor Yellow
  exit 0
}

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
