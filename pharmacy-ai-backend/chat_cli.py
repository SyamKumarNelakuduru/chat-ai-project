#!/usr/bin/env python3
"""
Simple CLI chat interface for the pharmacy AI backend
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def send_question(question):
    """Send a question to the backend and get the response"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/ask",
            json={"question": question},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("answer", "No answer received")
        else:
            return f"Error: Status code {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return f"❌ Cannot connect to backend at {BASE_URL}. Is it running?"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def main():
    print("\n" + "="*60)
    print("🏥 Pharmacy AI Chat - Terminal Interface")
    print("="*60)
    print("Type your pharmacy questions below.")
    print("Type 'quit' or 'exit' to close.\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit']:
                print("\n👋 Goodbye!")
                sys.exit(0)
            
            print("\n⏳ Processing...\n")
            answer = send_question(user_input)
            print(f"Bot: {answer}\n")
            print("-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    main()
