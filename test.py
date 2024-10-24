# import openai

# # # Initialize OpenAI with your API key
# openai.api_key = "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"

# # # Function to get a response from ChatGPT using the new API format
# # def get_chatgpt_response(prompt):
# #     response = openai.completions.create(
# #       model="gpt-3.5-turbo",  # or "gpt-4"
# #       prompt=prompt,          # Change from 'messages' to 'prompt'
# #       max_tokens=100,         # You can adjust this limit as per your need
# #       temperature=0.7         # Optional, controls the creativity of the response
# #     )
# #     return response['choices'][0]['text']  # 'text' instead of 'message'

# # # Example usage
# # prompt = "Hi Chatgpt"
# # response = get_chatgpt_response(prompt)
# # print(response)



# def get_chatgpt_response(prompt):
#     response = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",  # or gpt-4 depending on your model
#         messages=[{"role": "user", "content": prompt}]
#     )
#     return response['choices'][0]['message']['content']

# # Example usage
# prompt = "Explain the nitrogen gas explosion incident in Kota Kemuning"
# response = get_chatgpt_response(prompt)
# print(response)
from openai import OpenAI
client = OpenAI(api_key="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")
completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Hi Chatgpt"
        }
    ]
)

print(completion.choices[0].message.content)