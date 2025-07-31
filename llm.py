import ollama

def ai_assistant():
    print("DeepSeek-R1 Local Assistant (type 'exit' to quit)")
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break
        response = ollama.chat(
            model="deepseek-r1:8b",
            messages=[{"role": "user", "content": user_input}],
            stream=True,
            think=False,
        )
        for chunk in response:
            print(chunk['message']['content'], end='', flush=True)
        print()

if __name__ == "__main__":
    ai_assistant()
