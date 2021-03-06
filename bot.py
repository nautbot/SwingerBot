import datetime, time
import asyncio
import traceback
import json
import random
from enum import Enum

import discord
from discord.ext import commands
from discord.utils import get
import sqlite3

with open('settings.json') as settings_file:
    settings = json.load(settings_file)

sql = sqlite3.connect('sql.db')
print('Loaded SQL Database')
cur = sql.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER, guild INTEGER, relationship INTEGER, with_id INTEGER, score INTEGER, ignore INTEGER)')
print('Loaded Users')
cur.execute('CREATE TABLE IF NOT EXISTS sex(id1 INTEGER, id2 INTEGER, guild INTEGER, timestamp FLOAT)')
print('Loaded Sex')
sql.commit()

username = settings["discord"]["description"]
version = settings["discord"]["version"]
command_prefix = settings["discord"]["command_prefix"]
start_time = datetime.datetime.utcnow()
client = commands.Bot(
    command_prefix=settings["discord"]["command_prefix"],
    description=settings["discord"]["description"])

client.remove_command("help")

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
    mods_msg += '\n`' + ''.join(tb) + '\n`'
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


def user_exists(guild_id, user_id):
    try:
        cur.execute('SELECT count(*) FROM users WHERE guild=? AND id=?', (guild_id, user_id))
        user = cur.fetchone()
        return int(user[0]) != 0
    except Exception as e:
        print('user_exists : ', e)
        pass


def get_user_info(guild_id, user_id):
    try:
        if user_exists(guild_id, user_id):
            cur.execute('SELECT relationship, score FROM users WHERE guild=? AND id=?', (guild_id, user_id))
            user = cur.fetchone()
            relationship = Relationship(int(user[0]))
            score = int(user[1])
            return relationship, score
        else:
            relationship = Relationship.Single
            score = 0
            return relationship, score
    except Exception as e:
        print('get_user_info : ', e)
        pass

def user_ignored(guild_id, user_id):
    try:
        if user_exists(guild_id, user_id):
            cur.execute("SELECT ignore FROM users WHERE guild=? AND id=?", (guild_id, user_id))
            user = cur.fetchone()
            return int(user[0])==1
        else:
            return True
    except Exception as e:
        print('user_exists : ', e)
        pass


def add_user(guild_id, user_id):
    try:
        if not user_exists(guild_id, user_id):
            cur.execute('INSERT INTO users VALUES(?,?,1,0,0,0)', (user_id, guild_id))
        else:
            cur.execute('UPDATE users SET ignore=0 WHERE guild=? AND id=?', (guild_id, user_id))
        sql.commit()
        cur.execute('VACUUM')
    except Exception as e:
        print('add_user : ', e)
        pass


def opt_out_user(guild_id, user_id):
    try:
        if user_exists(guild_id, user_id):
            cur.execute('UPDATE users SET relationship=1, with_id=0, score=0, ignore=1 WHERE guild=? AND id=?', (guild_id, user_id))
        else:
            cur.execute('INSERT INTO users VALUES(?,?,1,0,0,1)', (user_id,guild_id))
        sql.commit()
        cur.execute('VACUUM')
    except Exception as e:
        print('add_user : ', e)
        pass


def get_random_user(guild_id, calling_user_id, is_not_married):
    try:
        if is_not_married:
            cur.execute('SELECT id FROM users WHERE guild=? AND ignore=0 AND id<>? AND relationship<>2 AND relationship<>3 ORDER BY RANDOM() LIMIT 1;', (guild_id, calling_user_id))
        else:
            cur.execute('SELECT id FROM users WHERE guild=? AND ignore=0 AND id<>? ORDER BY RANDOM() LIMIT 1;', (guild_id, calling_user_id))
        row = cur.fetchone()
        return get(client.get_all_members(), id=row[0])
    except Exception as e:
        print('get_random_user : ', e)
        pass


