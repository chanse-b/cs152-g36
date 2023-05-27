from queue import PriorityQueue
from googleapiclient import discovery
import os
import json

token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    perspective_token = tokens['perspective']
    print("success")
    
#def analyzer(message):
    text_to_analyze = "Howdy Partner!"
    client = discovery.build("commentanalyzer","v1alpha1", developerKey=perspective_token,
    discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
    static_discovery=False,)

    analyze_request = {
    'comment': { 'text': text_to_analyze },
    'requestedAttributes': {'THREAT': {}}
    }
    response = client.comments().analyze(body=analyze_request).execute()
    print(json.dumps(response, indent=2))