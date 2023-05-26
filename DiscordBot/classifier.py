import os
import openai
import json
# print(openai.Model.list()) # Can used to verify GPT-4 access

gtp4_path = "gpt4.json"
if not os.path.isfile(gtp4_path):
    raise Exception(f"{gtp4_path} not found!")
with open(gtp4_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    path = json.load(f)
    api_key = path['key']
openai.api_key = api_key

response = openai.ChatCompletion.create(
model="gpt-4",
messages=[
{"role": "system", "content": "You are a content moderation system. Classify each input as either threatening or not-threatening."},
{"role": "user", "content": "I am going to kill you."},
{"role": "assistant", "content": "Threatening"},
{"role": "user", "content": "I love you"},
{"role": "assistant", "content": "Not-threatening"},
{"role": "user", "content": "You should kill yourself"}
]
)


output = response['choices'][0]['message']['content']

output = response["results"][0]
print(output)