def get_score(guild_id, user_id):
    try:
        if user_exists(guild_id, user_id):
            cur.execute("SELECT score FROM users WHERE guild=? AND id=? AND relationship=3", (guild_id, user_id))
            user = cur.fetchone()
            return int(user[0])
        else:
            return 0
    except Exception as e:
        print('get_score : ', e)
        pass


def update_score(guild_id, user_id, new_score):
    try:
        if user_exists(guild_id, user_id):
            cur.execute("UPDATE users SET score=? WHERE guild=? AND id=?", (int(new_score), guild_id, user_id))
            sql.commit()
            cur.execute('VACUUM')
            return True
        return False
    except Exception as e:
        print('update_score : ', e)
        pass


def increment_score(guild_id, user_id, increment):
    try:
        if user_exists(guild_id, user_id):
            cur.execute("UPDATE users SET score=score+? WHERE guild=? AND id=?", (int(increment), guild_id, user_id))
            sql.commit()
            cur.execute('VACUUM')
            return True
        return False
    except Exception as e:
        print('update_score : ', e)
        pass


def add_fuck(guild_id, user1_id, user2_id):
    try:
        if user_exists(guild_id, user1_id) and user_exists(guild_id, user2_id):
            remove_all_fucks(guild_id, user1_id, user2_id)
            cur.execute('INSERT INTO sex VALUES(?,?,?,?)', (user1_id, user2_id, guild_id, time.time()))
            sql.commit()
            cur.execute('VACUUM')
            return True
        return False
    except Exception as e:
        print('add_fuck : ', e)
        pass


def most_recent_fuck(guild_id, user1_id, user2_id):
    try:
        cur.execute('SELECT count(*), timestamp FROM sex WHERE guild=? AND ((id1=? AND id2=?) OR (id1=? AND id2=?)) ORDER BY 1 DESC LIMIT 1', (guild_id, user1_id, user2_id, user2_id, user1_id))
        encounter = cur.fetchone()
        return float(encounter[1]) if int(encounter[0])!=0 else 0.0
    except Exception as e:
        print('most_recent_fuck : ', e)
        pass


def remove_all_fucks(guild_id, user1_id, user2_id):
    try:
        if user_exists(guild_id, user1_id) and user_exists(guild_id, user2_id):
            cur.execute('DELETE FROM sex WHERE guild=? AND ((id1=? AND id2=?) OR (id1=? AND id2=?))', (guild_id, user1_id, user2_id, user2_id, user1_id))
            sql.commit()
            cur.execute('VACUUM')
            return True
        return False
    except Exception as e:
        print('remove_all_fucks : ', e)
        pass


def add_spouse(guild_id, user1_id, user2_id):
    try:
        cur.execute("UPDATE users SET relationship=3, with_id=? WHERE guild=? AND id=?", (user2_id, guild_id, user1_id))
        cur.execute("UPDATE users SET relationship=3, with_id=? WHERE guild=? AND id=?", (user1_id, guild_id, user2_id))
        sql.commit()
        cur.execute('VACUUM')
    except Exception as e:
        print('add_spouse : ', e)
        pass


def is_married(guild_id, user_id):
    try:
        cur.execute("SELECT count(*) FROM users WHERE guild=? AND id=? AND relationship=3", (guild_id, user_id))
        user = cur.fetchone()
        return int(user[0]) != 0
    except Exception as e:
        print('is_married : ', e)
        pass


def add_significant_other(guild_id, user1_id, user2_id):
    try:
        cur.execute("UPDATE users SET relationship=2, with_id=? WHERE guild=? AND id=?", (user2_id, guild_id, user1_id))
        cur.execute("UPDATE users SET relationship=2, with_id=? WHERE guild=? AND id=?", (user1_id, guild_id, user2_id))
        sql.commit()
        cur.execute('VACUUM')
    except Exception as e:
        print('add_significant_other : ', e)
        pass


