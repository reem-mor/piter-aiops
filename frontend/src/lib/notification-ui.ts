import type { BootstrapResponse } from "@/types/api";

export function isLiveDispatchReady(notification: BootstrapResponse["notification"] | undefined): boolean {
  if (!notification) return false;
  if (notification.dispatch_ready === true) return true;
  return (
    notification.live_dispatch_enabled === true &&
    notification.mode === "live" &&
    (notification.email_configured === true || notification.sms_configured === true) &&
    (notification.allowlist_count ?? 0) > 0
  );
}

export function notificationModeLabel(notification: BootstrapResponse["notification"] | undefined): string {
  return isLiveDispatchReady(notification) ? "LIVE" : "PREVIEW";
}
