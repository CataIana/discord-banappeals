# Ban Appeals Bot

Allows users to submit ban appeals by logging in with discord and submitting a reason why they should be unbanned.
Output is directed to one or multiple webhooks

This setup assumes you are using the reverse proxy server nginx.
# Setup:
* Ensure you have a working nginx setup.
* Copy the provided `nginx_conf` file to `/etc/nginx/sites-enabled`, renaming it as necessary.
* Set in the <server-name>, the <directory> that the cloned folder is in, and if necessary, replace the with a port of your choice, The default is 5005
* Optionally you can replace the logo.png with anything you like
* Before starting the bot, install the few depdendencies `sudo pip3 install --upgrade discord.py aiohttp`
* Create a new discord application, and under Oauth2, add a redirect uri with `<server-name>/authorize`, replacing `<server-name>` with your domain. Eg `https://example.com/authorize`
* Rename `exampleconfig.json` to `config.json` and fill in the required fields. If you changed the port in the nginx, set the proxy_port to the same port.
* Finally, you should be able to just run the bot, with `python3 bot.py`.