def remove_relationship(guild_id, user1_id, user2_id):
    try:
        cur.execute("UPDATE users SET relationship=1, with_id=0 WHERE guild=? AND id=?", (guild_id, user1_id))
        cur.execute("UPDATE users SET relationship=1, with_id=0 WHERE guild=? AND id=?", (guild_id, user2_id))
        sql.commit()
        cur.execute('VACUUM')
    except Exception as e:
        print('remove_relationship : ', e)
        pass


def is_dating(guild_id, user_id):
    try:
        cur.execute("SELECT count(*) FROM users WHERE guild=? AND id=? AND relationship=2", (guild_id, user_id))
        user = cur.fetchone()
        return int(user[0]) != 0
    except Exception as e:
        print('remove_spouse : ', e)
        pass


def in_relationship_with(guild_id, user_id):
    try:
        cur.execute("SELECT count(*), with_id FROM users WHERE guild=? AND id=?", (guild_id, user_id))
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
        cur.execute("SELECT count(*), relationship FROM users WHERE guild=? AND id=? AND (relationship=2 OR relationship=3)", (guild_id, user_id))
        user = cur.fetchone()
        return int(user[0]) != 0 and int(user[1]) != 1
    except Exception as e:
        print('is_in_relationship : ', e)
        pass


def get_relationship_status(guild_id, user_id):
    try:
        cur.execute("SELECT count(*), relationship FROM users WHERE guild=? AND id=?", (guild_id, user_id))
        user = cur.fetchone()
        return Relationship(int(user[1])) if int(user[0]) != 0 else None
    except Exception as e:
        print('get_relationship_status : ', e)
        pass


async def get_answer(reply, target_user):
    try:
        await reply.add_reaction("✅")
        await reply.add_reaction("❌")

        def check(reaction, user):
            return str(reaction.emoji) in ["✅", "❌"] and user == target_user

        try:
            reaction, user = await client.wait_for('reaction_add', timeout=60.0, check=check)
            # answer = await client.wait_for('reaction_add', emoji=["✅", "❌"], message=reply, timeout=60.0, check=lambda reaction, user: user == target_user)
        except asyncio.TimeoutError:
            return Results.timeout
        else:
            if reaction.emoji == "✅":
                return Results.accept
            elif reaction.emoji == "❌":
                return Results.decline
    except Exception as e:
        print('get_answer : ', e)
        pass


