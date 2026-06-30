# Example only — edit recipients before running against your AWS account.
# Push live escalation recipients + allowlist to SSM (SecureString). Idempotent.
$ErrorActionPreference = "Stop"

$recipients = @(
    "your-email@example.com",
    "admin1@example.com",
    "admin2@example.com",
    "admin3@example.com"
) -join ","

$allowlist = $recipients

$params = @{
    "/piter-aiops/notification/mode" = "live"
    "/piter-aiops/notification/enable_live_dispatch" = "true"
    "/piter-aiops/notification/escalation_email" = $recipients
    "/piter-aiops/notification/allowlist" = $allowlist
    "/piter-aiops/notification/demo_email" = "your-email@example.com"
}

foreach ($entry in $params.GetEnumerator()) {
    aws ssm put-parameter --name $entry.Key --value $entry.Value --type SecureString --overwrite | Out-Null
    Write-Host "Synced $($entry.Key)"
}

$verify = @(
    "admin1@example.com",
    "admin2@example.com",
    "admin3@example.com"
)
foreach ($email in $verify) {
    aws ses verify-email-identity --email-address $email 2>$null | Out-Null
    Write-Host "SES verification requested: $email"
}

Write-Host "Done. Patch EC2 container: .\scripts\deploy-ec2-ssm.ps1 -NotificationOnly"
