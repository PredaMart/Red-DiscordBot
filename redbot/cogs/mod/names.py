from datetime import datetime
from typing import cast

import discord
from discord import ActivityType
from redbot.core import commands, i18n, checks
from redbot.core.utils.common_filters import (
    filter_invites,
    filter_various_mentions,
    escape_spoilers_and_mass_mentions,
)
from redbot.core.utils.mod import get_audit_reason
from .abc import MixinMeta

_ = i18n.Translator("Mod", __file__)


class ModInfo(MixinMeta):
    """
    Commands regarding names, userinfo, etc.
    """

    async def get_names_and_nicks(self, user):
        names = await self.settings.user(user).past_names()
        nicks = await self.settings.member(user).past_nicks()
        if names:
            names = [escape_spoilers_and_mass_mentions(name) for name in names if name]
        if nicks:
            nicks = [escape_spoilers_and_mass_mentions(nick) for nick in nicks if nick]
        return names, nicks

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_nicknames=True)
    @checks.admin_or_permissions(manage_nicknames=True)
    async def rename(self, ctx: commands.Context, user: discord.Member, *, nickname: str = ""):
        """Change a user's nickname.

        Leaving the nickname empty will remove it.
        """
        nickname = nickname.strip()
        me = cast(discord.Member, ctx.me)
        if not nickname:
            nickname = None
        elif not 2 <= len(nickname) <= 32:
            await ctx.send(_("Nicknames must be between 2 and 32 characters long."))
            return
        if not (
            (me.guild_permissions.manage_nicknames or me.guild_permissions.administrator)
            and me.top_role > user.top_role
            and user != ctx.guild.owner
        ):
            await ctx.send(
                _(
                    "I do not have permission to rename that member. They may be higher than or "
                    "equal to me in the role hierarchy."
                )
            )
        else:
            try:
                await user.edit(reason=get_audit_reason(ctx.author, None), nick=nickname)
            except discord.Forbidden:
                # Just in case we missed something in the permissions check above
                await ctx.send(_("I do not have permission to rename that member."))
            except discord.HTTPException as exc:
                if exc.status == 400:  # BAD REQUEST
                    await ctx.send(_("That nickname is invalid."))
                else:
                    await ctx.send(_("An unexpected error has occured."))
            else:
                await ctx.send(_("Done."))

    def handle_custom(self, user):
        print(user.activities)
        a = [c for c in user.activities if c.type == ActivityType.custom]
        if not a:
            return None, ActivityType.custom
        a = a[0]
        c_status = None
        if not a.name:
            c_status = self.bot.get_emoji(a.emoji.id)
        if c_status:
            pass
        if a.name and a.emoji:
            c_status = f"{a.emoji} {a.name}"
        elif a.emoji and not c_status:
            c_status = f"{a.emoji}"
        elif a.name:
            c_status = a.name
        else:
            c_status = None
        return c_status, ActivityType.custom

    def handle_playing(self, user):
        p_acts = [c for c in user.activities if c.type == ActivityType.playing]
        p_act = p_acts[0] if p_acts else None
        act = p_act.name if p_act and p_act.name else None
        return act, ActivityType.playing
    def handle_streaming(self, user):
        s_acts = [c for c in user.activities if c.type == ActivityType.streaming]
        s_act = s_acts[0] if s_acts else None
        act = f"[{s_act.name}{' | ' if s_act.game else ''}{s_act.game or ''}]({s_act.url})" if s_act and s_act.name and hasattr(s_act, "game") else s_act.name if s_act and s_act.name else None
        return act, ActivityType.streaming
    def handle_listening(self, user):
        l_acts = [c for c in user.activities if c.type == ActivityType.listening]
        l_act = l_acts[0] if l_acts else None
        act = f"[{l_act.title}{' | ' if l_act.artists[0] else ''}{l_act.artists[0] or ''}](https://open.spotify.com/track/{l_act.track_id})" if l_act and hasattr(l_act, "title") else l_act.name if l_act and l_act.name else None
        return act, ActivityType.listening
    def handle_watching(self, user):
        w_acts = [c for c in user.activities if c.type == ActivityType.watching]
        w_act = w_acts[0] if w_acts else None
        act = w_act.name if w_act else None
        return act, ActivityType.watching

    def get_status_string(self, user):
        string = ""
        for a in [self.handle_custom(user), self.handle_playing(user), self.handle_listening(user), self.handle_streaming(user), self.handle_watching(user)]:
            status_string, status_type= a
            if status_string is None:
                continue
            if status_type == discord.ActivityType.custom:
                string += f"Custom: {status_string}\n"
            elif status_type == discord.ActivityType.playing:
                string += f"Playing: {status_string}\n"
            elif status_type == discord.ActivityType.streaming:
                string += f"Streaming: {status_string}\n"
            elif status_type == discord.ActivityType.listening:
                string += f"Listening: {status_string}\n"
            elif status_type == discord.ActivityType.watching:
                string += f"Watching: {status_string}\n"
        return string
    
    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def userinfo(self, ctx, *, user: discord.Member = None):
        """Show information about a user.
        This includes fields for status, discord join date, server
        join date, voice state and previous names/nicknames.
        If the user has no roles, previous names or previous nicknames,
        these fields will be omitted.
        """
        author = ctx.author
        guild = ctx.guild

        if not user:
            user = author

        #  A special case for a special someone :^)
        special_date = datetime(2016, 1, 10, 6, 8, 4, 443000)
        is_special = user.id == 96130341705637888 and guild.id == 133049272517001216

        roles = user.roles[-1:0:-1]
        names, nicks = await self.get_names_and_nicks(user)

        joined_at = user.joined_at if not is_special else special_date
        since_created = (ctx.message.created_at - user.created_at).days
        if joined_at is not None:
            since_joined = (ctx.message.created_at - joined_at).days
            user_joined = joined_at.strftime("%d %b %Y %H:%M")
        else:
            since_joined = "?"
            user_joined = _("Unknown")
        user_created = user.created_at.strftime("%d %b %Y %H:%M")
        voice_state = user.voice
        member_number = (
            sorted(guild.members, key=lambda m: m.joined_at or ctx.message.created_at).index(user)
            + 1
        )

        created_on = _("{}\n({} days ago)").format(user_created, since_created)
        joined_on = _("{}\n({} days ago)").format(user_joined, since_joined)

        if user.status.name == "online":
            if user.is_on_mobile() is True:
                statusemoji = "https://cdn.discordapp.com/emojis/554418132953989140.png?v=1"
            else:
                statusemoji = "https://cdn.discordapp.com/emojis/642458713738838017.png?v=1"
        elif user.status.name == "offline":
            statusemoji = "https://cdn.discordapp.com/emojis/642458714074513427.png?v=1"
        elif user.status.name == "dnd":
            statusemoji = "https://cdn.discordapp.com/emojis/642458714145816602.png?v=1"
        elif user.status.name == "streaming":
            statusemoji = "https://cdn.discordapp.com/emojis/642458713692569602.png?v=1"
        elif user.status.name == "idle":
            statusemoji = "https://cdn.discordapp.com/emojis/642458714003210240.png?v=1"

        activity = _("Chilling in {} status").format(user.status)
        status_string = self.get_status_string(user)

        if roles:
            role_str = ", ".join([x.mention for x in roles])
            # 400 BAD REQUEST (error code: 50035): Invalid Form Body
            # In embed.fields.2.value: Must be 1024 or fewer in length.
            if len(role_str) > 1024:
                # Alternative string building time.
                # This is not the most optimal, but if you're hitting this, you are losing more time
                # to every single check running on users than the occasional user info invoke
                # We don't start by building this way, since the number of times we hit this should be
                # infintesimally small compared to when we don't across all uses of Red.
                continuation_string = _(
                    "and {numeric_number} more roles not displayed due to embed limits."
                )
                available_length = 1024 - len(continuation_string)  # do not attempt to tweak, i18n

                role_chunks = []
                remaining_roles = 0

                for r in roles:
                    chunk = f"{r.mention}, "
                    chunk_size = len(chunk)

                    if chunk_size < available_length:
                        available_length -= chunk_size
                        role_chunks.append(chunk)
                    else:
                        remaining_roles += 1

                role_chunks.append(continuation_string.format(numeric_number=remaining_roles))

                role_str = "".join(role_chunks)

        else:
            role_str = None

        data = discord.Embed(description=status_string or activity, colour=user.colour)
            
        data.add_field(name=_("Joined Discord on"), value=created_on)
        data.add_field(name=_("Joined this server on"), value=joined_on)
        if role_str is not None:
            data.add_field(name=_("Roles"), value=role_str, inline=False)
        if names:
            # May need sanitizing later, but mentions do not ping in embeds currently
            val = filter_invites(", ".join(names))
            data.add_field(name=_("Previous Names"), value=val, inline=False)
        if nicks:
            # May need sanitizing later, but mentions do not ping in embeds currently
            val = filter_invites(", ".join(nicks))
            data.add_field(name=_("Previous Nicknames"), value=val, inline=False)
        if voice_state and voice_state.channel:
            data.add_field(
                name=_("Current voice channel"),
                value="{0.mention} ID: {0.id}".format(voice_state.channel),
                inline=False,
            )
        data.set_footer(text=_("Member #{} | User ID: {}").format(member_number, user.id))

        name = str(user)
        name = " ~ ".join((name, user.nick)) if user.nick else name
        name = filter_invites(name)

        if user.avatar:
            avatar = user.avatar_url_as(static_format="png")
            data.set_author(name=name, url=avatar, icon_url=statusemoji)
            data.set_thumbnail(url=avatar)
        else:
            data.set_author(name=name)

        await ctx.send(embed=data)

    @commands.command()
    async def names(self, ctx: commands.Context, *, user: discord.Member):
        """Show previous names and nicknames of a user."""
        names, nicks = await self.get_names_and_nicks(user)
        msg = ""
        if names:
            msg += _("**Past 20 names**:")
            msg += "\n"
            msg += ", ".join(names)
        if nicks:
            if msg:
                msg += "\n\n"
            msg += _("**Past 20 nicknames**:")
            msg += "\n"
            msg += ", ".join(nicks)
        if msg:
            msg = filter_various_mentions(msg)
            await ctx.send(msg)
        else:
            await ctx.send(_("That user doesn't have any recorded name or nickname change."))
