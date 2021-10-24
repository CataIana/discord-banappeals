from aiohttp import web
import json
from datetime import datetime
from random import choice
from string import ascii_letters
from urllib.parse import parse_qs
from typing import TYPE_CHECKING
from html import unescape
if TYPE_CHECKING:
    from .bot import Appeals

class RecieverWebServer():
    def __init__(self, bot):
        self.bot: Appeals = bot
        with open("config.json") as f:
            self.config = json.load(f)
        self.check_banned = self.config.get("check_ban_before_submission", False)
        if self.check_banned:
            try:
                self.guild_id = int(self.config["guild_id"])
                self.bot_token = self.config["bot_token"]
                if self.bot_token == "":
                    raise KeyError
            except KeyError:
                self.check_banned = False
                self.bot.log.warning("Check bans is enabled, but bad configuration provided! Disabling.")
            except ValueError:
                self.check_banned = False
                self.bot.log.warning("Check bans is enabled, but bad configuration provided! Disabling.")
        self.port = int(self.config.get("proxy_port", 5005))
        self.discord_url = "https://discord.com/api/v9"
        self.web_server = web.Application()
        self.web_server.add_routes([web.get('/', self.main)])
        self.web_server.add_routes([web.get('/authorize', self.authorize)])
        self.web_server.add_routes([web.get('/appeal', self.appeal)])
        self.web_server.add_routes([web.post('/submit', self.submit)])
        self.web_server.add_routes([web.get('/error', self.error)])
        self.web_server.add_routes([web.get('/notbanned', self.notbanned)])
        self.web_server.add_routes([web.get('/done', self.success)])
        self.web_server.add_routes([web.get('/logo', self.logo)])
        self.web_server.add_routes([web.get('/favicon', self.favicon)])
        self.ids = {}

    async def start(self):
        runner = web.AppRunner(self.web_server)
        await runner.setup()
        await web.TCPSite(runner, host="localhost", port=self.port).start()
        self.bot.log.info(f"Webserver running on localhost:{self.port}")
        return self.web_server

    async def main(self, request):
        return web.FileResponse("html/index.html")

    async def logo(self, request):
        return web.FileResponse("html/logo.png")

    async def favicon(self, request):
        return web.FileResponse("html/favicon.ico")

    async def submit(self, request):
        r = await request.read()
        query = parse_qs(r.decode())
        self.bot.log.debug(f"Appeal submission: {query}")
        if query.get('user_id', None) is None:
            return web.Response(body="Invalid request", status=400)
        user = self.ids.get(query['user_id'][0], None)
        if user is None:
            return web.Response(body="Invalid request", status=400)
        try:
            await self.bot.submit_appeal(id=query["user_id"][0], user=user["object"], ban_age=query["ban_age"][0], justified_ban=query["justified"][0], ban_reason=unescape(query["whyunbanme"][0]), ban_appeal=unescape(query["appealbox"][0]), extra_message=unescape(query.get("extramessage", [''])[0]))
        except KeyError: # Put the user back on the appeal back if they somehow submit without filling in everything
            try:
                return web.HTTPSeeOther(f"{self.config['server_url']}/appeal?id={query['user_id'][0]}")
            except KeyError: # Put the user back onto the root page if the ID can't be fetched
                return web.HTTPSeeOther(f"{self.config['server_url']}")
        except IndexError:
            try:
                return web.HTTPSeeOther(f"{self.config['server_url']}/appeal?id={query['user_id'][0]}")
            except KeyError:
                return web.HTTPSeeOther(f"{self.config['server_url']}")
        return web.HTTPSeeOther(f"{self.config['server_url']}/done")

    async def error(self, request):
        return web.FileResponse("html/error.html")

    async def notbanned(self, request):
        return web.FileResponse("html/notbanned.html")

    async def success(self, request):
        return web.FileResponse("html/done.html")

    async def appeal(self, request):
        if request.query.get("id", None) not in self.ids.keys():
            return web.HTTPSeeOther(f"{self.config['server_url']}")
        with open("appealed_users.txt") as f:
            already_appealed = f.read().splitlines()
        if request.query.get("id", None) in already_appealed:
            return web.HTTPSeeOther(f"{self.config['server_url']}/error")    
        return web.FileResponse("html/appeal.html")

    async def authorize(self, request):
        #Check if user needs to be redirected so a code can be aquired
        if request.query.get("code-required", "false") == "true":
            scopes = "identify"
            url = f"https://discord.com/oauth2/authorize?client_id={self.config['client_id']}&redirect_uri={self.config['server_url']}/authorize&response_type=code&scope={scopes}"
            return web.HTTPSeeOther(url)

        #Discord errors return here, redirect to error page if this is the case
        if request.query.get("error", None) is not None:
            err_code = request.query.get("error", "")
            error_description = request.query.get("error_description", "")
            return web.HTTPSeeOther("./")

        # Get oauth code
        if request.query.get("code", None) is None:
            self.bot.log.debug("No code provided, ignoring")
            return web.Response(body="No code provided", status=400)
        else:
            oauth = request.query.get("code", None)
        self.bot.log.debug(f"Oauth2 code: {oauth}")
        # Get access token
        data = {
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "grant_type": "authorization_code",
            "code": oauth,
            "redirect_uri": f'{self.config["server_url"]}/authorize'
        }
        r = await self.bot.aSession.post(f"{self.discord_url}/oauth2/token", headers={"Content-Type": "application/x-www-form-urlencoded"}, data=data)
        token = await r.json()
        if token.get("error", None) is not None:
            self.bot.log.error(f"Error authorising: {token['error_description']}")
            err_code = ""
            error_description = "Invalid authorization code"
            return web.HTTPSeeOther(f"{self.config['server_url']}/error?error={err_code}&error_description={error_description}")
        self.bot.log.debug(f"Token data: {token}")

        # #Get User Information, mainly ID
        r = await self.bot.aSession.get(f"{self.discord_url}/users/@me", headers={"Authorization": f"Bearer {token['access_token']}"})
        user = await r.json()
        self.bot.log.debug(f"User Details: {user}")
        random = self.random_string(20)
        while random in list(self.ids.keys()):
            random = self.random_string(20)
        for random_string, u in self.ids.items():
            if u["object"]["id"] == user["id"]:
                random = random_string
                break

        #Start checks if user is banned in guild, if provided
        if self.check_banned:
            r = await self.bot.aSession.get(f"{self.discord_url}/guilds/{self.guild_id}/bans/{user['id']}",
                headers={"Authorization": f"Bot {self.bot_token}"})
            if r.status == 404: #Discord returns 404 if no ban
                self.bot.log.debug(f"User {user['username']} not banned. Redirecting to error page")
                return web.HTTPSeeOther(f"{self.config['server_url']}/notbanned")
            elif r.status == 401: #401 returned if cannot check
                self.bot.log.warning("Ban check returned 401! Please check token and server permissions! Continuing without check")
            elif r.status == 200: #Returns 200 if the user is banned
                self.bot.log.debug(f"Confirmed user {user['username']} is banned. Proceeding with submission")
            else: #If something else happens, send a warning. This ideally should never happen.
                ban = await r.json()
                self.bot.log.warning(f"Ban check returned message: {ban['message']}. Continuing without check")
        
        self.ids[random] = {"submitted": datetime.utcnow(), "object": user}
        with open("appealed_users.txt") as f:
            already_appealed = f.read().splitlines()
        if user['id'] in already_appealed:
            return web.HTTPSeeOther(f"{self.config['server_url']}/error")    
        return web.HTTPSeeOther(f"{self.config['server_url']}/appeal?id={random}")

    def random_string(self, length):
        return ''.join(choice(ascii_letters) for x in range(length))