@client.command(pass_context=True, name='status')
async def status(ctx):
    try:
        # reply with embed of user's relationship and points status
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        targets = ctx.message.mentions
        target = 0
        guild_id = ctx.message.guild.id
        user = ctx.message.author
        if len(targets) > 1:
            await ctx.send("{0.mention} Please mention one user to check their status, or do not mention any to check your own.".format(user))
            return
        elif len(targets) == 1:
            target = targets[0]
        else:
            target = user
        if target.bot:
            await ctx.send("{0.mention} ".format(user) + random.choice(["Uh, that's a bot....", "Maybe try an actual person.", "That's a weird fetish."]))
            return
        if not user_exists(guild_id, target.id):
            await ctx.send("{0.mention} Looks like that user isn't playing".format(user))
            return
        relationship, score = get_user_info(guild_id, target.id)
        other = in_relationship_with(guild_id, target.id)
        embed = discord.Embed(title='User Status', type='rich', color=0x77B255)
        embed.add_field(name='User:', value=target.display_name, inline=True)
        if relationship == Relationship.Single:
            embed.add_field(name='Status:', value=relationship.name, inline=True)
        else:
            embed.add_field(name='Status:', value="{0} ({1})".format(relationship.name, other.display_name), inline=True)
        embed.add_field(name='Score:', value=score, inline=True)
        await ctx.send(embed=embed)
    except Exception as e:
        print('status : ', e)
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
        # if spouse declines divorce, nothing happens.  but really, does *nothing* happen?
        # if SO chooses split, both revert to single
        # if SO delinces split, what a loser
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        guild_id = ctx.message.guild.id
        user = ctx.message.author
        add_user(guild_id, user.id)
        targets = ctx.message.mentions
        target = None
        if len(targets) > 1:
            await ctx.send("{0.mention} Please mention one user to fuck, or do not mention any to fuck at random.".format(user))
            return
        elif len(targets) == 1:
            target = targets[0]
            if target == user:
                await ctx.send("{0.mention} ".format(user) + random.choice(["I guess you can fuck yourself.", "That's just gross."]))
                return
        else:
            target = get_random_user(guild_id, user.id, False)
        if target.bot:
            await ctx.send("{0.mention} ".format(user) + random.choice(["Uh, that's a bot....", "Maybe try an actual person.", "That's a weird fetish."]))
            return
        if user_ignored(guild_id, target.id):
            await ctx.send("{0.mention} Looks like that user isn't playing.".format(user))
            return
        if is_married(guild_id, user.id) and in_relationship_with(guild_id, user.id) == target:
            time_since = time.time() - most_recent_fuck(guild_id, user.id, target.id)
            if time_since < 300:
                await ctx.send("{0.mention} You two are married, you need to wait {1} more seconds lmao.".format(user, int(300-time_since)))
                return
        if is_dating(guild_id, user.id) and in_relationship_with(guild_id, user.id) == target:
            time_since = time.time() - most_recent_fuck(guild_id, user.id, target.id)
            if time_since < 120:
                await ctx.send("{0.mention} Slow down there lovebirds, you need to wait {1} more seconds lol.".format(user, int(120-time_since)))
                return
        reply = await ctx.send("{0.mention} Looks like {1.mention} wants to bang.  You down?".format(target, user))
        answer = await get_answer(reply, target)
        if answer == Results.accept:
            if is_married(guild_id, user.id) and in_relationship_with(guild_id, user.id) == target:
                await ctx.send("{0.mention} Boring marital sex.  Alright then.  +20".format(user))
                increment_score(guild_id, user.id, 20)
                increment_score(guild_id, target.id, 20)
                add_fuck(guild_id, user.id, target.id)
                return
            if in_relationship_with(guild_id, user.id) == target:
                await ctx.send("{0.mention} Ayyy.  +50".format(user))
                increment_score(guild_id, user.id, 50)
                increment_score(guild_id, target.id, 50)
                add_fuck(guild_id, user.id, target.id)
                return
            if not is_in_relationship(guild_id, user.id) and not is_in_relationship(guild_id, target.id):
                await ctx.send("{0.mention} ***HOT***.  +100".format(user))
                increment_score(guild_id, user.id, 100)
                increment_score(guild_id, target.id, 100)
                add_fuck(guild_id, user.id, target.id)
                return
            cheater = random.choice([user, target])
            caught = random.randint(1,5) == 1
            if caught:
                if is_married(guild_id, cheater.id):
                    spouse = in_relationship_with(guild_id, cheater.id)
                    reply = await ctx.send("{0.mention} You just caught {1.mention} cheating.  Is this marriage over?".format(spouse, cheater))
                    answer = await get_answer(reply, spouse)
                    if answer == Results.accept:
                        score = get_score(guild_id, cheater.id)
                        update_score(guild_id, cheater.id, score / 2)
                        update_score(guild_id, spouse.id, get_score(guild_id, spouse.id) + (score / 2))
                        remove_relationship(guild_id, cheater.id, spouse.id)
                        remove_all_fucks(guild_id, cheater.id, spouse.id)
                        await ctx.send("Welp, {0.mention} just lost half their shit.".format(cheater))
                    elif answer == Results.decline:
                        await ctx.send("{0.mention} I can't believe you're just going to let {1.mention} walk all over you, but that's cool.".format(spouse, cheater))
                    elif answer == Results.timeout:
                        await ctx.send("{0.mention} Took too long to answer.  Wouldn't let this linger, though.".format(spouse))
                elif is_dating(guild_id, cheater.id):
                    significant_other = in_relationship_with(guild_id, cheater.id)
                    reply = await ctx.send("{0.mention} You just caught {1.mention} cheating.  Gonna dump their ass?".format(significant_other, cheater))
                    answer = await get_answer(reply, significant_other)
                    if answer == Results.accept:
                        remove_relationship(guild_id, cheater.id, significant_other.id)
                        remove_all_fucks(guild_id, cheater.id, significant_other.id)
                        await ctx.send("{0.mention} Guess you just got dumped.  YOLO!".format(cheater))
                    elif answer == Results.decline:
                        await ctx.send("{0.mention} I can't believe you're just going to let {1.mention} walk all over you, but that's cool.".format(significant_other, cheater))
                    elif answer == Results.timeout:
                        await ctx.send("{0.mention} Took too long to answer.  Wouldn't let this linger, though.".format(significant_other))
            else:
                await ctx.send("{0.mention} No one got caught.  *NICE*.  +200".format(user))
                increment_score(guild_id, user.id, 200)
                increment_score(guild_id, target.id, 200)
                add_fuck(guild_id, user.id, target.id)
                return
        elif answer == Results.decline:
            await ctx.send("{0.mention} lmao denied!".format(user))
        elif answer == Results.timeout:
            await ctx.send("{0.mention} Guess you just got blown off.  Better luck next time.".format(user))
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
        guild_id = ctx.message.guild.id
        user = ctx.message.author
        add_user(guild_id, user.id)
        targets = ctx.message.mentions
        target = None
        if len(targets) > 1:
            await ctx.send("{0.author.mention} Please mention only one user to date.  Or don't mention any to date at random.".format(ctx.message))
            return
        elif len(targets) == 1:
            target = targets[0]
            if target == user:
                await ctx.send("{0.mention} ".format(user) + random.choice(["Try dating *someone else*.", "That's just gross."]))
                return
        else:
            target = get_random_user(ctx.message.guild.id, user.id, False)
        if target.bot:
            await ctx.send("{0.mention} ".format(user) + random.choice(["Uh, that's a bot....", "Maybe try an actual person.", "That's a weird fetish."]))
            return
        if user_ignored(guild_id, target.id):
            await ctx.send("{0.mention} Looks like that user isn't playing.".format(user))
            return
        if is_married(guild_id, user.id):
            if in_relationship_with(guild_id, user.id) == target:
                await ctx.send("{0.mention} That's cute and all, but you two are already married.".format(user))
                return
            else:
                await ctx.send("{0.mention} You're already married.  Gotta drop that baggage first with a `{1}divorce`.".format(user, command_prefix))
                return
        if is_dating(guild_id, user.id):
            if in_relationship_with(guild_id, user.id) != target:
                await ctx.send("{0.mention} You're already dating someone else.  Gotta `{1}dump` their ass first.".format(user, command_prefix))
                return
        if is_in_relationship(guild_id, target.id):
            await ctx.send("{0.mention} That player is already taken.".format(user))
            return
        reply = await ctx.send("{0.mention} My friend {1.mention} wants to go out with you, what do you think?".format(target, user))
        answer = await get_answer(reply, target)
        if answer == Results.accept:
            await ctx.send("{0.mention} You two make a great couple!".format(user))
            add_significant_other(guild_id, user.id, target.id)
            increment_score(guild_id, user.id, 300)
            increment_score(guild_id, target.id, 300)
        elif answer == Results.decline:
            await ctx.send("{0.mention} Tbh you probably dodged a bullet there.".format(user))
        elif answer == Results.timeout:
            await ctx.send("{0.mention} No answer, guess they aren't that into you.".format(user))
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
        guild_id = ctx.message.guild.id
        user = ctx.message.author
        add_user(guild_id, user.id)
        targets = ctx.message.mentions
        target = None
        reply = None
        if len(targets) > 1:
            await ctx.send("{0.author.mention} Please mention only one user to marry, this isn't Utah.  Or don't mention any to marry at random.".format(ctx.message))
            return
        elif len(targets) == 1:
            target = targets[0]
            if target == user:
                await ctx.send("{0.mention} ".format(user) + random.choice(["Try marrying *someone else*.", "That's just gross."]))
                return
        else:
            target = get_random_user(ctx.message.guild.id, user.id, False)
        if target.bot:
            await ctx.send("{0.mention} ".format(user) + random.choice(["Uh, that's a bot....", "Maybe try an actual person.", "That's a weird fetish."]))
            return
        if user_ignored(guild_id, target.id):
            await ctx.send("{0.mention} Looks like that user isn't playing.".format(user))
            return
        if is_married(guild_id, user.id):
            if in_relationship_with(guild_id, user.id) == target:
                await ctx.send("{0.mention} That's cute and all, but you two are already married.".format(user))
                return
            else:
                await ctx.send("{0.mention} You're already married.  Gotta drop that baggage first with a `{1}divorce`.".format(user, command_prefix))
                return
        elif is_dating(guild_id, user.id):
            if in_relationship_with(guild_id, user.id) != target:
                await ctx.send("{0.mention} You're already dating someone else.  Gotta `{1}dump` their ass first.".format(user, command_prefix))
                return
            if in_relationship_with(guild_id, user.id) == target:
                reply = await ctx.send("{0.mention} I guess {1.mention} finally popped the question.  What do you say?".format(target, user))
        elif is_in_relationship(guild_id, target.id):
            await ctx.send("{0.mention} That player is already taken.".format(user))
            return
        else:
            reply = await ctx.send("{0.mention} Oh wow, {1.mention} just proposed!  What do you say?".format(target, user))
        answer = await get_answer(reply, target)
        if answer == Results.accept:
            await ctx.send("{0.mention} Looks like you just got hitched!".format(user))
            add_spouse(guild_id, user.id, target.id)
            increment_score(guild_id, user.id, 500)
            increment_score(guild_id, target.id, 500)
        elif answer == Results.decline:
            await ctx.send("{0.mention} ***BIG OOF***".format(user))
        elif answer == Results.timeout:
            await ctx.send("{0.mention} No answer, that's cold.".format(user))
    except Exception as e:
        print('marry : ', e)
        pass


