from googleapiclient import discovery
import os
import json
import unidecode as decode
from deep_translator import GoogleTranslator as GoogleTranslate
import pandas as pd
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns


token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    perspective_token = tokens['perspective']
    print("perspective successfully activated")

    
def analyzer(text_to_analyze):
    client = discovery.build("commentanalyzer","v1alpha1", developerKey=perspective_token,
    discoveryServiceUrl="https://commentanalyzer.googleapis.com/$discovery/rest?version=v1alpha1",
    static_discovery=False,)

    try: # for foreign language detection
        analyze_request = {
        'comment': { 'text': text_to_analyze },
        'requestedAttributes': {'THREAT': {}}
        }
        response = client.comments().analyze(body=analyze_request).execute()
    except:
        text_to_analyze = GoogleTranslate(source='auto', target='english').translate(text_to_analyze)
        analyze_request = {
        'comment': { 'text': text_to_analyze},
        'requestedAttributes': {'THREAT': {}}
        }
        try: 
            response = client.comments().analyze(body=analyze_request).execute()
        except: 
            return -1 
    #print(json.dumps(response, indent=2))
    #print(response)
    return response['attributeScores']['THREAT']['spanScores'][0]['score']['value']

def confusionMatrix():
    # Read the Excel file into a pandas DataFrame
    df = pd.read_excel('path_to_your_excel_file.xlsx')

    # Assuming the first column is 'strings' and the second column is 'labels'
    messages = df.iloc[:,0]
    y_true = df.iloc[:, 1]  # Get the ground truth labels
    y_pred = [1 if analyzer(message) > .5 else 0 for message in messages] # Get the predicted labels

    # Build the confusion matrix
    cm = confusion_matrix(y_true, y_pred)

    # Visualize the confusion matrix
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
    plt.title("Confusion Matrix")
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.show()

confusionMatrix()