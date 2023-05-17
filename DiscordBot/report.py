from enum import Enum, auto
import discord
import re
from deep_translator import GoogleTranslator as GoogleTranslate

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    MESSAGE_TO_TRANSLATE = auto()
    AWAITING_CONTEXT = auto()
    REPORT_COMPLETE = auto()
    DANGER_REPORT = auto()
    SPAM_REPORT = auto()
    HARRASSMENT_REPORT = auto()
    OFFENSIVE_REPORT = auto()
    AWAITING_BLOCK_DECISION = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    PROCEED_KEYWORD = "continue"
    reported_message = None
    reported_message_history = None
    message_link = None
    
    
    context = None
    tags = ""
    
    IMMINENT_DANGER = "imminent danger"
    OFFENSIVE_CONTENT = "offensive content"
    HARASSMENT = "harassment"
    SPAM = "spam"
    AbuseTypes = [IMMINENT_DANGER, OFFENSIVE_CONTENT, HARASSMENT, SPAM]
    offensive_bins = ["personally-targeted content", "hate speech", "explicit content", "graphic content", "encouragement of violence"]
    harrasment_bins = ["stalking", "impersonation", "doxxing", "unwanted sexual content", "trolling"]
    spam_bins = ["solicitation","fraud", "phishing", "propaganda"]
    bins = offensive_bins + spam_bins + harrasment_bins


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
            Report.reported_message = None
            Report.tags = ""
            return ["Report cancelled."]
        
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "To start, please copy and paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            Report.message_link = message.content 
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
                Report.reported_message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED 
            reply = []
            reply += ["Say 'translate' if you'd like me translate the message"]
            reply += ["I found this message:", "```" + self.reported_message.author.name + ": " + self.reported_message.content + "```", \
                    "Enter 'continue' to continue reporting, or 'cancel' to cancel"]
            return reply
        if self.state == State.MESSAGE_IDENTIFIED and "translate" in message.content:
            return ["I found this message:", "```" + self.reported_message.author.name + ": " + GoogleTranslate(source='auto', target='english').translate(self.reported_message.content) + "```", \
                    "Enter 'continue' to continue reporting, or 'cancel' to cancel"]
            
       
        if message.content == self.PROCEED_KEYWORD and self.state == State.MESSAGE_IDENTIFIED:
            reply = "Please select a classification for this message. Say 'more info' for more information\n\n"
            reply += "Spam\n"
            reply += "Harassment\n"
            reply += "Offensive Content \n"
            reply += "Imminent Danger \n"
            return [reply]
                
        if message.content.lower() == 'more info' and self.state == State.MESSAGE_IDENTIFIED:
            reply = "Here's some more information to what the classifcations mean: \n\n"
            reply += "Spam: Any unwanted, unsolicited communcation\n"
            reply += "Harassment: a repeated pattern of behavior intended to scare, harm, anger, or shame a targeted individual \n"
            reply += "Offensive Content: Content that is defamitory, obscene, pornographic, gratuitously violenent or causes another person to be offended, scared, or worried.\n"
            reply += "Imminent Danger: Somone or a group of persons who's life may be in danger now or in future.\n"
            return [reply]
        elif message.content not in self.AbuseTypes and self.state == State.MESSAGE_IDENTIFIED:
            return ["I didn't quite catch that. Please try again or enter 'cancel' to cancel 1"]
        
        if message.content == self.IMMINENT_DANGER and self.state == State.MESSAGE_IDENTIFIED:
            self.state = State.DANGER_REPORT
            Report.tags += message.content + ","
            reply = "You have indicated someone is in imminent danger. If your safety is in jeopardy, it is recommended that you call 911 \n\n"
            reply += "please tell me more about the situation using the following options:  \n"
            reply += "School Threat \n"
            reply += "Personal Threat \n"
            reply += "Public Threat \n\n"
            reply += "Or say 'more info' for more information"
            return [reply]
        if message.content == 'more info' and self.state == State.DANGER_REPORT:
            reply = "Here's some more information to what these types of threats are: \n\n"
            reply += "School Threat: A threat against a public, private, or secondary school \n"
            reply += "Personal Threat: a threat against you or someone else \n"
            reply += "Public Threat: a threat against an institution or against a group of people \n"
            return [reply]
        
        if message.content == self.SPAM and self.state == State.MESSAGE_IDENTIFIED:
            self.state = State.SPAM_REPORT
            Report.tags += message.content + ","
            reply = "You have indicated this message is spam \n"
            reply += "please tell me more about the situation using the following options: \n\n"
            reply += "Solicitation \n"
            reply += "Fraud and/or Phishing \n"
            reply += "Propaganda \n\n"
            reply += "Or say 'more info' for more information"
            return [reply]
        if message.content == 'more info' and self.state == State.SPAM_REPORT:
            reply = "Here's some more information to what these types of spam are: \n\n"
            reply += "Solicitation: the offense of offering money to someone with the specific intent of inducing that person to commit a crime \n"
            reply += "Fraud and/or Phishing: wrongful or criminal deception intended to result in financial or personal gain. \n"
            reply += "Propaganda : the dissemination of information—facts, arguments, rumours, half-truths, or lies—to influence public opinion \n"
            return [reply]
        elif self.state == State.SPAM_REPORT and message.content not in self.bins:
            return ["I didn't quite catch that. Please try again or enter 'cancel' to cancel 2"]
        
        if message.content == self.HARASSMENT and self.state == State.MESSAGE_IDENTIFIED:
            self.state = State.HARRASSMENT_REPORT
            Report.tags += message.content + ","
            reply = "You have indicated this message is harassment \n"
            reply += "please tell me more about the situation using the following options: \n\n"
            reply += "Unwanted Sexual Content \n"
            reply += "Stalking \n"
            reply += "Impersonation \n"
            reply += "Doxxing \n\n"
            reply += "Or say 'more info' for more information"
            return [reply]
        if message.content == 'more info' and self.state == State.HARRASSMENT_REPORT:
            reply = "Here's some more information to what these types of spam are: \n\n"
            reply += "Unwanted Sexual Content: Can inclucde being sent or shown naked or semi-naked images (nudes), receiving sexual messages, or being sent links to sexual videos\n"
            reply += "Stalking: the crime of illegally following and watching someone over a period of time\n"
            reply += "Impersonation: Somone pretending to be you or someone else\n"
            reply += "Doxxing: search for and publish private or identifying information about (a particular individual) on the internet, typically with malicious intent. \n"
            return [reply]
        elif self.state == State.HARRASSMENT_REPORT and message.content not in self.bins:
            return ["I didn't quite catch that. Please try again or enter 'cancel' to cancel 3"]
        
        if message.content == self.OFFENSIVE_CONTENT and self.state == State.MESSAGE_IDENTIFIED:
            self.state = State.OFFENSIVE_REPORT
            Report.tags += message.content + ","
            reply = "You have indicated this message is offensive \n\n"
            reply += "please tell me more about the situation using the following options: \n"
            reply += "Hate Speech \n"
            reply += "Explicit Content \n"
            reply += "Graphic content \n"
            reply += "Personally-Targeted content\n"
            reply += "Encouragement of Violence\n\n"
            reply += "Or say 'more info' for more information"
            return [reply]
        if message.content == 'more info' and self.state == State.OFFENSIVE_REPORT:
            reply = "Here's some more information to what these types of spam are: \n\n"
            reply += "Hate Speech: Abusive or threatening speech or writing that expresses prejudice on the basis of ethnicity, religion, sexual orientation, or similar grounds. \n"
            reply += "Explicit Content: <Need a definition here> \n"
            reply += "Graphic content: Any type of visual material that is considered disturbing, offensive, or inappropriate\n"
            reply += "Personally-Targeted content: <>\n"
            reply += "Encouragement of Violence: Somone encouraging violance toward an individual, group of people, or other entity\n"
            return [reply]
        elif self.state == State.OFFENSIVE_REPORT and message.content not in self.bins:
            return ["I didn't quite catch that. Please try again or enter 'cancel' to cancel 4"]
        
        if (self.state == State.OFFENSIVE_REPORT or self.state == State.HARRASSMENT_REPORT or self.state == State.SPAM_REPORT) and message.content.lower() in self.bins:
            self.state = State.AWAITING_CONTEXT 
            Report.tags += message.content
            return ["Please include more details describing the context behind this comment."]
        
        if self.state == State.AWAITING_CONTEXT:
            # send context + the report to moderation channel
            print("message.content before context is set:", message.content)
            Report.context = message.content
            print(Report.tags)
            reply = "Thank you for reporting this. It will now be reviewed by our moderation team. We will be in touch if we require additional information.\n"
            reply += "Do you want to block this user?"
            self.state = State.AWAITING_BLOCK_DECISION
            return [reply]
        
        if self.state == State.AWAITING_BLOCK_DECISION and message.content.lower() == "yes":
             # block the user
            self.state = State.REPORT_COMPLETE
            return ["user has been blocked"]
        elif self.state == State.AWAITING_BLOCK_DECISION and message.content.lower() == "no":
            self.state = State.REPORT_COMPLETE
            return ["user has not been blocked"]
        elif self.state == State.AWAITING_BLOCK_DECISION:
            return ["sorry, I'm afraid I didn't get that. Can you please try again?"]
        
        if self.state == State.DANGER_REPORT and "threat" in message.content.lower() and ("school" or "public") in message.content.lower():
            if "school" in message.content.lower(): Report.tags += "school threat"
            elif "public" in message.content.lower(): Report.tags += "public threat"
            print(Report.tags," ", Report.reported_message)
            self.state = State.REPORT_COMPLETE
            ## route message to authorities
            reply = "Thank you for your report. It has been successfully received and will be reviewed by our content moderation team and sent to local authorities\n" 
            reply += "If you have reason to believe that someone is in grave danger, please contact 911."
            return [reply]
        elif self.state == State.DANGER_REPORT and "threat" in message.content.lower():
            self.state = State.REPORT_COMPLETE
            Report.tags += "personal"
            reply = "Thank you for your report. It has been successfully received and will be reviewed by our content moderation team\n" 
            reply += "If you have reason to believe that someone is in grave danger, please contact 911."
            return [reply]
        elif self.state == State.DANGER_REPORT:
            return ["I didn't quite catch that. Please try again or enter 'cancel' to cancel 5"]
        if self.state == State.REPORT_COMPLETE:
            return self.state == State.REPORT_COMPLETE
        
    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
        
    


    

