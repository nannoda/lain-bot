import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, CheckFailure
import os, random, asyncio, logging
from os import path
from dotenv import load_dotenv
from aiohttp import ClientResponseError	
from requests import HTTPError
logger = logging.getLogger(__name__)

from modules.core.client import Client
from modules.core.database import Database
from modules.config.user import User
from modules.anime.safebooru import Safebooru
from modules.anime.doujin import Doujin
from modules.anime.anilist import Anilist
from modules.anime.anilist2 import Anilist2
from modules.anime.mal import Mal
from modules.anime.vndb import Vndb
from modules.config.config import Config

class Anime(commands.Cog):

	load_dotenv()

	def __init__(self, bot):
		self.bot = bot

	async def cog_command_error(self, ctx, err):
		logger.exception("Error during >al command")
		if isinstance(err, discord.ext.commands.errors.CommandInvokeError):
			err = err.original
		try:
			if isinstance(err, discord.ext.commands.MissingPermissions):
				await ctx.send("You lack the needed permissions!")
			elif isinstance(err, Anilist2.AnilistError):
				await ctx.send(f"Query request failed\nmsg: {err.message}\nstatus: {err.status}")	
			elif isinstance(err, HTTPError):	
				await ctx.send(err.http_error_msg)
			else:
				await ctx.send('error!', file=discord.File(os.getcwd() + '/assets/lain_err_sm.png'))
		except:
			pass
		
	@commands.command(pass_context=True)
	async def safebooru(self, ctx, tags):
		"""Look up images on safebooru"""
		channel = ctx.message.channel

		safebooruSearch = Safebooru.booruSearch(tags)

		safebooruImageURL = safebooruSearch[0]
		safebooruPageURL = safebooruSearch[1]
		safebooruTagsTogether = safebooruSearch[2]

		embed = discord.Embed(
			title = tags,
			description = 'Here\'s the picture you were looking for:',
			color = discord.Color.green(),
			url = safebooruPageURL
		)

		embed.set_image(url=safebooruImageURL)
		embed.set_footer(text=safebooruTagsTogether)

		await channel.send(embed=embed)

	@commands.group(pass_context=True)
	async def doujin(self, ctx):
		if ctx.invoked_subcommand is None:
			await ctx.send('Invalid doujin command passed...')

	@doujin.command(pass_context=True)
	async def search(self, ctx):
		tags = str(ctx.message.content)[(len(ctx.prefix) + len('doujin search ')):]
		links = Doujin.tagSearch(tags)
		
		await ctx.trigger_typing()
		embed = discord.Embed(
			title = 'Results',
			color = discord.Color.red()
		)
		embed.set_thumbnail(url='https://e-hentai.org/favicon.png')

		if links != None:
			def check(reaction, user):
				return user == ctx.message.author and (str(reaction.emoji) == '1️⃣' or str(reaction.emoji) == '2️⃣' or str(reaction.emoji) == '3️⃣' or str(reaction.emoji) == '4️⃣' or str(reaction.emoji) == '5️⃣' or str(reaction.emoji) == '6️⃣' or str(reaction.emoji) == '7️⃣' or str(reaction.emoji) == '8️⃣' or str(reaction.emoji) == '9️⃣')
			
			size = len(links)
			if size == 0:
				await ctx.send('No results, try different tags')
				return
			
			i = 1
			for d in links:
				split = d.split('/')
				id = split[4]
				token = split[5]
				meta = Doujin.metaSearch(id, token)
				embed.add_field(name=str(i) + '. ' + meta['title'])
				i += 1
				if i == 10:
					break
			msg = await ctx.send(embed=embed)
			# add reaction(s)
			if size >= 1:
				await msg.add_reaction('1️⃣')
			if size >= 2:
				await msg.add_reaction('2️⃣')
			if size >= 3:
				await msg.add_reaction('3️⃣')
			if size >= 4:
				await msg.add_reaction('4️⃣')
			if size >= 5:
				await msg.add_reaction('5️⃣')
			if size >= 6:
				await msg.add_reaction('6️⃣')
			if size >= 7:
				await msg.add_reaction('7️⃣')
			if size >= 8:
				await msg.add_reaction('8️⃣')
			if size >= 9:
				await msg.add_reaction('9️⃣')

			try:
				reaction, user = await self.bot.wait_for('reaction_add', timeout=10.0, check=check)
			except asyncio.TimeoutError:
				await ctx.send('Took too long, try again')
			
			else:
				try:
					chose = links[str(reaction.emoji)[:1] - 1]
				except:
					await ctx.send('Invalid reaction, try again')
					return
				
				embed = discord.Embed(
					title = 'Not done yet lol',
					color = discord.Color.red(),
					url=chose
				)
				await ctx.send(embed=embed)

		else:
			await ctx.send('Error getting data')

	@commands.group(pass_context=True)
	async def al(self, ctx):
		# anilist command group
		if ctx.invoked_subcommand is None:
			await ctx.send('Invalid anilist command passed...')


	@al.command(pass_context=True)
	async def help(self, ctx):
		await ctx.trigger_typing()
		embed = discord.Embed(
			title = 'Available commands',
			description = '',
			color = discord.Color.blue(),
		)
		embed.add_field(name='al animelist enable', value='Requires admin. Enable anilist anime updates messages on this channel. The same can be done for \'mangalist\'. Replace \'enable\' with \'disable\' to stop message updates.', inline=False)
		embed.add_field(name='al search \<show\>', value='search for anime in anilist', inline=False)
		embed.add_field(name='al manga \<manga\>', value='search for manga in anilist', inline=False)
		embed.add_field(name='al user set \<username\>', value='connect anilist account to discord account', inline=False)
		embed.add_field(name='al user remove', value='disconnect anilist account from discord account', inline=False)
		embed.add_field(name='+more', value='I\'m too lazy to do describe all of them. There\'s safebooru, al char, al user profile', inline=False)

		await ctx.send(embed=embed)

	@al.command(pass_context=True)
	async def search(self, ctx):
		"""search for anime in anilist"""
		await ctx.trigger_typing()
		show = str(ctx.message.content)[(len(ctx.prefix) + len('al search ')):]
		# retrieve json file
		anilistResults = await Anilist2.aniSearch(Client.session, show, isAnime=True)
		showID = anilistResults["data"]["anime"]["id"]

		# parse out website styling
		desc = shorten(str(anilistResults['data']['anime']['description']))

		# make genre list look nice
		gees = str(anilistResults['data']['anime']['genres'])
		gees = gees.replace('\'', '')
		gees = gees.replace('[', '')
		gees = gees.replace(']', '')

		# embed text to output
		embed = discord.Embed(
			title = str(anilistResults['data']['anime']['title']['romaji']),
			description = desc,
			color = discord.Color.blue(),
			url = str(anilistResults['data']['anime']['siteUrl'])
		)

		embed.set_footer(text=gees)

		# images, check if valid before displaying
		if 'None' != str(anilistResults['data']['anime']['bannerImage']):
			embed.set_image(url=str(anilistResults['data']['anime']['bannerImage']))

		if 'None' != str(anilistResults['data']['anime']['coverImage']['large']):
			embed.set_thumbnail(url=str(anilistResults['data']['anime']['coverImage']['large']))

		# studio name and link to their AniList page
		try:
			embed.set_author(name=str(anilistResults['data']['anime']['studios']['nodes'][0]['name']), url=str(anilistResults['data']['anime']['studios']['nodes'][0]['siteUrl']))
		except IndexError:
			logger.error('empty studio name or URL')

		# if show is airing, cancelled, finished, or not released
		status = anilistResults['data']['anime']['status']

		if 'NOT_YET_RELEASED' not in status:
			embed.add_field(name='Score', value=str(anilistResults['data']['anime']['meanScore']) + '%', inline=True)
			embed.add_field(name='Popularity', value=str(anilistResults['data']['anime']['popularity']) + ' users', inline=True)
			if 'RELEASING' not in status:
				embed.add_field(name='Episodes', value=str(anilistResults['data']['anime']['episodes']), inline=False)

				# make sure season is valid
				if str(anilistResults['data']['anime']['seasonYear']) != 'None' and str(anilistResults['data']['anime']['season']) != 'None':
					embed.add_field(name='Season', value=str(anilistResults['data']['anime']['seasonYear']) + ' ' + str(anilistResults['data']['anime']['season']).title(), inline=True)

				# find difference in year month and days of show's air time
				try:
					air = True
					years = abs(anilistResults['data']['anime']['endDate']['year'] - anilistResults['data']['anime']['startDate']['year'])
					months = abs(anilistResults['data']['anime']['endDate']['month'] - anilistResults['data']['anime']['startDate']['month'])
					days = abs(anilistResults['data']['anime']['endDate']['day'] - anilistResults['data']['anime']['startDate']['day'])
				except TypeError:
					logger.error('Error calculating air time')
					air = False

				# get rid of anything with zero
				if air:
					tyme = str(days) + ' days'
					if months != 0:
						tyme += ', ' + str(months) + ' months'
					if years != 0:
						tyme += ', ' + str(years) + ' years'

					embed.add_field(name='Aired', value=tyme, inline=False)

		await embedScores(ctx.guild, showID, 'animeList', 9, embed)

		await ctx.send(embed=embed)

	@al.command(pass_context=True)
	async def manga(self, ctx):
		"""Search for manga in anilist"""
		await ctx.trigger_typing()
		comic = str(ctx.message.content)[(len(ctx.prefix) + len('al manga ')):]
		# retrieve json file
		anilistResults = await Anilist2.aniSearch(Client.session, comic, isManga=True)
		mangaID = anilistResults["data"]["manga"]["id"]

		# parse out website styling
		desc = shorten(str(anilistResults['data']['manga']['description']))

		# make genre list look nice
		gees = str(anilistResults['data']['manga']['genres'])
		gees = gees.replace('\'', '')
		gees = gees.replace('[', '')
		gees = gees.replace(']', '')

		# embed text to output
		embed = discord.Embed(
			title = str(anilistResults['data']['manga']['title']['romaji']),
			description = desc,
			color = discord.Color.blue(),
			url = str(anilistResults['data']['manga']['siteUrl'])
		)

		embed.set_footer(text=gees)
		embed.add_field(name = 'Format', value=str(anilistResults['data']['manga']['format']).title())

		# images, check if valid before displaying
		if 'None' != str(anilistResults['data']['manga']['bannerImage']):
			embed.set_image(url=str(anilistResults['data']['manga']['bannerImage']))

		if 'None' != str(anilistResults['data']['manga']['coverImage']['large']):
			embed.set_thumbnail(url=str(anilistResults['data']['manga']['coverImage']['large']))


		# if show is airing, cancelled, finished, or not released
		status = anilistResults['data']['manga']['status']

		if 'NOT_YET_RELEASED' not in status:
			embed.add_field(name='Score', value=str(anilistResults['data']['manga']['meanScore']) + '%', inline=True)
			embed.add_field(name='Popularity', value=str(anilistResults['data']['manga']['popularity']) + ' users', inline=True)
			if 'RELEASING' not in status:
				embed.add_field(name='Chapters', value=str(anilistResults['data']['manga']['chapters']), inline=False)
				# find difference in year month and days of show's air time
				try:
					air = True
					years = abs(anilistResults['data']['manga']['endDate']['year'] - anilistResults['data']['manga']['startDate']['year'])
					months = abs(anilistResults['data']['manga']['endDate']['month'] - anilistResults['data']['manga']['startDate']['month'])
					days = abs(anilistResults['data']['manga']['endDate']['day'] - anilistResults['data']['manga']['startDate']['day'])
				except TypeError:
					logger.error('Error calculating air time')
					air = False

				# get rid of anything with zero
				if air:
					tyme = str(days) + ' days'
					if months != 0:
						tyme += ', ' + str(months) + ' months'
					if years != 0:
						tyme += ', ' + str(years) + ' years'

					embed.add_field(name='Released', value=tyme, inline=False)

		await embedScores(ctx.guild, mangaID, 'mangaList', 9, embed)

		await ctx.send(embed=embed)

	@al.command(pass_context=True)
	async def char(self, ctx):
		"""Search for a character on anilist"""
		c = str(ctx.message.content)[(len(ctx.prefix) + len('al char ')):]
		anilistResults = await Anilist2.aniSearch(Client.session, c, isCharacter=True)

		embed = discord.Embed(
				title = str(anilistResults['data']['character']['name']['full']),
				color = discord.Color.blue(),
				url = str(anilistResults['data']['character']['siteUrl'])
			)

		# make alternative names look nice
		alts = str(anilistResults['data']['character']['name']['alternative'])
		alts = alts.replace('\'', '')
		alts = alts.replace('[', '')
		alts = alts.replace(']', '')

		image = str(anilistResults['data']['character']['image']['large'])
		if (image != 'None'):
			embed.set_image(url=image)

		try:
			embed.set_author(name=str(anilistResults['data']['character']['media']['nodes'][0]['title']['romaji']), url=str(anilistResults['data']['character']['media']['nodes'][0]['siteUrl']), icon_url=str(anilistResults['data']['character']['media']['nodes'][0]['coverImage']['medium']))
		except IndexError:
			logger.error('Character had empty show name or url, or image')

		embed.set_footer(text=alts)

		await ctx.send(embed=embed)

	@al.group(pass_context=True)
	async def animelist(self, ctx):
		if ctx.invoked_subcommand is None:
			await ctx.send('Invalid animelist command passed...\nTry \"\>al animelist enable\" to enable anime updates on this channel or use disable.')

	@animelist.command(pass_context=True, name="enable")
	@has_permissions(administrator=True)
	async def animelist_enable(self, ctx):
		res = await Database.guild_update_one(
			{ 'id': str(ctx.guild.id) },
			{  '$addToSet': { 'animeMessageChannels': str(ctx.channel.id) } },
			upsert=True
		)
		# if the update created a new document, populate it with the rest of the info
		if res.upserted_id:
			await Database.guild_update_one(
				{ '_id': res.upserted_id },
				{ '$set': { 'name': ctx.guild.name, 'mangaMessageChannels': [] } }
			)

		await ctx.send("Enabled AniList Anime messages in this channel!")


	@animelist.command(pass_context=True, name="disable")
	@has_permissions(administrator=True)
	async def animelist_diable(self, ctx):
		"""Disable anilist anime updates in this channel. Require admin privileges."""
		await Database.guild_update_one(
			{ 'id': str(ctx.guild.id) },
			{  '$pullAll': { 'animeMessageChannels': [str(ctx.channel.id)] } },
		)
		await ctx.send("Anime messages disabled for this channel!")

	@al.group(pass_context=True)
	async def mangalist(self, ctx):
		if ctx.invoked_subcommand is None:
			await ctx.send('Invalid mangalist command passed...\nTry \"\>al mangalist enable\" to enable manga updates on this channel or use disable.')

	@mangalist.command(pass_context=True, name="enable")
	@has_permissions(administrator=True)
	async def mangalist_enable(self, ctx):
		"""Enable anilist manga updates in this channel. Require admin privileges."""
		res = await Database.guild_update_one(
			{ 'id': str(ctx.guild.id) },
			{  '$addToSet': { 'mangaMessageChannels': str(ctx.channel.id) } },
			upsert=True
		)
		# if the update created a new document, populate it with the rest of the info
		if res.upserted_id:
			await Database.guild_update_one(
				{ '_id': res.upserted_id },
				{ '$set': { 'name': ctx.guild.name, 'animeMessageChannels': [] } }
			)

		await ctx.send("Enabled AniList Manga messages in this channel!")

	@mangalist.command(pass_context=True, name="disable")
	@has_permissions(administrator=True)
	async def mangalist_disable(self, ctx):
		"""Disable anilist manga updates in this channel. Require admin privileges."""
		await Database.guild_update_one(
			{ 'id': str(ctx.guild.id) },
			{  '$pullAll': { 'mangaMessageChannels': [str(ctx.channel.id)] } },
		)
		await ctx.send("Manga messages disabled for this channel!")

	@al.group(pass_context=True)
	async def user(self, ctx):
		if ctx.invoked_subcommand is None:
			await ctx.send('Invalid Anilist user command passed...')

	@user.command(name="set")
	async def set_(self, ctx, *user):
		"""Set anilist username for updates"""
		await ctx.trigger_typing()
		if not user:
			await ctx.send('Please provide a username')
			return
		
		if len(user[0]) < 2:
			await ctx.send('Usernames are 2 or more characters')
			return

		user = user[0]

		search = await Anilist2.userSearch(Client.session, user)
		if not search:
			logger.error('--search command err')
			ctx.send('Error! Probably an invalid username')
			return

		if search.get('errors'):
			notFound = False
			for error in search['errors']:
				if error['message'] == 'Not Found.':
					notFound =  True
					break
			if notFound:
				await ctx.send('Sorry, could not find that user')
			else:
				await ctx.send('Error!')
		else:
			def check(reaction, user):
				return user == ctx.message.author and (str(reaction.emoji) == '✅' or str(reaction.emoji) == '❌')
			await ctx.send('Is this you?')
			embed = discord.Embed(
				title = search['data']['User']['name'],
				description = search['data']['User']['about'] if search['data']['User']['about'] else '',
				color = discord.Color.blue(),
				url = 'http://anilist.co/user/'+str(search['data']['User']['id'])
			)
			embed.set_thumbnail(url=search['data']['User']['avatar']['large'])
			msg = await ctx.send(embed=embed)
			await msg.add_reaction('✅')
			await msg.add_reaction('❌')

			try:
				reaction, user = await self.bot.wait_for('reaction_add', timeout=5.0, check=check)
			except asyncio.TimeoutError:
				await ctx.send('Timed out. User not updated')
			else:
				if str(reaction.emoji) == '✅':
					await ctx.trigger_typing()
					lists = generateLists(search)
					await Database.user_update_one(
						{'discordId': str(ctx.message.author.id)},
						{'$set': {
							'anilistId': search['data']['User']['id'],
							'anilistName': search['data']['User']['name'],
							'animeList': lists['animeList'],
							'mangaList': lists['mangaList'],
							'profile': search['data']['User'],
							'status': 1,
							}
						},
						upsert=True
					)
					await ctx.send('Your details have been updated!')
				else:
					await ctx.send('Your details have NOT been updated!')

	@user.command()
	async def watching(self, ctx, *user):
		await ctx.trigger_typing()
		search = {}
		if len(user):
			# username given
			user = user[0].strip()
			if user.startswith('<@!'):
				userLen = len(user)-1
				atUser = user[3:userLen]
				search = {'discordId': atUser }
			elif user.startswith('<@'):
				userLen = len(user)-1
				atUser = user[2:userLen]
				search = {'discordId': atUser }
			elif len(user) > 5 and user[len(user)-5]=="#":
				userId = ctx.guild.get_member_named(user)
				if userId:
					# found in guild
					search = {'discordId': str(userId.id) }
				else:
					# not found
					await ctx.send('Sorry. I could not find that user in this server.')
					return
			else:
				search = {'anilistName': user }
		else:
			#no username given -> retrieve message creator's info
			search = {'discordId': str(ctx.message.author.id)}

		userData = await Database.user_find_one(
			search,
			{
				'anilistId': 1,
				'anilistName': 1,
				'animeList': 1,
				'profile.avatar.large': 1,
				'profile.bannerImage': 1
			}
		)

		if userData:
			watchingList = []
			rewatchingList = []

			for entry in userData['animeList']:
				e = '• ' + userData['animeList'][entry]['title'] + ' (' + str(userData['animeList'][entry]['progress']) + '/'
				if userData['animeList'][entry]['episodes']:
					e = e + str(userData['animeList'][entry]['episodes']) + ')'
				else:
					e = e + '-)'

				if userData['animeList'][entry]['status'] == 'CURRENT':
					watchingList.append(e)
					continue
				if userData['animeList'][entry]['status'] == 'REPEATING':
					rewatchingList.append(e)
					continue
			
			if not (watchingList or rewatchingList):
				await ctx.send('They do not have anything on their watch/rewatch list at the moment.')
				return

			watchingList = limitLength(watchingList)
			rewatchingList = limitLength(rewatchingList)

			# found
			embed = discord.Embed(
				title = userData['anilistName'],
				color = discord.Color.teal(),
				url = 'https://anilist.co/user/'+str(userData['anilistId']),
			)
			embed.set_thumbnail(url=userData['profile']['avatar']['large'])

			embed.set_image(url='https://files.catbox.moe/ixivqn.png') # mobile width fix

			if watchingList:
				embed.add_field(name='Watching', value='\n'.join(watchingList), inline=False)

			if rewatchingList:
				embed.add_field(name='Rewatching', value='\n'.join(rewatchingList), inline=False)

			await ctx.send(embed=embed)
		else:
			# not found
			if 'anilistName' in search:
				await ctx.send('Sorry. I do not support searches on users not registered with me')
				await ctx.send('...yet')
			else:
				await ctx.send('Sorry. I do not have that user\'s info')


	@user.command()
	async def remove(self, ctx):
		"""Remove anilist username for updates"""
		res = await Database.user_update_one(
			{ 'discordId': str(ctx.message.author.id) },
			{ '$set': { 'status': 0 } }
		)
		if res.matched_count:
			await ctx.send('You have been removed!')
		else:
			await ctx.send('You were never registered.')

	@user.command()
	async def profile(self, ctx, *user):
		await ctx.trigger_typing()
		search = {}
		if len(user):
			# username given
			user = user[0].rstrip()
			if user.startswith('<@!'):
				userLen = len(user)-1
				atUser = user[3:userLen]
				search = {'discordId': atUser }
			elif user[len(user)-5]=="#":
				userId = ctx.guild.get_member_named(user).id
				if userId:
					# found in guild
					search = {'discordId': str(userId) }
				else:
					# not found
					await ctx.send('Sorry. I could not find that user in this server.')
					return
			else:
				search = {'anilistName': user }
		else:
			#no username given -> retrieve message creator's info
			search = {'discordId': str(ctx.message.author.id)}

		userData = await Database.user_find_one(
			search,
			{
				'anilistId': 1,
				'anilistName': 1,
				'profile': 1,
			}
		)
		if userData:
			# found
			embed = discord.Embed(
				title = userData['anilistName'],
				color = discord.Color.teal(),
				url = 'https://anilist.co/user/'+str(userData['anilistId'])
			)
			animeGenres = None
			genreData = userData['profile']['statistics']['anime']['genres']
			if genreData and len(genreData):
				animeGenres=', '.join(map(lambda x: x['genre'], genreData))

			animeFavs = None
			favData = userData['profile']['favourites']['anime']['nodes']
			if favData and len(favData):
				animeFavs=', '.join(map(lambda x: x['title']['romaji'], favData))

			if userData['profile']["bannerImage"]:
				embed.set_image(url=userData['profile']["bannerImage"])
			if userData['profile']["avatar"]["large"]:
				embed.set_thumbnail(url=userData['profile']["avatar"]["large"])
			if userData['profile']['about']:
				embed.add_field(name="About:", value=str(userData['profile']['about']), inline=False)

			embed.add_field(name="Anime count:", value=str(userData['profile']["statistics"]["anime"]["count"]), inline=True)
			embed.add_field(name="Mean anime score:", value=str(userData['profile']["statistics"]["anime"]["meanScore"])+"/100.00", inline=True)

			if animeFavs:
				embed.add_field(name="Some favourites:", value=animeFavs, inline=False)

			if animeGenres:
				embed.add_field(name="Top anime genres:", value=animeGenres, inline=False)

			await ctx.send(embed=embed)
		else:
			# not found
			if 'anilistName' in search:
				await ctx.send('Sorry. I do not support searches on users not registered with me.')
			else:
				await ctx.send('Sorry. I could not find that user')

	# al user
	@user.command()
	async def profile_old(self, ctx, user):
		user = str(ctx.message.content)[(len(ctx.prefix) + len('al user profile ')):]
		# when the message contents are something like "@Sigurd#6070", converts format into "<@!user_id>"

		atLen = len(user)-5
		if user == "":
			try:
				user = User.userRead(str(ctx.message.author.id), "alName")
			except:
				user = None
		elif user.startswith("<@!"):
			userLen = len(user)-1
			atUser = user[3:userLen]
			try:
				user = User.userRead(str(atUser), "alName")
			except:
				user = None
		# re.findall(".+#[0-9]{4}", txt)
		elif user[atLen]=="#":
			for users in self.bot.users:
				usersSearch = users.name+"#"+users.discriminator
				if usersSearch == user:
					try:
						user = User.userRead(str(users.id), "alName")
					except:
						return None

		try:
			anilistResults = Anilist.userSearch(user)["data"]["User"]
		except:
			print(user)
			if user == None:
				await ctx.send("Error! Make sure you've set your profile using ``>al user set``!")
			else:
				await ctx.send("Error! Make sure you're spelling everything correctly!")
		try:
			color = colorConversion(anilistResults["options"]["profileColor"])
		except:
			color = discord.Color.teal()
		userUrl = anilistResults["siteUrl"]

		embed = discord.Embed(
			title = anilistResults["name"],
			color = color,
			url = userUrl
		)

		try:
			animeGenres = anilistResults["statistics"]["anime"]["genres"][0]["genre"]+", "+anilistResults["statistics"]["anime"]["genres"][1]["genre"]+", "+anilistResults["statistics"]["anime"]["genres"][2]["genre"]+", "+anilistResults["statistics"]["anime"]["genres"][3]["genre"]+", "+anilistResults["statistics"]["anime"]["genres"][4]["genre"]
		except:
			animeGenres = "None"

		# core user fields


		if anilistResults["bannerImage"]!=None:
			try:
				embed.set_image(url=anilistResults["bannerImage"])
			except:
				pass
		try:
			embed.set_thumbnail(url=anilistResults["avatar"]["large"])
		except:
			pass
		try:
			embed.add_field(name="About:", value=str(anilistResults["about"]), inline=False)
		except:
			pass
		try:
			embed.set_footer(text="Last update: "+str(anilistResults["updatedAt"]))
		except:
			pass

		# anime fields
		try:
			embed.add_field(name="Anime count:", value=str(anilistResults["statistics"]["anime"]["count"]), inline=True)
		except:
			pass
		try:
			embed.add_field(name="Mean anime score:", value=str(anilistResults["statistics"]["anime"]["meanScore"])+"/100.00", inline=True)
		except:
			pass
		try:
			embed.add_field(name="Top anime genres:", value=animeGenres, inline=False)
		except:
			pass
		try:
			await ctx.send(embed=embed)
		except Exception as e:
			logger.exception('%s; %s; %s', 
				anilistResults["bannerImage"],
				anilistResults["avatar"]["large"],
				anilistResults["siteUrl"])
			await ctx.send(e)

	@commands.group(pass_context=True)
	async def vn(self, ctx):
		if ctx.invoked_subcommand is None:
			await ctx.send('Invalid vndb command passed...')

	@vn.command(pass_context=True)
	async def get(self, ctx):
		"""Lookup a visual novel on vndb"""
		# name of vn
		arg = str(ctx.message.content)[(len(ctx.prefix) + len('vn get ')):]
		try:
			# grab info from database
			vn = Vndb()
			r = vn.vn(arg.strip())
			r = r['items'][0]

			# assign variables
			title = r['title']
			link = 'https://vndb.org/v' + str(r['id'])

			try:
				desc = shorten(r['description'])
			except:
				desc = 'Empty Description'
			# ----
			try:
				score = str(r['rating'])
			except:
				score = 'Unknown'
			# ----
			try:
				votes = str(r['votecount'])
			except:
				votes = 'Unknown'
			# ----
			try:
				popularity = str(r['popularity'])
			except:
				popularity = 'Unknown'
			# ----
			try:
				released = r['released']
			except:
				released = 'Unknown'
			# ----
			try:
				length = {
					1 : 'Very Short (< 2 hours)',
					2 : 'Short (2 - 10 hours)',
					3 : 'Medium (10 - 30 hours)',
					4 : 'Long (30 - 50 hours)',
					5 : 'Very Long (> 50 hours)'
				}[r['length']]
			except:
				length = 'Unknown'
			# ----
			try:
				image = r['image']
			except:
				image = 'https://i.kym-cdn.com/photos/images/original/000/290/992/0aa.jpg'
			# ----
			try:
				screens = r['screens']
			except:
				screens = []
			# ----
			try:
				langs = str(r['languages']).replace('[', '').replace(']', '').replace('\'','')
			except:
				langs = 'Unknown'
			# ----
			try:
				platforms = str(r['platforms']).replace('[', '').replace(']', '').replace('\'','')
			except:
				platforms = 'Unknown'
			# NSFW images disabled by default
			nsfw = False

			# display info on discord
			embed = discord.Embed(
					title = title,
					description = desc,
					color = discord.Color.purple(),
					url = link
				)
			try:
				embed.set_author(name='vndb')
			except:
				pass

			# adding fields to embed
			if score != 'Unknown':
				embed.add_field(name='Score', value=score, inline=True)
			if votes != 'Unknown':
				embed.add_field(name='Votes', value=votes, inline=True)
			if popularity != 'Unknown':
				embed.add_field(name='Popularity', value=popularity, inline=True)
			if released != 'Unknown':
				embed.add_field(name='Released', value=released, inline=True)
			if length != 'Unknown':
				embed.add_field(name='Time To Complete', value=length, inline=True)
			if langs != 'Unknown':
				embed.add_field(name='Languages', value=langs, inline=True)
			if platforms != 'Unknown':
				embed.add_field(name='Platforms', value=platforms, inline=True)

			embed.set_footer(text='NSFW: {0}'.format({False : 'off', True : 'on'}[nsfw]))

			embed.set_thumbnail(url=image)

			# Filter out porn
			risky = []
			for pic in screens:
				if pic['nsfw']:
					risky.append(pic)

			for f in risky:
				screens.remove(f)

			# Post image
			if len(screens) >= 1:
				embed.set_image(url=random.choice(screens)['image'])

			await ctx.send(embed=embed)
		except Exception as e:
			logger.exception('Exception looking up VN')
			await ctx.send('VN not found (title usually has to be exact)')

	@vn.command(pass_context=True)
	async def quote(self, ctx):
		"""Display a random visual novel quote"""
		q = Vndb()
		quote = q.quote()

		embed = discord.Embed(
					title = quote['quote'],
					color = discord.Color.purple()
				)

		embed.set_author(name=quote['title'], url='https://vndb.org/v' + str(quote['id']), icon_url=quote['cover'])

		await ctx.send(embed=embed)

