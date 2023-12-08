import os
import asyncio
import logging
from Tepthon import zedub
from Tepthon.core.managers import edit_delete, edit_or_reply
from Tepthon.helpers.utils import mentionuser
from telethon import functions
from telethon.errors import ChatAdminRequiredError, UserAlreadyInvitedError
from telethon.tl.types import Channel, Chat, User
from pathlib import Path
import requests
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.exceptions import (
    AlreadyJoinedError,
    NoActiveGroupCall,
    NotInGroupCallError,
)
from pytgcalls.types import AudioPiped, AudioVideoPiped
from pytgcalls.types.stream import StreamAudioEnded
from telethon import functions
from telethon.errors import ChatAdminRequiredError
from yt_dlp import YoutubeDL
from .stream_helper import Stream, check_url, video_dl, yt_regex


class thesource:
    def __init__(self, client) -> None:
        self.app = PyTgCalls(client, overload_quiet_mode=True)
        self.client = client
        self.CHAT_ID = None
        self.CHAT_NAME = None
        self.PLAYING = False
        self.PAUSED = False
        self.MUTED = False
        self.PLAYLIST = []

    async def start(self):
        await self.app.start()

    def clear_vars(self):
        self.CHAT_ID = None
        self.CHAT_NAME = None
        self.PLAYING = False
        self.PAUSED = False
        self.MUTED = False
        self.PLAYLIST = []

    async def join_vc(self, chat, join_as=None):
        if self.CHAT_ID:
            return f"موجود بالفعل في المكالمة الصوتية {self.CHAT_NAME}"
        if join_as:
            try:
                join_as_chat = await self.client.get_entity(int(join_as))
                join_as_title = f" على **{join_as_chat.title}**"
            except ValueError:
                return "عليك كتابة ايدي الدردشة للأنضمام"
        else:
            join_as_chat = await self.client.get_me()
            join_as_title = "𝗧𝗘𝗣𝗧𝗛𝗢𝗡 𝗤𝗨𝗥𝗔𝗡"
        try:
            await self.app.join_group_call(
                chat_id=chat.id,
                stream=AudioPiped("thesource/tgcalls/Silence01s.mp3"),
                join_as=join_as_chat,
                stream_type=StreamType().pulse_stream,
            )
        except NoActiveGroupCall:
            try:
                await self.client(
                    functions.phone.CreateGroupCallRequest(
                        peer=chat,
                        title="TepThon Quran",
                    )
                )
                await self.join_vc(chat=chat, join_as=join_as)
            except ChatAdminRequiredError:
                return "- عليك ان تكون مشرف في الدردشة اولا"
        except AlreadyJoinedError:
            await self.app.leave_group_call(chat.id)
            await asyncio.sleep(3)
            await self.join_vc(chat=chat, join_as=join_as)
        self.CHAT_ID = chat.id
        self.CHAT_NAME = chat.title
        return f"- تم الانضمام الى الدردشة : **{chat.title}**{join_as_title}"

    async def leave_vc(self):
        try:
            await self.app.leave_group_call(self.CHAT_ID)
        except (NotInGroupCallError, NoActiveGroupCall):
            pass
        self.CHAT_NAME = None
        self.CHAT_ID = None
        self.PLAYING = False
        self.PLAYLIST = []

    async def play_song(self, input, stream=Stream.audio, force=False):
        if yt_regex.match(input):
            with YoutubeDL({}) as ytdl:
                ytdl_data = ytdl.extract_info(input, download=False)
                title = ytdl_data.get("title", None)
            if title:
                playable = await video_dl(input, title)
            else:
                return "خطأ اثناء التعرف على الرابط"
        elif check_url(input):
            try:
                res = requests.get(input, allow_redirects=True, stream=True)
                ctype = res.headers.get("Content-Type")
                if "video" not in ctype or "audio" not in ctype:
                    return "الرابط غير صحيح"
                name = res.headers.get("Content-Disposition", None)
                if name:
                    title = name.split('="')[0].split('"') or ""
                else:
                    title = input
                playable = input
            except Exception as e:
                return f"الرابط غير صحيح\n\n{e}"
        else:
            path = Path(input)
            if path.exists():
                if not path.name.endswith(
                    (".mkv", ".mp4", ".webm", ".m4v", ".mp3", ".flac", ".wav", ".m4a")
                ):
                    return "- هذا الملف غير صحيح ليتم تشغيله"
                playable = str(path.absolute())
                title = path.name
            else:
                return "مسار الملف غير صحيح"
        print(playable)
        if self.PLAYING and not force:
            self.PLAYLIST.append({"title": title, "path": playable, "stream": stream})
            return f"- تمت اضافته الى قائمة التشغيل.\n الموقع: {len(self.PLAYLIST)+1}"
        if not self.PLAYING:
            self.PLAYLIST.append({"title": title, "path": playable, "stream": stream})
            await self.skip()
            return f"يتم تشغيل {title}"
        if force and self.PLAYING:
            self.PLAYLIST.insert(
                0, {"title": title, "path": playable, "stream": stream}
            )
            await self.skip()
            return f"يتم تشغيل {title}"

    async def handle_next(self, update):
        if isinstance(update, StreamAudioEnded):
            await self.skip()

    async def skip(self, clear=False):
        if clear:
            self.PLAYLIST = []

        if not self.PLAYLIST:
            if self.PLAYING:
                await self.app.change_stream(
                    self.CHAT_ID,
                    AudioPiped("thesource/tgcalls/Silence01s.mp3"),
                )
            self.PLAYING = False
            return "- تم تخطي التشغيل الحالي\nقائمة التشغيل فارغة"

        next = self.PLAYLIST.pop(0)
        if next["stream"] == Stream.audio:
            streamable = AudioPiped(next["path"])
        else:
            streamable = AudioVideoPiped(next["path"])
        try:
            await self.app.change_stream(self.CHAT_ID, streamable)
        except Exception:
            await self.skip()
        self.PLAYING = next
        return f"- تم تخطي التشغيل الحالي\nيتم تشغيل : `{next['title']}`"

    async def pause(self):
        if not self.PLAYING:
            return "- لم يتم تشغيل شيء لأيقافه"
        if not self.PAUSED:
            await self.app.pause_stream(self.CHAT_ID)
            self.PAUSED = True
        return f"- تم الايقاف المؤقت في {self.CHAT_NAME}"

    async def resume(self):
        if not self.PLAYING:
            return "- لم يتم تشغيل شي لأستأنافه"
        if self.PAUSED:
            await self.app.resume_stream(self.CHAT_ID)
            self.PAUSED = False
        return f"- تم الاستئناف في {self.CHAT_NAME}"

