# bot.py
# TODO:

# forward message to an authorities channel
# Implinent a strike system that checks how many times a user has been reported

import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests #for google vm
from report import Report
from deep_translator import GoogleTranslator as GoogleTranslate

 
import pdb

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'DiscordBot/tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.messages = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.user_messages = {} # Map of user ID , which is a map of message id: to message history
        self.toreport = None
        self.authorities = None
        self.main_channel = None

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
                    self.toreport = channel
                elif channel.name == f'group-{self.group_num}-authorities':
                    self.authorities = self.authorities[guild.id]
                elif channel.name == f'group-{self.group_num}':
                    self.main_channel = channel
                    
    async def on_raw_message_edit(self,payload):
        channel = await self.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        self.user_messages[message.author.id][message.id].append(message.content) #if a message is edited, update the map

                
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            if message.author.id not in self.user_messages:
                self.user_messages[message.author.id] = {message.id: []}
            if message.id not in self.user_messages[message.author.id]:
                self.user_messages[message.author.id][message.id] = []
            self.user_messages[message.author.id][message.id].append(message.content)
            print(self.user_messages)
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content.lower() == Report.HELP_KEYWORD:
            reply = "Hi, " + "`" + message.author.name + "`" + ", it is my pleasure to assist you today. \n" 
            reply +=  "Please use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.lower().startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            if Report.reported_message != None:
                await self.toreport.send("```" + message.author.name + "```" + "has initiated a report with the following status: " + Report.tags + "\n")
                report_to_send = "Original Reported Message:" + "```" + Report.reported_message.author.name + ": " + Report.reported_message.content + "```"
                await self.toreport.send(report_to_send)
                report_to_send = "Translated Reported Message:" + "```" + Report.reported_message.author.name + ": " + GoogleTranslate(source='auto', target='english').translate(Report.reported_message.content) + "```"
                await self.toreport.send(report_to_send)
                await self.toreport.send("Here is the message link :" + Report.message_link)
                if Report.context != None:
                    await self.toreport.send("the user gives the following context: " + "```" + Report.context + "```")
                elif "school" or "public" in Report.tags:
                    pass
                if Report.reported_message.id in self.user_messages[Report.reported_message.author.id] and len(self.user_messages[Report.reported_message.author.id][Report.reported_message.id]) > 1:
                    await self.toreport.send("here's the message history (oldest to newest): ")
                    message_history = self.user_messages[Report.reported_message.author.id][Report.reported_message.id]
                    for m in message_history:
                        await self.toreport.send("```" + Report.reported_message.author.name + ": " + m + "```" + "\nTranslated: " + "```" + GoogleTranslate(source='auto', target='english').translate(m) + "```")
                        await self.toreport.send("-----------------------------------")

            #await self.authorities.send("WARNING: CREDIBLE THREAT")
            #await Report.reported_message.delete()
            Report.reported_message = None
            Report.context = None
            Report.tags = ""
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-36" channel
        #if not message.channel.name == f'group-{self.group_num}':
        #    return
        mod_channel = self.mod_channels[message.guild.id]
        if message.channel.name == f'group-{self.group_num}-mod':
            if "delete" in message.content.lower():
                message.content = message.content.lower().replace("delete", "")
                m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
                guild = self.get_guild(int(m.group(1)))
                channel = guild.get_channel(int(m.group(2)))
                to_delete = await channel.fetch_message(int(m.group(3)))
                await to_delete.delete()
                await mod_channel.send("message deleted")
            if "ban" in message.content.lower():
                message.content = message.content.lower().replace("ban", "")
                texts = await self.main_channel.history(limit=None).flatten()
                for text in texts:
                    print("Check if the message was sent by the target user")
                    print(text.author.name, ":", message.content)
                    if text.author.name.lower() in message.content:
                        # Delete the message
                        await text.delete()
                        print(f"Deleted message: {message.content}")
            await mod_channel.send("Done")
    
        # MODIFY TO SEND FLAGGED OR REPORTED MESSAGES ONLY 
        elif message.channel.name == f'group-{self.group_num}':
            scores = self.eval_text(message.content)
            if scores > 0:
                await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
                await mod_channel.send(self.code_format(scores))
       
        
    
        
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return 0

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"
    
client = ModBot()
client.run(discord_token)