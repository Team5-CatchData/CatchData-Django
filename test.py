from google import genai

client = genai.Client(api_key="AIzaSyDzZI8jQMaKTKu7ZjyVzbP4Mdaw8keHQDU")

for m in client.models.list():
    if "generateContent" in m.supported_actions:
        print(m.name)