def shorten(desc):
	# italic
	desc = desc.replace('<i>', '*')
	desc = desc.replace('</i>', '*')
	# bold
	desc = desc.replace('<b>', '**')
	desc = desc.replace('</b>', '**')
	# remove br
	desc = desc.replace('<br>', '')

	# keep '...' in
	desc = desc.replace('...', '><.')

	# limit description to three sentences
	sentences = findSentences(desc)
	if len(sentences) > 3:
		desc = desc[:sentences[2] + 1]

	# re-insert '...'
	desc = desc.replace('><', '..')

	return desc

def findSentences(s):
	return [i for i, letter in enumerate(s) if letter == '.' or letter == '?' or letter == '!']

def colorConversion(arg):
	colors = {
		"blue": discord.Color.blue(),
		"purple": discord.Color.purple(),
		"pink": discord.Color.magenta(),
		"orange": discord.Color.orange(),
		"red": discord.Color.red(),
		"green": discord.Color.green(),
		"gray": discord.Color.light_grey()
	}
	return colors.get(arg, discord.Color.teal())

def statusConversion(arg, listType):
	colors = {
		"CURRENT": "W",
		"PLANNING": "P",
		"COMPLETED": "C",
		"DROPPED": "D",
		"PAUSED": "H",
		"REPEATING": "R"
	}
	if listType == 'mangaList':
		colors['CURRENT'] = "R"
		colors['REPEATING'] = "RR"

	return colors.get(arg, "X")


