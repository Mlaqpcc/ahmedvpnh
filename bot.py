import os
import threading
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID_STR = os.getenv("OWNER_ID", "6803988521").strip()
try:
    OWNER_ID = int(OWNER_ID_STR)
except ValueError:
    OWNER_ID = 6803988521

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8080))

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import database

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("AhmedVpnBot")

# Store conversation state for the owner.
# Schema: {user_id: {"mode": "add|announce|update", "step": "...", "data": {...}}}
SESSIONS = {}


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def get_main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("➕ إضافة سيرفر", callback_data="menu_add_server"),
            InlineKeyboardButton("🗑️ مسح سيرفر", callback_data="menu_delete_server_0")
        ],
        [
            InlineKeyboardButton("📋 عرض السيرفرات", callback_data="menu_list_servers"),
            InlineKeyboardButton("🔄 تحديث", callback_data="menu_refresh")
        ],
        [
            InlineKeyboardButton("📢 إعلان للتطبيق", callback_data="menu_announce"),
            InlineKeyboardButton("⬆️ تحديث إجباري", callback_data="menu_update")
        ],
        [
            InlineKeyboardButton("🧩 بروكسي/بايلود لسيرفر", callback_data="menu_advanced_0")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_flag_for_name(name: str) -> str:
    n = (name or "").upper()
    if "GERMAN" in n or "ألمان" in n:
        return "🇩🇪"
    elif "NETHER" in n or "هولند" in n:
        return "🇳🇱"
    elif "FRANCE" in n or "فرنس" in n:
        return "🇫🇷"
    elif "USA" in n or "AMERICA" in n or "أمريك" in n:
        return "🇺🇸"
    elif "TURK" in n or "ترك" in n:
        return "🇹🇷"
    elif "BRIT" in n or "UK" in n or "بريطان" in n:
        return "🇬🇧"
    elif "SINGAPORE" in n:
        return "🇸🇬"
    elif "CANADA" in n:
        return "🇨🇦"
    return "🌐"


def main_menu_text() -> str:
    count = database.get_servers_count()
    users = database.get_users_count()
    return (
        "🚀 **AHMED VPN — لوحة التحكم بالخوادم** 🛡️\n\n"
        "مرحباً بك يا مالك التطبيق في لوحة الإدارة.\n\n"
        f"📊 عدد السيرفرات الحالية: `{count}`\n"
        f"👥 عدد الأجهزة المسجّلة: `{users}`\n"
        f"🌐 رابط الـ API للتطبيق:\n`http://{HOST}:{PORT}/api/servers`\n\n"
        "اختر أحد الخيارات للبدء:"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_owner(user_id):
        await update.message.reply_text(
            "⛔ **عذراً، هذا البوت خاص بمالك تطبيق AHMED VPN فقط.**\n"
            f"آيدي المستخدم الخاص بك: `{user_id}` غير مصرح له.",
            parse_mode="Markdown"
        )
        return

    SESSIONS.pop(user_id, None)
    await update.message.reply_text(
        main_menu_text(),
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if not is_owner(user_id):
        await query.edit_message_text("⛔ عذراً، لست مالك البوت.")
        return

    if data == "menu_refresh" or data == "menu_main":
        SESSIONS.pop(user_id, None)
        await query.edit_message_text(
            main_menu_text(),
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "menu_add_server":
        SESSIONS[user_id] = {"mode": "add", "step": "name", "data": {}}
        text = (
            "➕ **إضافة سيرفر جديد (الخطوة 1 من 3):**\n\n"
            "أرسل الآن **اسم السيرفر**:\n"
            "*(مثال: Germany 01)*\n\n"
            "💡 أو يمكنك إرسال رابط السيرفر مباشرة (`vless://...`, `vmess://...`, `trojan://...`) ليتم تحليله وحفظه فورياً."
        )
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("set_proto_"):
        proto = data.split("_")[-1]
        session = SESSIONS.get(user_id)
        if session:
            session["data"]["protocol"] = proto
            session["step"] = "config"
            text = (
                f"✅ تم اختيار البروتوكول: `{proto}`\n\n"
                "🔗 **الخطوة 3 من 3:**\n"
                f"أرسل الآن **رابط السيرفر** (يبدأ بـ `{proto.lower()}://`):"
            )
            keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="menu_main")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "menu_list_servers":
        servers = database.get_all_servers()
        if not servers:
            text = "📋 **لا توجد سيرفرات مضافة حالياً في قاعدة البيانات.**"
            keyboard = [
                [InlineKeyboardButton("➕ إضافة سيرفر", callback_data="menu_add_server")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        text = f"📋 **عرض السيرفرات المتاحة ({len(servers)} سيرفر):**\n\n"
        for s in servers:
            flag = get_flag_for_name(s["name"])
            text += (
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🔹 **ID:** `{s['id']}`\n"
                f"🏷️ **الاسم:** {flag} {s['name']}\n"
                f"⚡ **البروتوكول:** `{s['protocol']}`\n"
                f"📅 **تاريخ الإضافة:** `{s['created_at']}`\n"
                f"🔗 **الرابط:**\n`{s['config']}`\n"
            )
        text += "━━━━━━━━━━━━━━━━━━━"
        keyboard = [
            [InlineKeyboardButton("➕ إضافة سيرفر", callback_data="menu_add_server")],
            [InlineKeyboardButton("🗑️ مسح سيرفر", callback_data="menu_delete_server_0")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("menu_delete_server_"):
        page = int(data.split("_")[-1])
        servers = database.get_all_servers()
        if not servers:
            text = "🗑️ **لا توجد سيرفرات لحذفها حالياً.**"
            keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu_main")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        per_page = 5
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, len(servers))
        current_page = servers[start_idx:end_idx]

        keyboard = []
        for s in current_page:
            flag = get_flag_for_name(s["name"])
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ {flag} {s['name']} ({s['protocol']})",
                    callback_data=f"confirm_del_{s['id']}"
                )
            ])

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"menu_delete_server_{page - 1}"))
        if end_idx < len(servers):
            nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"menu_delete_server_{page + 1}"))
        if nav:
            keyboard.append(nav)

        keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu_main")])

        text = "🗑️ **اختر السيرفر الذي ترغب بحذفه نهائياً:**"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("confirm_del_"):
        server_id = int(data.split("_")[-1])
        server = database.get_server_by_id(server_id)
        if not server:
            await query.answer("السيرفر غير موجود أو تم حذفه مسبقاً!", show_alert=True)
            await query.edit_message_text("السيرفر غير موجود.", reply_markup=get_main_menu_keyboard())
            return

        flag = get_flag_for_name(server["name"])
        text = (
            f"⚠️ **تأكيد الحذف:**\n\n"
            f"هل أنت متأكد من حذف السيرفر:\n"
            f"**{flag} {server['name']}** (`{server['protocol']}`)\n\n"
            "⚠️ هذه العملية لا يمكن التراجع عنها وسيتم حذفه من قاعدة البيانات وتطبيق المستخدمين."
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ نعم، حذف", callback_data=f"execute_del_{server_id}"),
                InlineKeyboardButton("❌ إلغاء", callback_data="menu_delete_server_0")
            ]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("execute_del_"):
        server_id = int(data.split("_")[-1])
        server = database.get_server_by_id(server_id)
        name = server["name"] if server else f"#{server_id}"
        database.delete_server(server_id)

        await query.answer("تم حذف السيرفر بنجاح!", show_alert=True)
        text = f"✅ **تم حذف السيرفر بنجاح:**\n`{name}`"
        keyboard = [
            [InlineKeyboardButton("🗑️ مسح سيرفر آخر", callback_data="menu_delete_server_0")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- Per-server proxy/payload ----------
    elif data.startswith("menu_advanced_"):
        page = int(data.split("_")[-1])
        servers = database.get_all_servers()
        if not servers:
            keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu_main")]]
            await query.edit_message_text("🧩 لا توجد سيرفرات بعد.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return
        per_page = 5
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, len(servers))
        keyboard = []
        for s in servers[start_idx:end_idx]:
            flag = get_flag_for_name(s["name"])
            has = []
            if s.get("proxy_host") and s.get("proxy_port"):
                has.append("بروكسي")
            if s.get("payload"):
                has.append("بايلود")
            tag = (" — " + " + ".join(has)) if has else ""
            keyboard.append([InlineKeyboardButton(f"🧩 {flag} {s['name']}{tag}", callback_data=f"adv_pick_{s['id']}")])
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"menu_advanced_{page - 1}"))
        if end_idx < len(servers):
            nav.append(InlineKeyboardButton("التالي ➡️", callback_data=f"menu_advanced_{page + 1}"))
        if nav:
            keyboard.append(nav)
        keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu_main")])
        await query.edit_message_text("🧩 **اختر سيرفراً لضبط البروكسي/البايلود الخاص به:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("adv_pick_"):
        sid = int(data.split("_")[-1])
        server = database.get_server_by_id(sid)
        if not server:
            await query.answer("السيرفر غير موجود", show_alert=True)
            return
        SESSIONS[user_id] = {"mode": "adv", "step": "proxy", "data": {"id": sid, "name": server["name"]}}
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="menu_main")]]
        await query.edit_message_text(
            f"🧩 **{server['name']}**\n\nأرسل **البروكسي** بصيغة `host:port`\n(أو أرسل `-` لتخطي البروكسي ومسحه):",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- Announcement ----------
    elif data == "menu_announce":
        SESSIONS[user_id] = {"mode": "announce", "step": "text", "data": {}}
        text = (
            "📢 **إعلان للتطبيق**\n\n"
            "أرسل الآن **نص الإعلان** الذي سيصل لكل المستخدمين كإشعار داخل التطبيق:"
        )
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- Forced update ----------
    elif data == "menu_update":
        SESSIONS[user_id] = {"mode": "update", "step": "version", "data": {}}
        text = (
            "⬆️ **تحديث إجباري للتطبيق (الخطوة 1 من 3):**\n\n"
            "أرسل **رقم الإصدار الجديد** (versionCode) — رقم صحيح أكبر من الحالي:"
        )
        keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_owner(user_id):
        return

    text = (update.message.text or "").strip()
    session = SESSIONS.get(user_id)

    # 1. Quick direct-link detection (vless://, vmess://, trojan://)
    if text.startswith("vless://") or text.startswith("vmess://") or text.startswith("trojan://"):
        lines = text.splitlines()
        added = 0
        name = ""
        proto = ""
        for line in lines:
            line = line.strip()
            if not line:
                continue
            proto = "VLESS" if line.startswith("vless://") else ("VMESS" if line.startswith("vmess://") else "TROJAN")
            name = f"Server {database.get_servers_count() + 1}"
            if "#" in line:
                from urllib.parse import unquote
                remark = unquote(line.split("#")[-1]).strip()
                if remark:
                    name = remark

            database.add_server(name=name, protocol=proto, config=line)
            added += 1

        SESSIONS.pop(user_id, None)
        flag = get_flag_for_name(name)
        reply = (
            f"✅ **تمت إضافة {added} سيرفر بنجاح!** 🚀\n\n"
            f"• **الاسم:** {flag} {name}\n"
            f"• **البروتوكول:** `{proto}`\n"
        )
        keyboard = [
            [InlineKeyboardButton("📋 عرض السيرفرات", callback_data="menu_list_servers")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu_main")]
        ]
        await update.message.reply_text(reply, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # 2. Wizard sessions
    if session:
        mode = session.get("mode", "add")

        if mode == "announce":
            if not text:
                await update.message.reply_text("⚠️ أرسل نصاً غير فارغ.")
                return
            database.add_announcement(text)
            SESSIONS.pop(user_id, None)
            reply = f"✅ **تم إرسال الإعلان للتطبيق:**\n\n{text}"
            keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu_main")]]
            await update.message.reply_text(reply, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        if mode == "update":
            step = session.get("step")
            if step == "version":
                if not text.isdigit():
                    await update.message.reply_text("⚠️ أرسل رقم إصدار صحيح (أرقام فقط).")
                    return
                session["data"]["version_code"] = int(text)
                session["step"] = "url"
                await update.message.reply_text(
                    f"✅ رقم الإصدار: `{text}`\n\n🔗 **الخطوة 2 من 3:** أرسل **رابط تحميل الـAPK** (يبدأ بـ http):",
                    parse_mode="Markdown"
                )
                return
            elif step == "url":
                if not text.startswith("http"):
                    await update.message.reply_text("⚠️ الرابط يجب أن يبدأ بـ http.")
                    return
                session["data"]["url"] = text
                session["step"] = "message"
                await update.message.reply_text(
                    "✅ تم حفظ الرابط.\n\n📝 **الخطوة 3 من 3:** أرسل **نص رسالة التحديث** (أو أرسل `-` لاستخدام النص الافتراضي):",
                    parse_mode="Markdown"
                )
                return
            elif step == "message":
                import json
                msg = "" if text == "-" else text
                database.set_setting("app_update", json.dumps({
                    "enabled": True,
                    "version_code": session["data"].get("version_code", 0),
                    "url": session["data"].get("url", ""),
                    "message": msg,
                }))
                SESSIONS.pop(user_id, None)
                reply = (
                    "✅ **تم تفعيل التحديث الإجباري!**\n\n"
                    f"• versionCode: `{session['data'].get('version_code')}`\n"
                    f"• الرابط: `{session['data'].get('url')}`"
                )
                keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu_main")]]
                await update.message.reply_text(reply, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
                return

        if mode == "adv":
            step = session.get("step")
            sid = session["data"].get("id")
            if step == "proxy":
                host = ""
                port = 0
                if text != "-":
                    if ":" in text:
                        h, p = text.rsplit(":", 1)
                        if p.strip().isdigit():
                            host = h.strip()
                            port = int(p.strip())
                    if not host or port <= 0:
                        await update.message.reply_text("⚠️ صيغة غير صحيحة. أرسل `host:port` أو `-`.", parse_mode="Markdown")
                        return
                session["data"]["proxy_host"] = host
                session["data"]["proxy_port"] = port
                session["step"] = "payload"
                await update.message.reply_text("🔗 أرسل الآن **البايلود** (أو `-` لتخطيه):", parse_mode="Markdown")
                return
            elif step == "payload":
                payload = "" if text == "-" else text
                srv = database.get_server_by_id(sid) or {}
                database.update_server_advanced(
                    sid,
                    country=srv.get("country", "") or "",
                    proxy_host=session["data"].get("proxy_host", ""),
                    proxy_port=session["data"].get("proxy_port", 0),
                    proxy_user=srv.get("proxy_user", "") or "",
                    proxy_pass=srv.get("proxy_pass", "") or "",
                    payload=payload,
                )
                SESSIONS.pop(user_id, None)
                reply = (
                    "✅ **تم حفظ إعدادات السيرفر**\n\n"
                    f"• بروكسي: `{session['data'].get('proxy_host') or '—'}`\n"
                    f"• بايلود: `{'نعم' if payload else '—'}`"
                )
                keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu_main")]]
                await update.message.reply_text(reply, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
                return

        if mode == "add":
            step = session.get("step")
            if step == "name":
                session["data"]["name"] = text
                session["step"] = "protocol"
                prompt = (
                    f"🏷️ اسم السيرفر: **{text}**\n\n"
                    "⚡ **الخطوة 2 من 3:**\n"
                    "اختر **البروتوكول** من الأزرار أدناه:"
                )
                keyboard = [
                    [
                        InlineKeyboardButton("VLESS", callback_data="set_proto_VLESS"),
                        InlineKeyboardButton("VMESS", callback_data="set_proto_VMESS"),
                        InlineKeyboardButton("TROJAN", callback_data="set_proto_TROJAN")
                    ],
                    [InlineKeyboardButton("🔙 إلغاء", callback_data="menu_main")]
                ]
                await update.message.reply_text(prompt, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
                return

            elif step == "config":
                proto = session["data"].get("protocol", "VLESS")
                name = session["data"].get("name", "Server")
                config = text

                sid = database.add_server(name=name, protocol=proto, config=config)
                SESSIONS.pop(user_id, None)

                flag = get_flag_for_name(name)
                reply = (
                    "🎉 **تم حفظ السيرفر بنجاح في قاعدة البيانات!**\n\n"
                    f"• **ID:** `{sid}`\n"
                    f"• **الاسم:** {flag} {name}\n"
                    f"• **البروتوكول:** `{proto}`\n"
                    f"• **الرابط:** `{config[:35]}...`\n"
                )
                keyboard = [
                    [InlineKeyboardButton("➕ إضافة سيرفر آخر", callback_data="menu_add_server")],
                    [InlineKeyboardButton("📋 عرض السيرفرات", callback_data="menu_list_servers")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu_main")]
                ]
                await update.message.reply_text(reply, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
                return

    # If no session and text sent, remind owner of /start
    await update.message.reply_text(
        "💡 أرسل /start لفتح لوحة التحكم، أو أرسل رابط سيرفر (`vless://...`) لإضافته فورياً."
    )


async def announce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick: /announce <text>"""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        return
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("الاستخدام: `/announce نص الإعلان`", parse_mode="Markdown")
        return
    database.add_announcement(text)
    await update.message.reply_text("✅ تم إرسال الإعلان للتطبيق.")


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick: /update <versionCode> <apk_url> [message]"""
    import json
    user_id = update.effective_user.id
    if not is_owner(user_id):
        return
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "الاستخدام: `/update versionCode apk_url [message]`", parse_mode="Markdown"
        )
        return
    if not args[0].isdigit() or not args[1].startswith("http"):
        await update.message.reply_text("⚠️ تأكد من رقم الإصدار والرابط (يبدأ بـ http).")
        return
    message = " ".join(args[2:]) if len(args) > 2 else ""
    database.set_setting("app_update", json.dumps({
        "enabled": True,
        "version_code": int(args[0]),
        "url": args[1],
        "message": message,
    }))
    await update.message.reply_text("✅ تم تفعيل التحديث الإجباري.")


def start_api_server():
    """Runs uvicorn in a daemon thread so 'python bot.py' runs both."""
    import uvicorn
    logger.info(f"Starting FastAPI on http://{HOST}:{PORT}")
    uvicorn.run("api:app", host=HOST, port=PORT, log_level="warning")


def main():
    print("=" * 60)
    print("  🚀 AHMED VPN - Telegram Bot & FastAPI Server")
    print(f"  Owner ID: {OWNER_ID}")
    print(f"  API Endpoint: http://{HOST}:{PORT}/api/servers")
    print("=" * 60)

    # 1. Initialize SQLite Database
    database.init_db()

    # 2. Check token
    if not BOT_TOKEN or BOT_TOKEN == "ضع_توكن_البوت_هنا":
        print("\n" + "!" * 60)
        print(" [!] تحذير: لم تقم بوضع BOT_TOKEN داخل ملف .env بعد!")
        print(f" [!] افتح الملف: {env_path}")
        print(" [!] ضع التوكن الخاص بك ثم أعد التشغيل.")
        print(" [!] سيعمل سيرفر الـ API فقط الآن على المنفذ " + str(PORT))
        print("!" * 60 + "\n")
        # Run API directly in main thread
        import uvicorn
        uvicorn.run("api:app", host=HOST, port=PORT, log_level="info")
        return

    # 3. Start FastAPI server in background thread
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    # 4. Start Telegram Bot on main thread
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("announce", announce_command))
    app.add_handler(CommandHandler("update", update_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    logger.info("Bot is starting polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
