import datetime
import asyncio
import traceback
import json
import random
from enum import Enum

import discord
from discord.ext import commands
from discord.utils import get
import sqlite3
from textblob import TextBlob

with open('settings.json') as settings_file:
    settings = json.load(settings_file)

sql = sqlite3.connect('sql.db')
print('Loaded SQL Database')
cur = sql.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER, guild INTEGER, relationship INTEGER, with_id INTEGER, points INTEGER, ignore INTEGER)')
print('Loaded Users')
cur.execute('CREATE TABLE IF NOT EXISTS sex(id1 INTEGER, id2 INTEGER, guild INTEGER, random BIT, time DATETIME)')
print('Loaded Sex')
sql.commit()

username = settings["discord"]["description"]
version = settings["discord"]["version"]
command_prefix = settings["discord"]["command_prefix"]
start_time = datetime.datetime.utcnow()
client = commands.Bot(
    command_prefix=settings["discord"]["command_prefix"],
    description=settings["discord"]["description"])

print('{} - {}'.format(username, version))

class Relationship(Enum):
    Single = 1
    Dating = 2
    Married = 3

class Actions(Enum):
    fuck = 1
    date = 2
    marry = 3

class Results(Enum):
    accept = 1
    decline = 2
    timeout = 3

@client.command(pass_context=True, name="ping")
async def bot_ping(ctx):
    pong_message = await ctx.message.channel.send("Pong!")
    await asyncio.sleep(0.5)
    delta = pong_message.created_at - ctx.message.created_at
    millis = delta.days * 24 * 60 * 60 * 1000
    millis += delta.seconds * 1000
    millis += delta.microseconds / 1000
    await pong_message.edit(content="Pong! `{}ms`".format(int(millis)))


@client.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.errors.CommandNotFound):
        pass  # ...don't need to know if commands don't exist
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.message.channel.send(
            ctx.message.channel,
            '{} You don''t have permission to use this command.' \
            .format(ctx.message.author.mention))
    elif isinstance(error, commands.errors.CommandOnCooldown):
        try:
            await ctx.message.delete()
        except discord.errors.NotFound:
            pass
        await ctx.message.channel.send(
            ctx.message.channel, '{} This command was used {:.2f}s ago ' \
            'and is on cooldown. Try again in {:.2f}s.' \
            .format(ctx.message.author.mention,
                    error.cooldown.per - error.retry_after,
                    error.retry_after))
        await asyncio.sleep(10)
        await ctx.message.delete()
    else:
        await ctx.message.channel.send(
            'An error occured while processing the `{}` command.' \
            .format(ctx.command.name))
        print('Ignoring exception in command {0.command} ' \
            'in {0.message.channel}'.format(ctx))
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        print(''.join(tb))


@client.event
async def on_error(event_method, *args, **kwargs):
    if isinstance(args[0], commands.errors.CommandNotFound):
        # For some reason runs despite the above
        return
    print('Ignoring exception in {}'.format(event_method))
    mods_msg = "Exception occured in {}".format(event_method)
    tb = traceback.format_exc()
    print(''.join(tb))
    mods_msg += '\n```' + ''.join(tb) + '\n```'
    mods_msg += '\nargs: `{}`\n\nkwargs: `{}`'.format(args, kwargs)
    print(mods_msg)
    print(args)
    print(kwargs)


@client.event
async def on_ready():
    await asyncio.sleep(1)
    print("Logged in to discord.")
    try:
        await client.change_presence(
            activity=discord.Game(name=settings["discord"]["game"]),
            status=discord.Status.online,
            afk=False)
    except Exception as e:
        print('on_ready : ', e)
        pass
    await asyncio.sleep(1)


