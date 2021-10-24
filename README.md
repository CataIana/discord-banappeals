# Ban Appeals Bot

Allows users to submit ban appeals by logging in with discord and submitting a reason why they should be unbanned.
Output is directed to one or multiple webhooks

## Known Issues
Some characters are not properly decoded in the appeal embed.

# Setup:
* This setup assumes you are using the reverse proxy server nginx.
* Copy the provided `nginx_conf` file to `/etc/nginx/sites-enabled`, renaming it as necessary.
* Set the \<server-name>, the \<directory> that the cloned folder is in, and if necessary, replace the with a port of your choice, The default is 5005
* Optionally you can replace the logo.png with anything you like
* Before starting the bot, install the few depdendencies `sudo pip3 install --upgrade discord.py aiohttp`
* Create a new discord application, and under Oauth2, add a redirect uri with `<server-name>/authorize`, replacing `<server-name>` with your domain. Eg `https://example.com/authorize`
* Rename `exampleconfig.json` to `config.json` and fill in the required fields. If you changed the port in the nginx configuration file, set the proxy_port to the same port.
* Finally, you should be able to just run the bot, with `python3 bot.py`.

* Optionally, the script can also check if users are actually banned, preventing useless appeals. This requires a guild ID, a Bot token, and the bot to be authorized with the ban members permission in the server. Check will be ignored if any of these values are not provided

```
{
    "client_id": "The client ID of the discord application. Create in https://discordapp.com/developers/applications/",
    "client_secret": "The client secret of the discord application. Found in the same location as the client ID",
    "server_url": "The server url for redirects. Example: https://example.com",
    "webhook_urls": "Either one or multiple webhook urls to send ban appeals to",
    "proxy_port": 5005,
    "guild_id": "Only required if checking bans before submission",
    "bot_token": "Only required if checking bans before submission
    "check_ban_before_submission": false
}```
