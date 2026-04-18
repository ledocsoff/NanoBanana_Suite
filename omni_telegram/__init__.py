from .nodes import (
    Omni_TelegramConfig,
    Omni_TelegramBulkInviteLinks,
    Omni_TelegramExportCSV,
    Omni_TelegramLinkAnalytics,
    Omni_TelegramRevokeLinks,
    Omni_TelegramDBReader,
)

NODE_CLASS_MAPPINGS = {
    "Omni_TelegramConfig": Omni_TelegramConfig,
    "Omni_TelegramBulkInviteLinks": Omni_TelegramBulkInviteLinks,
    "Omni_TelegramExportCSV": Omni_TelegramExportCSV,
    "Omni_TelegramLinkAnalytics": Omni_TelegramLinkAnalytics,
    "Omni_TelegramRevokeLinks": Omni_TelegramRevokeLinks,
    "Omni_TelegramDBReader": Omni_TelegramDBReader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Omni_TelegramConfig": "⚙️ Telegram Config Global",
    "Omni_TelegramBulkInviteLinks": "🔗 Telegram Bulk Invite Links",
    "Omni_TelegramExportCSV": "📁 Telegram Export CSV",
    "Omni_TelegramLinkAnalytics": "📊 Telegram Link Analytics",
    "Omni_TelegramRevokeLinks": "🗑️ Telegram Revoke Links",
    "Omni_TelegramDBReader": "📚 Telegram DB Reader",
}