@client.command(pass_context=True, name='status')
async def status(ctx):
    try:
        # reply with embed of user's relationship and points status
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        users = ctx.message.mentions
        user = 0
        if len(users) > 1:
            await ctx.send("{0.author.mention} Please mention one user to check their status, or do not mention any to check your own.".format(ctx.message))
            return
        elif len(users) == 1:
            user = users[0]
        else:
            user = ctx.message.author
        cur.execute('SELECT count(*), id, relationship, score, ignore FROM users WHERE id=?', (ctx.message.author.id,))
        user = cur.fetchone()
        if int(user[0]) == 0 or int(user[4]) == 1:
            await ctx.send("{0.author.mention} That user does not appear to be playing.".format(ctx.message))
            return
        embed = discord.Embed(title='User Status', type='rich', color=0x77B255)
        embed.add_field(name='User:', value='{0.mention}'.format(user), inline=False)
        embed.add_field(name='Status:', value=Relationship(int(user[2])).name, inline=False)
        embed.add_field(name='Score:', value=str(int(user[3])), inline=False)
        await ctx.send(embed)
    except Exception as e:
        print('status : ', e)
        pass


def add_user(guild_id, user_id):
    try:
        cur.execute('SELECT count(*) FROM users WHERE guild=? AND id=?', (guild_id, user_id))
        user = cur.fetchone()
        if int(user[0]) == 0:
            cur.execute('INSERT INTO users VALUES(?,?,1,null,0,0)', (id,))
    except Exception as e:
        print('add_user : ', e)
        pass


def get_random_user(guild_id, calling_user_id, is_not_married):
    try:
        if is_not_married:
            cur.execute('SELECT id FROM users WHERE guild=? AND ignore=0 AND id<>? AND relationship<>3 ORDER BY RANDOM() LIMIT 1;', (guild_id, calling_user_id))
        else:
            cur.execute('SELECT id FROM users WHERE guild=? AND ignore=0 AND id<>? ORDER BY RANDOM() LIMIT 1;', (guild_id, calling_user_id))
        row = cur.fetchone()
        return get(client.get_all_members(), id=row[0])
    except Exception as e:
        print('get_random_user : ', e)
        pass


def add_fuck(guild_id, user1_id, user2_id):
    try:
        pass
    except Exception as e:
        print('add_fuck : ', e)
        pass


def has_recent_fuck(guild_id, user1_id, user2_id):
    try:
        pass
    except Exception as e:
        print('has_recent_fuck : ', e)
        pass 


def add_spouse(guild_id, user1_id, user2_id):
    try:
        cur.execute("UPDATE users SET relationship=3, with_id=? WHERE guild=? AND id=?", (user2_id, guild_id, user1_id))
        cur.execute("UPDATE users SET relationship=3, with_id=? WHERE guild=? AND id=?", (user1_id, guild_id, user2_id))
        sql.commit()
    except Exception as e:
        print('add_spouse : ', e)
        pass


def remove_spouse(guild_id, user1_id, user2_id):
    try:
        cur.execute("UPDATE users SET relationship=1, with_id=null WHERE guild=? AND id=?", (guild_id, user1_id))
        cur.execute("UPDATE users SET relationship=1, with_id=null WHERE guild=? AND id=?", (guild_id, user2_id))
        sql.commit()
    except Exception as e:
        print('remove_spouse : ', e)
        pass


def is_married(guild_id, user_id):
    try:
        cur.execute("SELECT count(*) FROM users WHERE guild=? AND id=? AND relationship=3", (guild_id, user_id))
        user = cur.fetchone()
        return int(user[0]) != 0
    except Exception as e:
        print('is_married : ', e)
        pass


def married_to_user(guild_id, user_id):
    try:
        cur.execute("SELECT count(*), with_id FROM users WHERE guild=? AND id=? AND relationship=3", (guild_id, user_id))
        user = cur.fetchone()
        if int(user[1]) != 0:
            return get(client.get_all_members(), id=user[1])
        else:
            return None
    except Exception as e:
        print('married_to_user : ', e)
        pass


def add_so(guild_id, user1_id, user2_id):
    try:
        cur.execute("UPDATE users SET relationship=2, with_id=? WHERE guild=? AND id=?", (user2_id, guild_id, user1_id))
        cur.execute("UPDATE users SET relationship=2, with_id=? WHERE guild=? AND id=?", (user1_id, guild_id, user2_id))
        sql.commit()
    except Exception as e:
        print('add_so : ', e)
        pass


def remove_so(guild_id, user1_id, user2_id):
    try:
        cur.execute("UPDATE users SET relationship=1, with_id=null WHERE guild=? AND id=?", (guild_id, user1_id))
        cur.execute("UPDATE users SET relationship=1, with_id=null WHERE guild=? AND id=?", (guild_id, user2_id))
        sql.commit()
    except Exception as e:
        print('remove_so : ', e)
        pass


