#!/usr/bin/env bash
set -euo pipefail

BUCKET="${BUCKET:-your-artifacts-bucket}"
PREFIX="${PREFIX:-projects/piter-aiops/deploy}"
ENV_FILE="/opt/piter-aiops/.env"

aws s3 cp "s3://${BUCKET}/${PREFIX}/piter-aiops.tar" /tmp/piter-aiops.tar
docker load -i /tmp/piter-aiops.tar

set_kv() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}"
  else
    echo "${key}=${val}" >> "${ENV_FILE}"
  fi
}

if aws ssm get-parameters-by-path --path /piter-aiops/notification --with-decryption --output json >/tmp/piter-notification-params.json 2>/dev/null; then
python3 <<'PY'
import json, pathlib

mapping = {
    "/piter-aiops/notification/mode": "PITER_NOTIFICATION_MODE",
    "/piter-aiops/notification/enable_live_dispatch": "PITER_ENABLE_LIVE_DISPATCH",
    "/piter-aiops/notification/require_confirmation": "PITER_NOTIFICATION_REQUIRE_CONFIRMATION",
    "/piter-aiops/notification/confirmation_token": "PITER_NOTIFICATION_CONFIRMATION_TOKEN",
    "/piter-aiops/notification/allowlist": "PITER_NOTIFICATION_ALLOWLIST",
    "/piter-aiops/notification/allowed_severities": "PITER_NOTIFICATION_ALLOWED_SEVERITIES",
    "/piter-aiops/notification/ses_sender": "PITER_SES_SENDER_EMAIL",
    "/piter-aiops/notification/ses_configuration_set": "PITER_SES_CONFIGURATION_SET",
    "/piter-aiops/notification/sns_topic_arn": "PITER_SNS_TOPIC_ARN",
    "/piter-aiops/notification/sns_sms_use_topic": "PITER_SNS_SMS_USE_TOPIC",
    "/piter-aiops/notification/sms_use_voice_v2": "PITER_SMS_USE_VOICE_V2",
    "/piter-aiops/notification/demo_email": "PITER_DEMO_EMAIL_RECIPIENT",
    "/piter-aiops/notification/demo_sms": "PITER_DEMO_SMS_RECIPIENT",
    "/piter-aiops/notification/escalation_email": "PITER_ESCALATION_EMAIL",
    "/piter-aiops/notification/escalation_sms": "PITER_ESCALATION_SMS",
}

params = json.loads(pathlib.Path("/tmp/piter-notification-params.json").read_text(encoding="utf-8")).get("Parameters", [])
env_path = pathlib.Path("/opt/piter-aiops/.env")
lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
kv: dict[str, str] = {}
for line in lines:
    if "=" in line and not line.strip().startswith("#"):
        key, value = line.split("=", 1)
        kv[key.strip()] = value
for item in params:
    key = mapping.get(item["Name"])
    if key:
        kv[key] = item["Value"]
env_path.write_text("\n".join(f"{k}={v}" for k, v in kv.items()) + "\n", encoding="utf-8")
print(f"patched {len(params)} notification parameters")
PY
else
  echo "SSM parameter read unavailable; applying live notification defaults"
  set_kv PITER_NOTIFICATION_MODE live
  set_kv PITER_ENABLE_LIVE_DISPATCH true
  set_kv PITER_NOTIFICATION_REQUIRE_CONFIRMATION true
  set_kv PITER_NOTIFICATION_ALLOWED_SEVERITIES P1,P2
  set_kv PITER_SNS_SMS_USE_TOPIC false
  set_kv PITER_SMS_USE_VOICE_V2 true
fi

docker stop piter-aiops 2>/dev/null || true
docker rm piter-aiops 2>/dev/null || true
docker run -d --name piter-aiops --restart unless-stopped -p 8080:8080 \
  --env-file "${ENV_FILE}" \
  -e FORCE_LEGACY_UI=false \
  -e PITER_USE_BEDROCK=true \
  -e PITER_LOCAL_FALLBACK=true \
  piter-aiops:latest

sleep 8
curl -sf "http://localhost:8080/api/health?deep=1"
curl -sf "http://localhost:8080/api/bootstrap" | python3 -c "import sys,json; n=json.load(sys.stdin).get('notification',{}); print('mode=',n.get('mode'),'live=',n.get('live_dispatch_enabled'),'ready=',n.get('dispatch_ready'))"
docker exec piter-aiops ls -la /home/app/app/static/spa/assets/