async def embedScores(guild, showID, listType, maxDisplay, embed):
		# get all users in db that are in this guild and have the show on their list
		userIdsInGuild = [str(u.id) for u in guild.members]
		users = [d async for d in Database.user_find(
			{
				'discordId': { '$in': userIdsInGuild },
				listType+'.'+str(showID): { '$exists': True }
			},
			{
				'anilistName': 1,
				listType+'.'+str(showID): 1,
				'profile.mediaListOptions': 1
			}
			)
		]

		usrLen = len(users)
		for i in range(0, min(usrLen, maxDisplay-1)):
			userScoreEmbeder(users[i], showID, listType, embed)

		# either load last or say there are '+XX others'
		if usrLen == maxDisplay:
			userScoreEmbeder(users[maxDisplay-1], showID, listType, embed)
		elif usrLen > maxDisplay:
			embed.add_field(name='+'+str(usrLen-maxDisplay+1)+' others', value="...", inline=True)

def userScoreEmbeder(user, showID, listType, embed):
	userInfo = user[listType][str(showID)]
	status = statusConversion(userInfo['status'], listType)

	score = userInfo['score']
	scoreFmt = Database.userScoreFormat(user)
	if not score or score == 0:
		embed.add_field(name=user['anilistName'], value="No Score ("+status+")", inline=True)
	else:
		embed.add_field(name=user['anilistName'], value=Database.scoreFormated(score, scoreFmt)+" ("+status+")", inline=True)

def generateLists(user):
	lists = { 'animeList': {}, 'mangaList': {} }

	for lst in user['data']['animeList']['lists']:
		for entry in lst['entries']:
			lists['animeList'][str(entry['mediaId'])] = Database.formListEntryFromAnilistEntry(entry, anime=True)

	for lst in user['data']['mangaList']['lists']:
		for entry in lst['entries']:
			lists['mangaList'][str(entry['mediaId'])] = Database.formListEntryFromAnilistEntry(entry, anime=False)

	return lists

def limitLength(lst):
	orgLen = len('\n'.join(lst))
	if orgLen <= 1024:
		return lst
	   
	lst.append('+#### others!')
	tLen = len('\n'.join(lst))
	lst = lst[:-1]
	numRemoved = 0
	lenRemoved = 0
	for i in reversed(range(len(lst))):
		lenRemoved += len(lst[i]) + 1
		numRemoved += 1
		del lst[i]
		if tLen - lenRemoved <= 1024:
			break

	lst.append('+' + str(numRemoved) + ' others!')
	return lst
