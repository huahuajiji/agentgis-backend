# 把本仓库同步到 Hugging Face Space（部署产物）。
#
# 做法：临时目录里组装一份"Space 要的内容"（Dockerfile + app + requirements +
# space/README.md），单独 git init 推到 HF。不推开发历史，也不改本地 remote。
#
# 首次运行前先确认能登录 HF（推送时提示输入用户名 + access token）。

$ErrorActionPreference = "Stop"

$repo = $PSScriptRoot | Split-Path -Parent
$user = $env:HF_USER
if (-not $user) { $user = "huahuajiji" }
$spaceId = "agentgis-backend"
$tmp = Join-Path $env:TEMP "agentgis-space-$([guid]::NewGuid().ToString('N').Substring(0,8))"

Write-Host "组装 Space 内容: $tmp"
New-Item -ItemType Directory -Path $tmp | Out-Null

Copy-Item (Join-Path $repo "Dockerfile") $tmp
Copy-Item (Join-Path $repo "requirements.txt") $tmp
Copy-Item (Join-Path $repo "app") $tmp -Recurse
Copy-Item (Join-Path $repo "space\README.md") (Join-Path $tmp "README.md")

Get-ChildItem -Path $tmp -Recurse -Directory -Filter "__pycache__" |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

$commit = git -C $repo rev-parse --short HEAD

Push-Location $tmp
try {
  git init -q
  git checkout -q -b main
  git add -A
  git -c user.name="huahuajiji" -c user.email="1914828859@qq.com" commit -q -m "deploy: 同步自 agentgis-backend@$commit"
  Write-Host "推送到 https://huggingface.co/spaces/$user/$spaceId"
  git push --force "https://huggingface.co/spaces/$user/$spaceId" main
} finally {
  Pop-Location
  Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}
