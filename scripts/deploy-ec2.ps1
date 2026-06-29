# Build PITER AiOps locally and print (or run) EC2 deploy commands.
# Does not run from CI. See frontend/EC2_DEPLOY.md and docs/LOCAL_DEV.md.
param(
    [string]$SshHost = "ec2-3-235-22-143.compute-1.amazonaws.com",
    [string]$SshUser = "ec2-user",
    [string]$SshKey = "",
    [string]$RemotePath = "/opt/piter-aiops",
    [string]$ImageTag = "piter-aiops:latest",
    [string]$PublicBaseUrl = "http://ec2-3-235-22-143.compute-1.amazonaws.com:8080",
    [switch]$SkipNpmBuild,
    [switch]$SkipDockerBuild,
    [switch]$Execute,
    [switch]$Verify
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"
$Python = Join-Path $Root ".venv\Scripts\python.exe"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Get-SshPrefix() {
    if ($SshKey) {
        return "ssh -i `"$SshKey`" ${SshUser}@${SshHost}"
    }
    return "ssh ${SshUser}@${SshHost}"
}

function Get-ScpPrefix() {
    if ($SshKey) {
        return "scp -i `"$SshKey`""
    }
    return "scp"
}

function Get-RemoteDeployScript() {
    $lines = @(
        "set -e"
        "cd $RemotePath"
        "git pull"
        "docker build -t $ImageTag ."
        "docker stop piter-aiops 2>/dev/null || true"
        "docker rm piter-aiops 2>/dev/null || true"
        "docker run -d --name piter-aiops --restart unless-stopped -p 8080:8080 \"
        "  --env-file $RemotePath/.env \"
        "  -e PITER_USE_BEDROCK=true \"
        "  -e PITER_LOCAL_FALLBACK=true \"
        "  $ImageTag"
        "curl -s http://localhost:8080/api/health?deep=1"
    )
    return ($lines -join "`n")
}

function Invoke-RemoteCommand([string]$RemoteScript) {
    $sshArgs = @()
    if ($SshKey) {
        $sshArgs += @("-i", $SshKey)
    }
    $sshArgs += "${SshUser}@${SshHost}"
    Write-Host "ssh $($sshArgs -join ' ')" -ForegroundColor DarkGray
    $RemoteScript | & ssh @sshArgs "bash -s"
    if ($LASTEXITCODE -ne 0) {
        throw "Remote command failed (exit $LASTEXITCODE)."
    }
}

Set-Location $Root

if (-not $SkipNpmBuild) {
    Write-Step "Building SPA (npm run build)"
    Push-Location $Frontend
    try {
        if (-not (Test-Path "node_modules")) {
            Write-Host "node_modules missing - running npm ci first" -ForegroundColor Yellow
            npm ci
            if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }
        }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "npm run build failed." }
    }
    finally {
        Pop-Location
    }
}

if (-not $SkipDockerBuild) {
    Write-Step "Building Docker image ($ImageTag)"
    docker build -t $ImageTag .
    if ($LASTEXITCODE -ne 0) { throw "docker build failed." }
}

$remoteDeploy = Get-RemoteDeployScript
$sshPrefix = Get-SshPrefix
$scpPrefix = Get-ScpPrefix

Write-Step "EC2 deploy commands (run after git push)"
Write-Host ""
Write-Host "# Option A - rebuild on EC2 (recommended; Dockerfile builds SPA inside image):" -ForegroundColor Yellow
Write-Host $remoteDeploy
Write-Host "# Run on EC2 via: $sshPrefix bash -s  (pipe script above to stdin)" -ForegroundColor Yellow
Write-Host ""
Write-Host "# Option B - transfer local image:" -ForegroundColor Yellow
Write-Host "docker save $ImageTag -o piter-aiops.tar" -ForegroundColor Yellow
Write-Host "$scpPrefix ./piter-aiops.tar ${SshUser}@${SshHost}:~/" -ForegroundColor Yellow
$loadCmd = "docker load -i ~/piter-aiops.tar; docker stop piter-aiops; docker rm piter-aiops; docker run -d --name piter-aiops --restart unless-stopped -p 8080:8080 --env-file $RemotePath/.env -e PITER_USE_BEDROCK=true $ImageTag"
Write-Host "$sshPrefix `"$loadCmd`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "# Public health check:" -ForegroundColor Yellow
Write-Host "curl -s $PublicBaseUrl/api/health?deep=1" -ForegroundColor Yellow
Write-Host "# Browser smoke: $PublicBaseUrl/ (see frontend/VERIFY.md)" -ForegroundColor Yellow
Write-Host ""

if ($Execute) {
    if (-not $SshKey) {
        Write-Error "-Execute requires -SshKey pointing to your .pem file."
    }
    Write-Step "Executing remote deploy on $SshHost"
    Invoke-RemoteCommand $remoteDeploy
}

if ($Verify) {
    Write-Step "Running verify_live_demo.py against $PublicBaseUrl"
    if (-not (Test-Path $Python)) {
        $Python = "python"
    }
    & $Python (Join-Path $Root "scripts\verify_live_demo.py") --base-url $PublicBaseUrl
    if ($LASTEXITCODE -ne 0) { throw "verify_live_demo.py failed." }
}

Write-Step "Done"
