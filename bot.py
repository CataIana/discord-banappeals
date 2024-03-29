from disnake import Colour, Embed, Webhook, HTTPException, NotFound
from aiohttp import ClientSession
from webserver import RecieverWebServer
from datetime import datetime
from textwrap import shorten
import asyncio
import logging
import signal
import sys



class Appeals():
    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()

        self.format = logging.Formatter(
            '%(asctime)s:%(levelname)s:%(name)s: %(message)s')
        self.log_level = logging.INFO
        self.log = logging.getLogger("Discord Ban Appeals")
        self.log.setLevel(self.log_level)

        chandler = logging.StreamHandler(sys.stdout)
        chandler.setLevel(self.log_level)
        chandler.setFormatter(self.format)
        self.log.addHandler(chandler)

        self.web_server = RecieverWebServer(self)
        self.loop.run_until_complete(self.web_server.start())

        self.colour = Colour.from_rgb(128, 0, 128)
        self.pending_users = []
    
    def run(self):
        try:
            self.loop.add_signal_handler(signal.SIGINT, lambda: self.loop.stop())
            self.loop.add_signal_handler(signal.SIGTERM, lambda: self.loop.stop())
        except NotImplementedError:
            pass

        self.loop.create_task(self.ready())
        self.loop.create_task(self.cleanup_ids())
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.log.info('Received signal to terminate bot and event loop.')
        finally:
            self.loop.run_until_complete(self.close())

    async def cleanup_ids(self):
        for user in self.web_server.ids.keys():
            if (datetime.utcnow() - self.web_server.ids[user]["submitted"]) > 600:
                del self.web_server.ids[user]
        await asyncio.sleep(600)
        
    async def ready(self):
        self.aSession = ClientSession()
        self.log.info(f"------ Web Server Running ------")
        self.log.info(f"Appeals URL: {self.web_server.config['server_url']}")
        # Permission integer 4 for fetch ban permission
        self.log.info(f"Invite URL: https://discord.com/oauth2/authorize?client_id={self.web_server.config['client_id']}&scope=bot&permissions=4")

    async def close(self):
        if not self.aSession.closed:
            await self.aSession.close()
        self.log.info("Shutting down...")

    def get_avatar(self, user):
        if user["avatar"]:
            ext = "gif" if user["avatar"].startswith("a_") else "png"
            return f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.{ext}?size={128}"
        else:
            key = int(user['discriminator']) % 5
            return f"https://cdn.discordapp.com/embed/avatars/{key}.png"

    async def submit_appeal(self, id, user, ban_age, justified_ban, ban_reason, ban_appeal, extra_message):
        self.log.info(f"Submitting appeal for {user['username']}#{user['discriminator']} ({user['id']})")
        embed = Embed(title="New Appeal", colour=self.colour, timestamp=datetime.utcnow())
        ban_age_dict = {
            "lessthan31d": "Less than 31 days ago",
            "13months": "1-3 Months ago",
            "36months": "3-6 Months ago",
            "612months": "6-12 Months ago",
            "morethan12m": "More than a year ago"
        }

        embed.add_field(name="When did you recieve your ban?", value=ban_age_dict[ban_age], inline=False)
        embed.add_field(name="Do you think the ban was justified?", value="Yes" if justified_ban == "yes" else "No", inline=False)
        embed.add_field(name="Why do you think you were banned?", value=shorten(ban_reason, width=1024), inline=False)
        embed.add_field(name="Why do you think you should be unbanned?", value=shorten(ban_appeal, width=1024), inline=False)
        if extra_message != "":
            embed.add_field(name="Is there anything else you would like to add?", value=shorten(extra_message, width=1024), inline=False)
        embed.set_author(name=f"{user['username']}#{user['discriminator']}", icon_url=self.get_avatar(user))
        embed.set_footer(text=f"User ID: {user['id']}")
        if type(self.web_server.config["webhook_urls"]) == list:
            webhooks = [Webhook.from_url(url, session=self.aSession) for url in self.web_server.config["webhook_urls"]]
        else:
            webhooks = [Webhook.from_url(self.web_server.config["webhook_urls"], session=self.aSession)]
        for webhook in webhooks:
            try:
                await webhook.send(embed=embed)
            except HTTPException:
                pass
            except NotFound:
                pass

        with open("appealed_users.txt", "a+") as f:
            f.write(f"{user['id']}\n")
    

bot = Appeals()
bot.run()
