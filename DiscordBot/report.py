from enum import Enum, auto
import discord
import re
from langdetect import detect
from deep_translator import GoogleTranslator as GoogleTranslate

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    DANGER_REPORT = auto()
    SPAM_REPORT = auto()
    HARRASSMENT_REPORT = auto()
    OFFENSIVE_REPORT = auto()
    BLOCK_USER = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    PROCEED_KEYWORD = "continue"
    
    IMMINENT_DANGER = "imminent danger"
    OFFENSIVE_CONTENT = "offensive content"
    HARASSMENT = "harassment"
    SPAM = "spam"
    AbuseTypes = [IMMINENT_DANGER, OFFENSIVE_CONTENT, HARASSMENT, SPAM]


    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''
        message.content = message.content.lower()
        print(message.content)
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED 
            reply = []
            reply += ["I will translate the message into English if necessrary"]
            reply += ["I found this message:", "```" + message.author.name + ": " + GoogleTranslate(source='auto', target='english').translate(message.content) + "```", \
                    "Enter 'continue' to continue reporting, or 'cancel' to cancel"]
            return reply
            
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
            
        if message.content == self.PROCEED_KEYWORD:
            reply = "Please select the reason for reporting this message. Say `help` at any time for more information.\n\n"
            reply += "Spam\n"
            reply += "Harassment\n"
            reply += "Offensive Content \n"
            reply += "Imminent Danger \n"
            self.state = State.MESSAGE_IDENTIFIED
            return [reply+"<insert rest of reporting flow here>"]
    
        if message.content not in self.AbuseTypes and self.state == State.MESSAGE_IDENTIFIED:
            return ["I didn't quite catch that. Please try again or enter 'cancel' to cancel"]
        if message.content == self.IMMINENT_DANGER and self.state == State.MESSAGE_IDENTIFIED:
            self.state = State.DANGER_REPORT
            reply = "You have indicated someone is in imminent danger. If your safety is in jeopardy, it is recommended that you call 911 \n\n"
            reply += "please tell me more about the situation using the following options: \n"
            reply += "School Threat \n"
            reply += "Personal Threat \n"
            reply += "Public Threat \n"
            return [reply]
        elif message.content == self.SPAM and self.state == State.MESSAGE_IDENTIFIED:
            self.state = State.SPAM_REPORT
            reply = "You have indicated this message is spam \n\n"
            reply += "please tell me more about the situation using the following options: \n"
            reply += "I think this is a bot \n"
            reply += "Trying to sell me something \n"
            return [reply]
        elif message.content == self.HARASSMENT and self.state == State.MESSAGE_IDENTIFIED:
            self.state = State.HARRASSMENT_REPORT
            reply = "You have indicated this message is harassment \n\n"
            reply += "please tell me more about the situation using the following options: \n"
            reply += "Unwanted Sexual Content \n"
            reply += "blah \n"
            reply += "blah blah \n"
            return [reply]
        elif message.content == self.OFFENSIVE_CONTENT and self.state == State.MESSAGE_IDENTIFIED:
            self.state = State.OFFENSIVE_REPORT
            reply = "You have indicated this message is offensive \n\n"
            reply += "please tell me more about the situation using the following options: \n"
            reply += "Hate Speech \n"
            reply += "Explicit Content \n"
            reply += "blah blah \n"
            return [reply]
        if self.state == State.DANGER_REPORT and "threat" in message.content.lower() and ("school" or "public") in message.content.lower():
            self.state = State.REPORT_COMPLETE
            reply = []
            ## route message to authorities
            if "school" or "public" in message.content.lower(): reply += ["WILL SEND TO LOCAL AUTHORITIES \n"]
            reply += ["Thank you for your report. It has been successfully received and will be reviewed by our content moderation team\n" 
                    + "If you have reason to believe that someone is in grave danger, please contact 911."]
            return [reply]
        elif self.state == State.DANGER_REPORT and "threat" in message.content.lower():
            self.state = State.REPORT_COMPLETE
            return ["Thank you for your report. It has been successfully received and will be reviewed by our content moderation team\n" 
                    + "If you have reason to believe that someone is in grave danger, please contact 911."]
        if self.state == State.REPORT_COMPLETE:
            return self.state == State.REPORT_COMPLETE
        
    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
        
    


    

