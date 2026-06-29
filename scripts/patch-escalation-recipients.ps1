# Push live escalation recipients + allowlist to SSM (SecureString). Idempotent.
$ErrorActionPreference = "Stop"

$recipients = @(
    "reem.mor3@gmail.com",
    "kalex7878@gmail.com",
    "sagy.galor@fursa.org.il",
    "sagy.galor@portlandtrust.org.il"
) -join ","

$allowlist = $recipients

$params = @{
    "/piter-aiops/notification/mode" = "live"
    "/piter-aiops/notification/enable_live_dispatch" = "true"
    "/piter-aiops/notification/escalation_email" = $recipients
    "/piter-aiops/notification/allowlist" = $allowlist
    "/piter-aiops/notification/demo_email" = "reem.mor3@gmail.com"
}

foreach ($entry in $params.GetEnumerator()) {
    aws ssm put-parameter --name $entry.Key --value $entry.Value --type SecureString --overwrite | Out-Null
    Write-Host "Synced $($entry.Key)"
}

$verify = @(
    "kalex7878@gmail.com",
    "sagy.galor@fursa.org.il",
    "sagy.galor@portlandtrust.org.il"
)
foreach ($email in $verify) {
    aws ses verify-email-identity --email-address $email 2>$null | Out-Null
    Write-Host "SES verification requested: $email"
}

Write-Host "Done. Patch EC2 container: .\scripts\deploy-ec2-ssm.ps1 -NotificationOnly"
