# Push notification env fragment to SSM Parameter Store (SecureString). Not committed with values.
param(
    [string]$EnvFile = (Join-Path $PSScriptRoot "ec2-notification.env")
)

$ErrorActionPreference = "Stop"
$map = @{
    "PITER_NOTIFICATION_MODE" = "/piter-aiops/notification/mode"
    "PITER_ENABLE_LIVE_DISPATCH" = "/piter-aiops/notification/enable_live_dispatch"
    "PITER_NOTIFICATION_REQUIRE_CONFIRMATION" = "/piter-aiops/notification/require_confirmation"
    "PITER_NOTIFICATION_CONFIRMATION_TOKEN" = "/piter-aiops/notification/confirmation_token"
    "PITER_NOTIFICATION_ALLOWLIST" = "/piter-aiops/notification/allowlist"
    "PITER_NOTIFICATION_ALLOWED_SEVERITIES" = "/piter-aiops/notification/allowed_severities"
    "PITER_SES_SENDER_EMAIL" = "/piter-aiops/notification/ses_sender"
    "PITER_SES_CONFIGURATION_SET" = "/piter-aiops/notification/ses_configuration_set"
    "PITER_SNS_TOPIC_ARN" = "/piter-aiops/notification/sns_topic_arn"
    "PITER_SNS_SMS_USE_TOPIC" = "/piter-aiops/notification/sns_sms_use_topic"
    "PITER_SMS_USE_VOICE_V2" = "/piter-aiops/notification/sms_use_voice_v2"
    "PITER_DEMO_EMAIL_RECIPIENT" = "/piter-aiops/notification/demo_email"
    "PITER_DEMO_SMS_RECIPIENT" = "/piter-aiops/notification/demo_sms"
    "PITER_ESCALATION_EMAIL" = "/piter-aiops/notification/escalation_email"
    "PITER_ESCALATION_SMS" = "/piter-aiops/notification/escalation_sms"
}

Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $parts = $line -split "=", 2
    if ($parts.Count -lt 2) { return }
    $key = $parts[0].Trim()
    $value = $parts[1].Trim()
    if (-not $map.ContainsKey($key)) { return }
    $name = $map[$key]
    aws ssm put-parameter --name $name --value $value --type SecureString --overwrite | Out-Null
    Write-Host "Synced $name"
}