@client.command(pass_context=True, name='dump')
async def dump(ctx):
    try:
        # dump : dumps current SO, just rip off that band-aid
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        guild_id = ctx.message.guild.id
        user = ctx.message.author
        add_user(guild_id, user.id)
        if not is_in_relationship(guild_id, user.id):
            await ctx.send("{0.mention} Need to actually `{1}date` someone before you can dump them.".format(user, command_prefix))
            return
        if is_married(guild_id, user.id):
            await ctx.send("{0.mention} You're married, it's not quite that easy.  A `{1}divorce` is what you're looking for.".format(user, command_prefix))
            return
        target = in_relationship_with(guild_id, user.id)
        remove_relationship(guild_id, user.id, target.id)
        remove_all_fucks(guild_id, user.id, target.id)
        await ctx.send("{0.mention} That was easy.".format(user))
    except Exception as e:
        print('dump : ', e)
        pass


@client.command(pass_context=True, name='divorce')
async def divorce(ctx):
    try:
        # divorce : attempt to dump significant other
        # if accepted, both users points totalled up, then each user left with 25% (lawyers take the other half lmao)
        # if declined, asking user loses random amount of points to ex-spouse
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        guild_id = ctx.message.guild.id
        user = ctx.message.author
        add_user(guild_id, user.id)
        if not is_in_relationship(guild_id, user.id):
            await ctx.send("{0.mention} Need to actually `{1}marry` someone first to ruin eachother's lives.".format(user, command_prefix))
            return
        if is_dating(guild_id, user.id):
            await ctx.send("{0.mention} You're only dating.  Just `{1}dump` their ass.".format(user, command_prefix))
            return
        spouse = in_relationship_with(guild_id, user.id)
        reply = await ctx.send("{0.mention} Oh shit, {1.mention} wants out!  What do you say?".format(spouse, user))
        answer = await get_answer(reply, spouse)
        if answer == Results.accept:
            new_score = (get_score(guild_id, user.id) + get_score(guild_id, spouse.id)) / 4
            update_score(guild_id, user.id, new_score)
            update_score(guild_id, spouse.id, new_score)
            remove_relationship(guild_id, user.id, spouse.id)
            remove_all_fucks(guild_id, user.id, spouse.id)
            await ctx.send("{0.mention} Freedom at last!".format(user))
        elif answer == Results.decline:
            loser = random.choice([user, spouse])
            lost_points = random.randint(1, int(get_score(guild_id, loser.id)))
            if loser == user:
                increment_score(guild_id, user.id, lost_points * -1)
                increment_score(guild_id, spouse.id, lost_points)
                remove_relationship(guild_id, user.id, spouse.id)
                remove_all_fucks(guild_id, user.id, spouse.id)
                await ctx.send("{0.mention} Best {1} points you ever spent.".format(user, lost_points))
            else:
                increment_score(guild_id, user.id, lost_points)
                increment_score(guild_id, spouse.id, lost_points * -1)
                remove_relationship(guild_id, user.id, spouse.id)
                remove_all_fucks(guild_id, user.id, spouse.id)
                await ctx.send("{0.mention} Came out on top of that deal.  ***NICE!***".format(user))
        elif answer == Results.timeout:
            await ctx.send("{0.mention} No answer, that's cold.".format(user))
    except Exception as e:
        print('divorce : ', e)
        pass


