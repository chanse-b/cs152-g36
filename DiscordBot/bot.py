# bot.py
# Chanse Bhakta, Febie Lin, Itbaan Nafi, Mo Akintan, Raul Ruiz-Solis, William Wang
# TODO:
# forward message to an authorities channel
# Adverseral countermeasures:
#   1. Moderators can see reported message history if edits were made
#   2. Messages in Foreign languages are translated to english for the moderator and at the reporter's discreation
#   3. Unicode detection

import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests #for google vm
from report import Report
from report import State
from deep_translator import GoogleTranslator as GoogleTranslate
import unidecode as decode
from classify import analyzer


import pdb

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        try:
            intents.message_content = True
        except:
            intents.messages = True
        
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.user_messages = {} # Map of user ID , which is a map of message id: to message history
        self.blacklist = {} # Map of how many times somone has been reported
        self.report_channel = None
        self.authorities_channel = None
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
                    self.report_channel = channel
                    await self.report_channel.send("commands available to you:\n" + "ban [user]\n" + "delete [message link]\n" + "see [user] history\n")
                elif channel.name == f'group-{self.group_num}-authorities':
                    self.authorities_channel = self.authorities_channel[guild.id]
                elif channel.name == f'group-{self.group_num}':
                    self.main_channel = channel 
        
                    
    async def on_raw_message_edit(self,payload):
        channel = await self.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        self.user_messages[message.author.id][message.id].append(message.content) #if a message is edited, update the map
        # analyze the message for harmful content
        scores = self.eval_text(message.content)
        decoded_scores =  self.eval_text(decode.unidecode(message.content))
        if scores[0] > .5:
            await self.report_channel.send("-----------------------------------")
            await self.report_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            await self.report_channel.send("Translated message from detectected language:" + GoogleTranslate(source='auto', target='english').translate(message.content))
            await self.report_channel.send("This message has been edited. Consider viewing the user's history")
            await self.report_channel.send(self.code_format(scores))
            await self.report_channel.send("-----------------------------------")
            if message.author.name not in self.blacklist:
                self.blacklist[message.author.name] = 0
            self.blacklist[message.author.name] += 1
            if self.blacklist[message.author.name] >= 4:
                await self.report_channel.send("```" + message.author.name + "```" + "has been reported " + str(self.blacklist[message.author.name]) + " times, consider banning")
        elif decoded_scores[0] > .5:
            await self.report_channel.send("-----------------------------------")
            await self.report_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            await self.report_channel.send("The message was encoded. Decoded as: " + str(decode.unidecode(message.content)))
            await self.report_channel.send(f'Forwarded message:\n{message.author.name}: "{decode(message.content)}"')
            await self.report_channel.send("Translated message from detectected language:" + GoogleTranslate(source='auto', target='english').translate(decode.unidecode(message.content)))
            await self.report_channel.send("This message has been edited. Consider viewing the user's history")
            await self.report_channel.send(self.code_format(scores))
            await self.report_channel.send("-----------------------------------")
            if message.author.name not in self.blacklist:
                self.blacklist[message.author.name] = 0
            self.blacklist[message.author.name] += 1
            if self.blacklist[message.author.name] >= 4:
                await self.report_channel.send("```" + message.author.name + "```" + "has been reported " + str(self.blacklist[message.author.name]) + " times, consider banning")
        elif scores == -1: # message could not be scanned, send to manual review
            await self.report_channel.send( "Consider viewing " + '`' + message.author.name + '`' + "'s history, message " +  '`'+message.content +'`' " could not be scanned")
                
        

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
            reply = "Hi, " + "`" + message.author.name + "`" + ", say" + " `help` " + "if you need assistance. \n" 
            await message.channel.send(reply)
            return 

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete() or self.reports[author_id].report_cancelled():
            if Report.reported_message != None:
                if "school" in Report.tags or "public" in Report.tags:
                    await self.report_channel.send("This is the threat specialist channel. use the command 'forward to authorities' to contact the local authorities")
                reported_user = Report.reported_message.author.name
                await self.report_channel.send("```" + message.author.name + "```" + "has initiated a report with the following status: " + Report.tags + "\n")
                report_to_send = "Original Reported Message:" + "```" + reported_user + ": " + Report.reported_message.content + "```"
                await self.report_channel.send(report_to_send)
                report_to_send = "Decoded Reported Message:" + "```" + reported_user + ": " + decode.unidecode(Report.reported_message.content) + "```"
                await self.report_channel.send(report_to_send)
                report_to_send = "Translated Reported Message:" + "```" + reported_user + ": " + GoogleTranslate(source='auto', target='english').translate(Report.reported_message.content) + "```"
                await self.report_channel.send(report_to_send)
                await self.report_channel.send("Here is the message link :" + Report.message_link)
                if Report.context != None:
                    await self.report_channel.send("the user gives the following context: " + "```" + Report.context + "```")
                if Report.reported_message.id in self.user_messages[Report.reported_message.author.id] and len(self.user_messages[Report.reported_message.author.id][Report.reported_message.id]) > 1:
                    await self.report_channel.send("here's the message history (oldest to newest): ")
                    message_history = self.user_messages[Report.reported_message.author.id][Report.reported_message.id]
                    for m in message_history:
                        await self.report_channel.send("```" + reported_user + ": " + m + "```" + "\nTranslated: " + "```" + GoogleTranslate(source='auto', target='english').translate(m) + "```")
                        await self.report_channel.send("-----------------------------------")

            #await self.authorities_channel.send("WARNING: CREDIBLE THREAT")
            #await Report.reported_message.delete()
            if self.reports[author_id].report_complete():
                if Report.reported_message.author.name not in self.blacklist:
                    self.blacklist[reported_user] = 0
                self.blacklist[reported_user] += 1
                if self.blacklist[reported_user] >= 4:
                    await self.report_channel.send("```" + reported_user + "```" + "has been reported " + str(self.blacklist[reported_user]) + " times, consider banning")
            Report.reported_message = None
            Report.context = None
            Report.tags = ""
            self.reports.pop(author_id)
            print(self.blacklist)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-36" channel
        #if not message.channel.name == f'group-{self.group_num}':
        #    return
        mod_channel = self.mod_channels[message.guild.id]
        if message.channel.name == f'group-{self.group_num}-mod':
            if "delete" in message.content.lower():
                message.content = message.content.lower().replace("delete", "")
                m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
                if not m: return 
                guild = self.get_guild(int(m.group(1)))
                if not guild: return
                channel = guild.get_channel(int(m.group(2)))
                if not channel: return
                to_delete = await channel.fetch_message(int(m.group(3)))
                try: 
                    await to_delete.delete()
                except:
                    pass
                await mod_channel.send("message deleted")
            elif "ban" in message.content.lower():
                message.content = message.content.lower().replace("ban", "")
                texts = [message async for message in self.main_channel.history(limit=None)]
                match = False
                target = ""
                for text in texts:
                    print("Check if the message was sent by the target user")
                    print(text.author.name, ":", message.content)
                    if text.author.name.lower() in message.content:
                        # Delete the message
                        await text.delete()
                        match = True
                        target = text.author.name
                        print(target)
                        print(f"Deleted message: {message.content}")
                if match: await self.report_channel.send("`"+ target +"`" + " was banned successfully")
                print(target)
            elif "see" and "history" in message.content.lower():
                message.content = message.content.lower().replace("see history", "")
                texts = [message async for message in self.main_channel.history(limit=None)]
                for text in texts:
                    print("Check if the message was sent by the target user")
                    print(text.author.name, ":", message.content)
                    if text.author.name.lower() in message.content:
                        await self.report_channel.send("```" + text.author.name + ": " + text.content + "```" + "Translated: " + "```" + GoogleTranslate(source='auto', target='english').translate(text.content) + "```")
                        await self.report_channel.send("-----------------------------------")
            elif "forward to authorities" in message.content:
                 await self.report_channel.send("this report will be forwarded to the authorities")
                
        # MODIFY TO SEND FLAGGED OR REPORTED MESSAGES ONLY 
        elif message.channel.name == f'group-{self.group_num}':
            scores = self.eval_text(message.content)
            decoded_scores = self.eval_text(decode.unidecode(str(message.content)))
            if scores[0] > .5:
                await self.report_channel.send("-----------------------------------")
                await self.report_channel.send("This is the threat specialist channel. use the command 'forward to authorities' to contact the local authorities")
                await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
                await mod_channel.send("Translated message from detectected language:" + GoogleTranslate(source='auto', target='english').translate(message.content))
                await mod_channel.send(self.code_format(scores))
                await self.report_channel.send("-----------------------------------")
                if message.author.name not in self.blacklist:
                    self.blacklist[message.author.name] = 0
                self.blacklist[message.author.name] += 1
                if self.blacklist[message.author.name] >= 4:
                    await self.report_channel.send("```" + message.author.name + "```" + "has been reported " + str(self.blacklist[message.author.name]) + " times, consider banning")
            elif decoded_scores[0] > .5:
                await self.report_channel.send("-----------------------------------")
                await self.report_channel.send("This is the threat specialist channel. use the command 'forward to authorities' to contact the local authorities")
                await mod_channel.send(f'Forwarded decoded message:\n{message.author.name}: "{decode.unidecode(message.content)}"')
                await mod_channel.send("Translated message from detectected language:" + GoogleTranslate(source='auto', target='english').translate(decode.unidecode(message.content)))
                await mod_channel.send(self.code_format(decoded_scores))
                await self.report_channel.send("-----------------------------------")
                if message.author.name not in self.blacklist:
                    self.blacklist[message.author.name] = 0
                self.blacklist[message.author.name] += 1
                if self.blacklist[message.author.name] >= 4:
                    await self.report_channel.send("```" + message.author.name + "```" + "has been reported " + str(self.blacklist[message.author.name]) + " times, consider banning")
            elif scores[0] == -1 or decoded_scores[0] == -1:
                await self.report_channel.send( "Consider viewing " + '`' + message.author.name + '`' + "'s history, message could not be scanned")
    
        
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        print(analyzer(message), message)
        return analyzer(message)

    
    def code_format(self, scores):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated " + str(scores[1]).upper() + " Threat" + " with: '" + str(scores[0]*100) + "% confidence"
    
client = ModBot()
client.run(discord_token)
