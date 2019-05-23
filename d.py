import httpimport
with httpimport.remote_repo(['multidict'], "https://raw.githubusercontent.com/superloach/multidict/master/"):
	import multidict
with httpimport.remote_repo(['attr', 'dry_attr'], "https://raw.githubusercontent.com/denis-ryzhkov/attr/master"):
	import attr
with httpimport.remote_repo(['idna'], "https://raw.githubusercontent.com/superloach/idna/master/"):
	import idna.core
with httpimport.remote_repo(['yarl'], "https://raw.githubusercontent.com/superloach/yarl/master/"):
	from yarl import _quoting
with httpimport.remote_repo(['aiohttp'], "https://raw.githubusercontent.com/superloach/aiohttp/master/"):
	import aiohttp
with httpimport.remote_repo(['discord'], "https://raw.githubusercontent.com/Rapptz/discord.py/master/"):
	import discord
print(discord)
