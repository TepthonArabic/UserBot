import random
import glob
import os
from telethon import TelegramClient, events
from yt_dlp import YoutubeDL
from Tepthon import zedub
from ..Config import Config

plugin_category = "البوت"

def get_cookies_file():
    folder_path = f"{os.getcwd()}/rcookies"
    txt_files = glob.glob(os.path.join(folder_path, '*.txt'))
    if not txt_files:
        raise FileNotFoundError("No .txt files found in the specified folder.")
    cookie_txt_file = random.choice(txt_files)
    return cookie_txt_file

@zedub.on(events.NewMessage(pattern='.بحث (.*)'))
async def download_audio(event):
    # تحقق مما إذا كان المرسل هو الحساب المنصب فقط
    if event.sender_id != Config.OWNER_ID:  # استبدل Config.OWNER_ID بمعرف صاحب الحساب
        return

    audio_name = event.pattern_match.group(1)
    await event.reply(f"࿊ مرحبًــا بـك عزيزي المنصـب، جاري البحث عن: {audio_name}...")

    # إعداد خيارات yt-dlp لتحميل الصوت فقط
    ydl_opts = {
        "format": "bestaudio/best",
        "extractaudio": True,  # استخراج الصوت فقط
        "outtmpl": "%(title)s.%(ext)s",
        "cookiefile": get_cookies_file(),
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            # البحث عن الصوت باستخدام اسم الصوت
            search_url = f"ytsearch:{audio_name}"
            info = ydl.extract_info(search_url, download=True)

            # تحقق من وجود 'title' في المعلومات المستخرجة
            if 'title' not in info or 'ext' not in info:
                await event.reply("❌ لم أتمكن من استخراج معلومات الصوت.")
                return

            title = info['title']
            filename = f"{title}.{info['ext']}"

            await event.reply(f"࿊ تم تحميـل الصوت: {title}\n⇜ انتظـر المعالجة جارية...")

            # إرسال الملف إلى تيليجرام
            await zedub.send_file(event.chat_id, filename)

            # حذف الملف بعد الإرسال
            os.remove(filename)
        except Exception as e:
            await event.reply(f"خطـــأ ❌: {e}")