@client.command(pass_context=True, name='keys')
async def keys(ctx):
    try:
        guild_id = ctx.message.guild.id
        add_user(guild_id, ctx.message.author.id)
        if not is_in_relationship(guild_id, ctx.message.author.id):
            await ctx.send("{0.mention} You need to be in a relationship to host a key party.".format(ctx.message.author))
            return
        reply = await ctx.send("{0.mention} is hosting a key party!  Who wants to attend?".format(ctx.message.author))
        reaction = await reply.add_reaction("🔑")
        await asyncio.sleep(60)
        reply = await ctx.channel.fetch_message(reply.id)
        reaction = None
        for react in reply.reactions:
            if react.emoji == "🔑":
                reaction = react
                break
        # reaction = next((x for x in reply.reactions if x.emoji=="🔑"), None)
        if not reaction:
            return
        users = await reaction.users().flatten()
        attendees = []
        for user in users:
            if user.bot:
                continue
            if in_relationship_with(guild_id, user.id) in users:
                attendees.append(user)
        eligible = 0
        for attendee in attendees:
            so = in_relationship_with(guild_id, attendee.id)
            if so in attendees:
                eligible+=1
        if eligible < 4:
            await ctx.send("{0.mention} Not enough couples joined your key party.  Lame.".format(ctx.message.author))
        couples = []
        matched = []
        while len(matched) < len(attendees):
            for attendee in attendees:
                match = random.choice(attendees)
                if match == attendee:
                    continue
                if match == in_relationship_with(guild_id, attendee.id):
                    continue
                matched.extend([attendee, match])
                couples.append([attendee, match, random.randint(1, 300)])
        couples.sort(key=lambda x: x[2], reverse=True)
        lines = []
        embed = discord.Embed(title='Key Party', type='rich', color=0x77B255)
        for couple in couples:
            lines.append('**{0} + {1} : {2}**'.format(couple[0].display_name, couple[1].display_name, couple[2]))
            increment_score(guild_id, couple[0].id, couple[2])
            increment_score(guild_id, couple[1].id, couple[2])
            remove_all_fucks(guild_id, couple[0].id, couple[1].id)
            add_fuck(guild_id, couple[0].id, couple[1].id)
        embed.add_field(name='Couples', value="\n".join(lines))
        await ctx.send(embed=embed)
    except Exception as e:
        print('keys : ', e)
        pass