def is_dating(guild_id, user_id):
    try:
        cur.execute("SELECT count(*) FROM users WHERE guild=? AND id=? AND relationship=2", (guild_id, user_id))
        user = cur.fetchone()
        return int(user[0]) != 0
    except Exception as e:
        print('remove_spouse : ', e)
        pass


def dating_user(guild_id, user_id):
    try:
        cur.execute("SELECT count(*), with_id FROM users WHERE guild=? AND id=? AND relationship=2", (guild_id, user_id))
        user = cur.fetchone()
        if int(user[1]) != 0:
            return get(client.get_all_members(), id=user[1])
        else:
            return None
    except Exception as e:
        print('dating_user : ', e)
        pass


def is_in_relationship(guild_id, user_id):
    try:
        cur.execute("SELECT count(*), id, relationship FROM users WHERE guild=? AND id=?", (guild_id, user_id))
        user = cur.fetchone()
        return int(user[0]) != 0 and int(user[2]) != 1
    except Exception as e:
        print('is_in_relationship : ', e)
        pass


@client.command(pass_context=True, name='fuck')
async def fuck(ctx):
    try:
        # fuck<mention> : attempt to fuck specified user (limited to 1)
        # fuck : choose a random active & online user to fuck
        #
        # target user will be asked if they want to fuck
        # if users both single, reward with 100 points each
        # if users dating eachother, reward with 50 points each
        # if users married to eachother, reward with 20 points
        # if one or both users in relationship with others, random probability of getting caught
        # if not caught, user(s) rewarded with 200 points
        # caught user's spouse asked if they want to divorce, SOs (dating) asked if want to split
        # if spouse chooses divorce, spouse takes half of cheaters points and both revert to single
        # if spouse declines divorce, both awarded 100 points
        # if SO chooses split, both revert to single
        # if SO delinces split, both awarded 50 points
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        users = ctx.message.mentions
        target = None
        if len(users) > 1:
            await ctx.send("{0.author.mention} Please mention one user to fuck, or do not mention any to fuck at random.".format(ctx.message))
            return
        elif len(users) == 1:
            target = users[0]
        else:
            target = get_random_user(ctx.message.guild.id, ctx.message.author.id, False)
        reply = await ctx.send("{0.mention} Looks like {1.mention} wants to bang.  You down?".format(target, ctx.message.author))
        await reply.add_reaction(reply, "✅")
        await reply.add_reaction(reply, "❌")
        try:
            answer = await reply.wait_for_reaction(emoji=["✅", "❌"], message=reply, timeout=60.0, check=lambda reaction, user: user == target)
        except asyncio.TimeoutError:
            return Results.timeout
        else:
            if answer.reaction.emoji == "✅":
                return Results.accept
            elif answer.reaction.emoji == "❌":
                return Results.decline
        if answer = Results.accept:

    except Exception as e:
        print('fuck : ', e)
        pass


@client.command(pass_context=True, name='date')
async def date(ctx):
    try:
        # date<mention> : attempt to date specified user (limited to 1)
        # date : choose a random active & online user to date
        #
        # if target user is single, will ask them if they want to date
        # if accepted, both users rewarded with 300 points
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        users = ctx.message.mentions
        target = None
        if len(users) > 1:
            await ctx.send("{0.author.mention} Please mention one user to date, or do not mention any to date at random.".format(ctx.message))
            return
        elif len(users) == 1:
            target = users[0]
        else:
            target = get_random_user(ctx.message.guild.id, ctx.message.author.id, False)
        reply = await ctx.send("{0.mention} Looks like {1.mention} wants to bang.  You down?".format(target, ctx.message.author))
        await reply.add_reaction(reply, "✅")
        await reply.add_reaction(reply, "❌")
        try:
            answer = await reply.wait_for_reaction(emoji=["✅", "❌"], message=reply, timeout=60.0, check=lambda reaction, user: user == target)
        except asyncio.TimeoutError:
            return Results.timeout
        else:
            if answer.reaction.emoji == "✅":
                return Results.accept
            elif answer.reaction.emoji == "❌":
                return Results.decline

    except Exception as e:
        print('date : ', e)
        pass


