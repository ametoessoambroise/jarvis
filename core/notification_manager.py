import asyncio
import json
import os
import sys
from pathlib import Path

# Try importing WinRT modules if on Windows
HAS_WINRT = False
if sys.platform == "win32":
    try:
        import winrt.windows.ui.notifications as notifications
        import winrt.windows.ui.notifications.management as mgmt
        HAS_WINRT = True
    except ImportError:
        pass

MAX_SEEN_IDS = 1000

class NotificationManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.config_path = base_dir / "config" / "notifications_config.json"
        self.seen_ids = set()
        self._seen_order = []
        self.initialized = False
        self.listener = None
        self.allowed_apps = []
        self.rules = []
        self.auto_reply_enabled = True

    def _add_seen_id(self, notif_id: int) -> None:
        """Ajoute un id vu et borne la taille maximale de l'historique."""
        if notif_id not in self.seen_ids:
            self.seen_ids.add(notif_id)
            self._seen_order.append(notif_id)
            if len(self._seen_order) > MAX_SEEN_IDS:
                oldest = self._seen_order.pop(0)
                self.seen_ids.discard(oldest)


    def load_config(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.enabled = cfg.get("enabled", True)
                    self.allowed_apps = cfg.get("allowed_apps", ["WhatsApp", "WhatsApp Web", "Telegram", "Discord", "Messenger"])
                    self.auto_reply_enabled = cfg.get("auto_reply_enabled", True)
                    self.rules = cfg.get("rules", [])
            else:
                self.enabled = False
        except Exception as e:
            print(f"[NotificationManager] Error loading config: {e}")
            self.enabled = False

    async def initialize(self) -> bool:
        self.load_config()
        if not self.enabled:
            return False

        if not HAS_WINRT:
            print("[NotificationManager] WinRT modules not installed or platform not Windows. Run: pip install winrt-Windows.UI.Notifications winrt-Windows.UI.Notifications.Management winrt-Windows.Foundation winrt-Windows.Foundation.Collections winrt-Windows.ApplicationModel winrt-Windows.Data.Xml.Dom")
            return False

        try:
            self.listener = mgmt.UserNotificationListener.current
            status = await self.listener.request_access_async()
            # 1 corresponds to UserNotificationListenerAccessStatus.ALLOWED
            if status != 1:
                print(f"[NotificationManager] Access to notifications not allowed. Status: {status}")
                return False
            
            # Pre-populate seen notification IDs so we don't process old notifications
            initial_notifs = await self.listener.get_notifications_async(notifications.NotificationKinds.TOAST)
            for notif in initial_notifs:
                self._add_seen_id(notif.id)
            print(f"[NotificationManager] Initialized. Ignored {len(self.seen_ids)} existing notifications.")
            self.initialized = True
            return True
        except Exception as e:
            print(f"[NotificationManager] Initialization error: {e}")
            return False

    def _should_process(self, app_name: str, sender: str, text: str) -> bool:
        # 1. Check if app is allowed (case-insensitive)
        app_lower = app_name.lower()
        allowed_lower = [a.lower() for a in self.allowed_apps]
        
        if "*" not in allowed_lower and allowed_lower:
            # Check if any allowed app name is a substring of the notification app_name, or vice versa
            matched = False
            for allowed in allowed_lower:
                if allowed in app_lower or app_lower in allowed:
                    matched = True
                    break
            if not matched:
                return False

        # 2. Check rules
        for rule in self.rules:
            rule_app = rule.get("app", "*")
            rule_sender = rule.get("sender", "*")
            rule_action = rule.get("action", "allow")
            
            app_match = (rule_app == "*" or rule_app.lower() in app_lower or app_lower in rule_app.lower())
            sender_match = (rule_sender == "*" or rule_sender.lower() in sender.lower() or sender.lower() in rule_sender.lower())
            
            if app_match and sender_match:
                if rule_action == "ignore":
                    return False

        return True

    async def poll_new_notifications(self):
        if not self.initialized or not self.listener:
            return

        try:
            notifs = await self.listener.get_notifications_async(notifications.NotificationKinds.TOAST)
            new_notifications = []
            
            for notif in notifs:
                if notif.id not in self.seen_ids:
                    self._add_seen_id(notif.id)
                    
                    app_name = notif.app_info.display_info.display_name
                    
                    # Extract title and body text
                    title = ""
                    body = ""
                    try:
                        binding = notif.notification.visual.get_binding(notifications.KnownNotificationBindings.toast_generic)
                        if binding:
                            txt_elements = binding.get_text_elements()
                            if len(txt_elements) > 0:
                                title = txt_elements[0].text or ""
                            if len(txt_elements) > 1:
                                body = txt_elements[1].text or ""
                    except Exception as ex:
                        print(f"[NotificationManager] Error reading notification visual: {ex}")
                        
                    # Filter and check rules
                    if self._should_process(app_name, title, body):
                        new_notifications.append({
                            "id": notif.id,
                            "app": app_name,
                            "title": title,
                            "body": body
                        })
            
            return new_notifications
        except Exception as e:
            print(f"[NotificationManager] Polling error: {e}")
            return []