@client.command(pass_context=True, name='play')
async def play(ctx):
    try:
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        guild_id = ctx.message.guild.id
        user = ctx.message.author
        add_user(guild_id, user.id)
        await ctx.send("{0.mention} You're ready to play!".format(user))
    except Exception as e:
        print('play : ', e)
        pass


@client.command(pass_context=True, name='stop')
async def stop(ctx):
    try:
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        guild_id = ctx.message.guild.id
        user = ctx.message.author
        add_user(guild_id, user.id)
        if is_in_relationship(guild_id, user.id):
            reply = await ctx.send("{0.mention} You're in a relationship.  Are you really going to walk away from that?".format(user))
            answer = await get_answer(reply, user)
            if answer == Results.accept:
                other = in_relationship_with(guild_id, user.id)
                update_score(guild_id, other.id, get_score(guild_id, other.id) + get_score(guild_id, user.id))
                remove_relationship(guild_id, user.id, other.id)
                opt_out_user(guild_id, user.id)
        else:
            opt_out_user(guild_id, user.id)
            await ctx.send("{0.mention} Okay, I won't bother you.".format(user))
    except Exception as e:
        print('play : ', e)
        pass


@client.command(pass_context=True, name='leaders')
async def leaders(ctx):
    try:
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        guild_id = ctx.message.guild.id
        rank = 1
        lines = []
        cur.execute('SELECT id, score FROM users WHERE guild=? AND ignore=0 ORDER BY 2 DESC LIMIT 10', (guild_id, ))
        users = cur.fetchall()
        embed = discord.Embed(title='Leaderboard', type='rich', color=0x77B255)
        for row in users:
            user = get(client.get_all_members(), id=row[0])
            score = int(row[1]) 
            lines.append('**{0}. {1} - {2}**'.format(rank, user.display_name, score))
            rank+=1
            if rank > 10:
                break
        embed.add_field(name='Players', value="\n".join(lines))
        await ctx.send(embed=embed)
    except Exception as e:
        print('leaders : ', e)
        pass