@zedub.zed_cmd(pattern="انضمام")
async def joinVoicechat(event):
    chat = event.pattern_match.group(1)
    joinas = event.pattern_match.group(2)

    await edit_or_reply(event, "**جار الانضمام للمكالمة الصوتية**")

    if chat and chat != "-as":
        if chat.strip("-").isnumeric():
            chat = int(chat)
    else:
        chat = event.chat_id

    if vc_player.app.active_calls:
        return await edit_delete(
            event, f"لقد انضممت بالفعل الى {vc_player.CHAT_NAME}"
        )

    try:
        vc_chat = await zedub.get_entity(chat)
    except Exception as e:
        return await edit_delete(event, f'ERROR : \n{e or "UNKNOWN CHAT"}')

    if isinstance(vc_chat, User):
        return await edit_delete(
            event, "لايمكنك استعمال اوامر القرآن على الخاص فقط في المجموعات !"
        )

    if joinas and not vc_chat.username:
        await edit_or_reply(
            event, "**لايمكنك استعمال اوامر القرآن على الخاص فقط في المجموعات !**"
        )
        joinas = False

    out = await vc_player.join_vc(vc_chat, joinas)
    await edit_delete(event, out)


@zedub.zed_cmd(pattern="مغادرة")
async def leaveVoicechat(event):
    if vc_player.CHAT_ID:
        await edit_or_reply(event, "** تم مغادرة من الاتصال 🥢 **")
        chat_name = vc_player.CHAT_NAME
        await vc_player.leave_vc()
        await edit_delete(event, f"تمت المغادرة من {chat_name}")
    else:
        await edit_delete(event, "** انا لست منضم الى الاتصال 🥢**")


