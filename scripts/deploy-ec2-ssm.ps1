# Build Docker image locally, upload to S3, deploy to EC2 via SSM (no SSH required).
# See docs/LOCAL_DEV.md and frontend/EC2_DEPLOY.md.
param(
    [string]$InstanceId = $env:PITER_EC2_INSTANCE_ID,
    [string]$Bucket = $env:PITER_ARTIFACTS_BUCKET,
    [string]$Prefix = "projects/piter-aiops/deploy",
    [string]$ImageTag = "piter-aiops:latest",
    [string]$PublicBaseUrl = $env:PITER_PUBLIC_BASE_URL,
    [switch]$SkipDockerBuild,
    [switch]$SkipS3Upload,
    [switch]$NotificationOnly,
    [switch]$Verify
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$SsmDeployJson = Join-Path $PSScriptRoot "ssm-deploy-image.json"
$SsmNotifyJson = Join-Path $PSScriptRoot "ssm-patch-notification-live.json"
$SsmVerifyJson = Join-Path $PSScriptRoot "ssm-verify-live.json"
$DeployScript = Join-Path $PSScriptRoot "ec2-deploy-from-s3.sh"
$TarPath = Join-Path $Root "piter-aiops.tar"

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Wait-SsmCommand([string]$CommandId, [string]$InstanceId, [int]$TimeoutSec = 300) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    do {
        Start-Sleep -Seconds 5
        $inv = aws ssm get-command-invocation `
            --command-id $CommandId `
            --instance-id $InstanceId `
            --output json | ConvertFrom-Json
        if ($inv.Status -in @("Success", "Failed", "Cancelled", "TimedOut")) {
            Write-Host $inv.StandardOutputContent
            if ($inv.StandardErrorContent) {
                Write-Host $inv.StandardErrorContent -ForegroundColor Yellow
            }
            if ($inv.Status -ne "Success") {
                throw "SSM command $CommandId ended with status $($inv.Status)"
            }
            return $inv
        }
    } while ((Get-Date) -lt $deadline)
    throw "SSM command $CommandId timed out after ${TimeoutSec}s"
}

Set-Location $Root

if ($NotificationOnly) {
    Write-Step "Patching notification env on EC2 via SSM"
    $cmdId = aws ssm send-command `
        --instance-ids $InstanceId `
        --document-name AWS-RunShellScript `
        --parameters "file://$SsmNotifyJson" `
        --output text --query "Command.CommandId"
    Wait-SsmCommand $cmdId $InstanceId | Out-Null
}
else {
    if (-not $SkipDockerBuild) {
        Write-Step "Building Docker image ($ImageTag)"
        docker build -t $ImageTag .
        if ($LASTEXITCODE -ne 0) { throw "docker build failed." }

        Write-Step "Saving image to $TarPath"
        docker save $ImageTag -o $TarPath
        if ($LASTEXITCODE -ne 0) { throw "docker save failed." }
    }

    if (-not $SkipS3Upload) {
        if (-not (Test-Path $TarPath)) {
            throw "Missing $TarPath - run without -SkipDockerBuild or -SkipS3Upload."
        }
        Write-Step "Uploading image and deploy script to S3"
        aws s3 cp $TarPath "s3://$Bucket/$Prefix/piter-aiops.tar"
        if ($LASTEXITCODE -ne 0) { throw "S3 upload (tar) failed." }
        aws s3 cp $DeployScript "s3://$Bucket/$Prefix/ec2-deploy-from-s3.sh"
        if ($LASTEXITCODE -ne 0) { throw "S3 upload (script) failed." }
    }

    Write-Step "Deploying on EC2 via SSM ($InstanceId)"
    $cmdId = aws ssm send-command `
        --instance-ids $InstanceId `
        --document-name AWS-RunShellScript `
        --parameters "file://$SsmDeployJson" `
        --output text --query "Command.CommandId"
    Wait-SsmCommand $cmdId $InstanceId | Out-Null
}

if ($Verify) {
    Write-Step "SSM verify on instance"
    $verifyId = aws ssm send-command `
        --instance-ids $InstanceId `
        --document-name AWS-RunShellScript `
        --parameters "file://$SsmVerifyJson" `
        --output text --query "Command.CommandId"
    Wait-SsmCommand $verifyId $InstanceId 120 | Out-Null

    Write-Step "Running verify_live_demo.py against $PublicBaseUrl"
    if (-not (Test-Path $Python)) { $Python = "python" }
    & $Python (Join-Path $Root "scripts\verify_live_demo.py") --base-url $PublicBaseUrl
    if ($LASTEXITCODE -ne 0) { throw "verify_live_demo.py failed." }
}

Write-Step "Done"
Write-Host "Browser smoke: $PublicBaseUrl/ (hard refresh Ctrl+Shift+R)" -ForegroundColor Green
Write-Host "Click-test: frontend/VERIFY.md" -ForegroundColor Green