@client.command(pass_context=True, name='help')
async def help(ctx):
    try:
        if ctx.message.author == client.user or ctx.message.author.bot:
            return
        inline = False
        embed = discord.Embed(title='Help', type='rich', color=0x77B255)
        embed.add_field(name='**{0}play**'.format(command_prefix), value='Join the game', inline=inline)
        embed.add_field(name='**{0}stop**'.format(command_prefix), value='Leave the game', inline=inline)
        embed.add_field(name='**{0}status <optional mention>**'.format(command_prefix), value='Check your status or that of another player', inline=inline)
        embed.add_field(name='**{0}fuck <optional mention>**'.format(command_prefix), value='Fuck a random or specific player', inline=inline)
        embed.add_field(name='**{0}date <optional mention>**'.format(command_prefix), value='Date a random or specific player', inline=inline)
        embed.add_field(name='**{0}marry <optional mention>**'.format(command_prefix), value='Marry a random or specific player', inline=inline)
        embed.add_field(name='**{0}dump**'.format(command_prefix), value='Dump your significant other', inline=inline)
        embed.add_field(name='**{0}divorce**'.format(command_prefix), value='Divorce your spouse', inline=inline)
        embed.add_field(name='**{0}keys**'.format(command_prefix), value='Host a party', inline=inline)
        embed.add_field(name='**{0}leaders**'.format(command_prefix), value='See the leaderboard', inline=inline)
        await ctx.send(embed=embed)
    except Exception as e:
        print('leaders : ', e)
        pass


client.run(settings["discord"]["client_token"])