@client.command(pass_context=True, name='marry')
async def marry(ctx):
    try:
        # marry<mention> : attempt to marry specified user (limited to 1)
        # marry : choose a random active & online user to marry
        #
        # if target user is single, will ask them if they want to marry
        # if accepted, both users rewarded with 500 points
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        users = ctx.message.mentions
        target = None
        if len(users) > 1:
            await ctx.send("{0.author.mention} Please mention one user to marry, or do not mention any to marry at random.".format(ctx.message))
            return
        elif len(users) == 1:
            target = users[0]
        else:
            target = get_random_user(ctx.message.guild.id, ctx.message.author.id, False)
        reply = await ctx.send("{0.mention} Looks like {1.mention} wants to bang.  You down?".format(target, ctx.message.author))
        await reply.add_reaction(reply, "✅")
        await reply.add_reaction(reply, "❌")
        try:
            answer = await reply.wait_for_reaction(emoji=["✅", "❌"], message=reply, timeout=60.0, check=lambda reaction, user: user == target)
        except asyncio.TimeoutError:
            return Results.timeout
        else:
            if answer.reaction.emoji == "✅":
                return Results.accept
            elif answer.reaction.emoji == "❌":
                return Results.decline
            
    except Exception as e:
        print('marry : ', e)
        pass


@client.command(pass_context=True, name='divorce')
async def divorce(ctx):
    try:
        # divorce<mention> : attempt to divorce specified user (limited to 1)
        # divorce : choose a random active & online user to divorce
        # if accepted, both users points totalled up, then each user left with 25% (lawyers take the other half lmao)
        # if declined, asking user loses random amount of points to ex-spouse
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        divorcees = ctx.message.mentions
        if len(divorcees) != 0:
            pass
        # need to add divorce actions:
        #   look up spouse
        #   create pending action for spouse to reply
    except Exception as e:
        print('divorce : ', e)
        pass


# @client.event
# async def on_raw_reaction_add(ctx):
#     try:
#         cur.execute('SELECT count(*), id1, id2, guild, message, action FROM pending WHERE message=?;', (ctx.message.id,))
#         row = cur.fetchone()
#         if int(row[0]) == 0:
#             return
        
#     except Exception as e:
#         print('on_raw_reaction_add : ', e)
#         pass


# @client.event
# async def on_message(message):
#     try:
#         pass
#     except Exception as e:
#         print('on_message : ', e)
#         pass


# @client.command(pass_context=True, name='check')
# async def check(ctx):
#     try:
#         pass
#     except Exception as e:
#         print('check : ', e)
#         pass


# @client.command(pass_context=True, name='optin')
# async def opt_in(ctx):
#     try:
#         if ctx.message.author == client.user or ctx.message.author.bot:
#             return
#         cur.execute('SELECT count(*), ignore from users where id=?', (ctx.message.author.id,))
#         user = cur.fetchone()
#         if int(user[0]) != 0:
#             cur.execute('UPDATE users SET ignore = 0 WHERE id=?', (ctx.message.author.id,))
#         else:
#             cur.execute('INSERT INTO users VALUES(?,0,0,0)', (ctx.message.author.id,))
#         sql.commit()
#         cur.execute('VACUUM')
#         await ctx.send("Hi {0.author.mention}!  Let's start being positive!".format(ctx.message))
#     except Exception as e:
#         print('opt_in : ', e)
#         pass


# @client.command(pass_context=True, name='optout')
# async def opt_out(ctx):
#     try:
#         if ctx.message.author == client.user or ctx.message.author.bot:
#             return
#         cur.execute('SELECT count(*), ignore from users where id=?', (ctx.message.author.id,))
#         user = cur.fetchone()
#         if int(user[0]) != 0:
#             cur.execute('UPDATE users SET ignore = 1 WHERE id=?', (ctx.message.author.id,))
#         else:
#             cur.execute('INSERT INTO users VALUES(?,0,0,1)', (ctx.message.author.id,))
#         sql.commit()
#         cur.execute('VACUUM')
#         await ctx.send("Sorry to see you go, {0.author.mention}!".format(ctx.message))
#     except Exception as e:
#         print('opt_out : ', e)
#         pass


client.run(settings["discord"]["client_token"])
