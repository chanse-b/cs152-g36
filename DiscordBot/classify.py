from googleapiclient import discovery
import os
import json
import unidecode as decode
from deep_translator import GoogleTranslator as GoogleTranslate
import pandas as pd
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report


token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    perspective_token = tokens['perspective']
    print("perspective successfully activated")
    df = pd.read_csv('label_data.csv')
    # Step 2: Preprocess text and create feature vectors
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(df['message'])
    y = df['label']
    # training the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=1, random_state=42)
    #Train a Multinomial Naive Bayes classifier
    classifier = MultinomialNB()
    classifier.fit(X_train, y_train)


def threat_labeler(message):
    # Step 6: Print classification report
    #print(classification_report(y_test, y_pred))
    return classifier.predict(vectorizer.transform([message]))[0]

    

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
            return -1, None
    #print(json.dumps(response, indent=2))
    #print(response)
    score = response['attributeScores']['THREAT']['spanScores'][0]['score']['value']
    if score > .5:
        return score, threat_labeler(text_to_analyze)
    return score, None

def confusionMatrix():
    # Read the Excel file into a pandas DataFrame
    df = pd.read_excel('threatening_messages.xlsx')

    # Assuming the first column is 'strings' and the second column is 'labels'
    messages = df.iloc[:,0]
    print(messages)
    y_true = (df.iloc[:, 1])  # Get the ground truth labels
    print(y_true[0])
    y_pred = ([1 if analyzer(message) > .5 else 0 for message in messages]) # Get the predicted labels

    # Build the confusion matrix
    cm = confusion_matrix(y_true, y_pred, normalize='all')

    # Visualize the confusion matrix
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt=".1%", cmap="Blues")
    plt.title("Confusion Matrix For Threat Detection")
    plt.xlabel("Predicted Threat")
    plt.ylabel("True Threat")
    return plt.show()

#confusionMatrix()