@zedub.zed_cmd(pattern="قائمة_التشغيل")
async def get_playlist(event):
    await edit_or_reply(event, "**جارِ جلب قائمة التشغيل**")
    playl = vc_player.PLAYLIST
    if not playl:
        await edit_delete(event, "Playlist empty", time=10)
    else:
        matrix = ""
        for num, item in enumerate(playl, 1):
            if item["stream"] == Stream.audio:
                matrix += f"{num}. 🔉  `{item['title']}`\n"
            else:
                matrix += f"{num}. 📺  `{item['title']}`\n"
        await edit_delete(event, f"**قائمة التشغيل:**\n\n{matrix}\n**-**")

def convert_youtube_link_to_name(link):
    with youtube_dl.YoutubeDL({}) as ydl:
        info = ydl.extract_info(link, download=False)
        title = info['title']
    return title

@zedub.zed_cmd(pattern="تشغيل")
async def play_audio(event):
    flag = event.pattern_match.group(1)
    input_str = event.pattern_match.group(2)
    if input_str == "" and event.reply_to_msg_id:
        input_str = await tg_dl(event)
    if not input_str:
        return await edit_delete(
            event, "**قم بالرد على ملف صوتي او رابط يوتيوب**", time=20
        )
    if not vc_player.CHAT_ID:
        return await edit_or_reply(event, "**`قم بلانضمام للمكالمة اولاً بأستخدام أمر `انضمام")
    if not input_str:
        return await edit_or_reply(event, "No Input to play in quran")
    await edit_or_reply(event, "**يتم الان تشغيل القرآن في الاتصال**")
    if flag:
        resp = await vc_player.play_song(input_str, Stream.audio, force=True)
    else:
        resp = await vc_player.play_song(input_str, Stream.audio, force=False)
    if resp:
        await edit_delete(event, resp, time=30)
        
@zedub.zed_cmd(pattern="ايقاف_مؤقت")
async def pause_stream(event):
    await edit_or_reply(event, "**تم ايقاف القرآن مؤقتاً ⏸**")
    res = await vc_player.pause()
    await edit_delete(event, res, time=30)


@zedub.zed_cmd(pattern="استمرار")
async def resume_stream(event):
    await edit_or_reply(event, "**تم استمرار القرآن الكريم ▶️**")
    res = await vc_player.resume()
    await edit_delete(event, res, time=30)


@zedub.zed_cmd(pattern="تخطي")
async def skip_stream(event):
    await edit_or_reply(event, "**تم تخطي القرآن وتشغيل القرآن التالي**")
    res = await vc_player.skip()
    await edit_delete(event, res, time=30)


async def get_group_call(chat):
    if isinstance(chat, Channel):
        result = await zedub(functions.channels.GetFullChannelRequest(channel=chat))
    elif isinstance(chat, Chat):
        result = await zedub(functions.messages.GetFullChatRequest(chat_id=chat.id))
    return result.full_chat.call


async def chat_vc_checker(event, chat, edits=True):
    if isinstance(chat, User):
        await edit_delete(event, "**لايمكنك تشغيل القرآن في المكالمات الخاصه**")
        return None
    result = await get_group_call(chat)
    if not result:
        if edits:
            await edit_delete(event, "** لا توجد مكالمة صوتية في هذه الدردشه**")
        return None
    return result


async def parse_entity(entity):
    if entity.isnumeric():
        entity = int(entity)
    return await zedub.get_entity(entity)


@zedub.zed_cmd(pattern="تشغيل_المكالمة")
async def start_vc(event):
    vc_chat = await zedub.get_entity(event.chat_id)
    gc_call = await chat_vc_checker(event, vc_chat, False)
    if gc_call:
        return await edit_delete(
            event, "**- المكالمة الصوتية بالفعل مشغلة بهذه الدردشة**"
        )
    try:
        await zedub(
            functions.phone.CreateGroupCallRequest(
                peer=vc_chat,
                title="𝗧𝗘𝗣𝗧𝗛𝗢𝗡 𝗤𝗨𝗥𝗔𝗡",
            )
        )
        await edit_delete(event, "**- تم بنجاح تشغيل المكالمة الصوتية**")
    except ChatAdminRequiredError:
        await edit_delete(event, "**- يجب ان تكون ادمن لتشغيل المكالمة هنا**", time=20)


@zedub.zed_cmd(pattern="انهاء_المكالمة")
async def end_vc(event):
    vc_chat = await zedub.get_entity(event.chat_id)
    gc_call = await chat_vc_checker(event, vc_chat)
    if not gc_call:
        return
    try:
        await zedub(functions.phone.DiscardGroupCallRequest(call=gc_call))
        await edit_delete(event, "**- تم بنجاح انهاء المكالمة الصوتية**")
    except ChatAdminRequiredError:
        await edit_delete(
            event, "**- يجب ان تكون مشرف لأنهاء المكالمة الصوتية**", time=20
        )


@zedub.zed_cmd(pattern="دعوة ?(.*)?")
async def inv_vc(event):
    users = event.pattern_match.group(1)
    reply = await event.get_reply_message()
    vc_chat = await zedub.get_entity(event.chat_id)
    gc_call = await chat_vc_checker(event, vc_chat)
    if not gc_call:
        return
    if not users:
        if not reply:
            return await edit_delete(
                "**- يجب عليك الرد على المستخدم او وضع معرفه مع الامر**"
            )
        users = reply.from_id
    await edit_or_reply(event, "**- تم بنجاح دعوة المستخدم**")
    entities = str(users).split(" ")
    user_list = []
    for entity in entities:
        cc = await parse_entity(entity)
        if isinstance(cc, User):
            user_list.append(cc)
    try:
        await zedub(
            functions.phone.InviteToGroupCallRequest(call=gc_call, users=user_list)
        )
        await edit_delete(event, "**- تم بنجاح دعوة المستخدمين**")
    except UserAlreadyInvitedError:
        return await edit_delete(event, "- تم دعوة المستخدم بالاصل", time=20)


@zedub.zed_cmd(pattern="معلومات_المكالمة")
async def info_vc(event):
    vc_chat = await zedub.get_entity(event.chat_id)
    gc_call = await chat_vc_checker(event, vc_chat)
    if not gc_call:
        return
    await edit_or_reply(event, "**- جار جلب معلومات المكالمة انتظر قليلا**")
    call_details = await zedub(
        functions.phone.GetGroupCallRequest(call=gc_call, limit=1)
    )
    grp_call = "**معلومات مكالمة المجموعة**\n\n"
    grp_call += f"**العنوان :** {call_details.call.title}\n"
    grp_call += f"**عدد المشاركين :** {call_details.call.participants_count}\n\n"

    if call_details.call.participants_count > 0:
        grp_call += "**المشاركون**\n"
        for user in call_details.users:
            nam = f"{user.first_name or ''} {user.last_name or ''}"
            grp_call += f"  ● {mentionuser(nam,user.id)} - `{user.id}`\n"
    await edit_or_reply(event, grp_call)


@zedub.zed_cmd(pattern="تسمية_المكالمة?(.*)?")
async def title_vc(event):
    title = event.pattern_match.group(1)
    vc_chat = await zedub.get_entity(event.chat_id)
    gc_call = await chat_vc_checker(event, vc_chat)
    if not gc_call:
        return
    if not title:
        return await edit_delete("**- يجب عليك كتابة العنوان مع الامر**")
    await zedub(functions.phone.EditGroupCallTitleRequest(call=gc_call, title=title))
    await edit_delete(event, f"- تم بنجاح تغيير اسم المكالمة الى **{title}**")
