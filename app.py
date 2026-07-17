from flask import Flask, render_template, request, Response,jsonify
from llama_cpp import Llama
import time 
import json
import os

NOTES_DIR = 'notes'
HISTORY_DIR = 'chat_history'


app = Flask(__name__)




@app.route('/')
def index():
    return render_template('index.html')
@app.route('/history', methods=['GET'])
def history():
    print('InHistory',flush=True)
    global messages
    try: 
       file_path = os.path.join(HISTORY_DIR, 'history.json')
       os.makedirs(HISTORY_DIR, exist_ok=True)
       with open(file_path, 'r',encoding='utf-8') as f:
           messages =  json.load(f)
    except:
       messages = []
       messages.append([{"role": "system", "content": "You are a helpful assistant. You must NEVER use emojis. Use plain text only."}])
    return jsonify(messages)

def save_chat_history(chat, directory, filename):
    print('save_chat_history',flush=True)
    file_path = os.path.join(directory, filename)
    os.makedirs(directory, exist_ok=True)

    with open(file_path, 'w',encoding='utf-8') as json_file:
        json.dump(chat, json_file, indent=4)


@app.route('/create_page', methods=['POST'])
def create_page():
    print('CraetPage',flush=True)
    data = request.json
    title = data.get('title', 'Untitled').strip()
    base_title = title
    counter = 1
    page_path = os.path.join(NOTES_DIR, f"{title}.txt")
    while os.path.exists(page_path):
        title = f"{base_title} ({counter})"
        page_path = os.path.join(NOTES_DIR, f"{title}.txt")
        counter += 1
    os.makedirs(NOTES_DIR, exist_ok=True)
    with open(page_path, 'w',encoding='utf-8') as f:
        f.write('')
    return jsonify({"status": "created", "title": title}) 
 

@app.route('/delete_page',methods=['POST'])
def delete_page():
    data = request.json
    title = data.get('title','').strip()
    if not title:
        return jsonify({"error": "No title provided"}), 400
    page_path = os.path.join(NOTES_DIR,f"{title}.txt")
    if os.path.exists(page_path):
        os.remove(page_path)
    else:
        return jsonify({"status": "not_found", "title": title}), 404 
    return jsonify({"status":"deleted","title": title})

@app.route('/pages_list', methods=['GET'])
def pages_list():
    print('InPageList',flush=True)
    os.makedirs(NOTES_DIR, exist_ok=True)
    txt_files = [f for f in os.listdir(NOTES_DIR) if f.endswith('.txt')]
    return jsonify(txt_files)
 

@app.route('/save_page/<title>', methods = ['POST'])
def save_page(title):
    data = request.json
    content = data.get('content','')
    new_title = data.get('new_title', title)
    file_path = os.path.join(NOTES_DIR, f"{title}.txt")
    if new_title != title:
        os.rename(f'{NOTES_DIR}/{title}.txt', f'{NOTES_DIR}/{new_title}.txt')  
        title=new_title 

    file_path = os.path.join(NOTES_DIR, f"{title}.txt")
    with open(file_path, 'w',encoding='utf-8') as f:
        f.write(content)
    return jsonify({"status": "saved", "title": title})


@app.route('/get_page/<title>', methods=['GET'])
def get_page(title):
    file_path = os.path.join(NOTES_DIR, f"{title}.txt")
    try:
        with open(file_path, 'r',encoding='utf-8') as f:
            content = f.read()
        return jsonify({"title": title, "content": content})
    except:
        return jsonify({"error": "Page not found"}), 404



def cmd_new_page(prompt):
        title = prompt[3:].strip()
        base_title = title
        counter = 1
        file_path = os.path.join(NOTES_DIR, f"{title}.txt")
        while os.path.exists(file_path):
            title = f"{base_title} ({counter})"
            file_path = os.path.join(NOTES_DIR, f"{title}.txt")
            counter += 1
        os.makedirs(NOTES_DIR, exist_ok=True)
        with open(file_path, 'w',encoding='utf-8') as f:
            f.write('')
        reply = f"Page '{title}' created."
        messages.append({"role": "user", "content": prompt})
        messages.append({"role": "assistant", "content": reply})
        return reply


def cmd_add_content(prompt):
    #print('awsa2',flush=True)
    title = prompt[5:].strip()
    content = messages[-1]['content']
    page_path = os.path.join(NOTES_DIR,f"{title}.txt")
    with open(page_path, 'w',encoding='utf-8') as f:
        f.write(content)
    reply = f"Content added to page '{title}."
    messages.append({"role": "user", "content": prompt})
    messages.append({"role": "assistant", "content": reply})
    return reply  


def cmd_delete_chat_history(prompt):
    global messages
    messages.clear() 
    history_path = os.path.join(HISTORY_DIR, 'history.json')
    with open(history_path, 'w', encoding='utf-8') as f:
        f.truncate(0)
    reply = f"History got deleted!"
    #messages.append({"role": "user", "content": prompt})
    #messages.append({"role": "assistant", "content": reply})
    return reply 
 

 
COMMANDS = {
    '/delete-h': cmd_delete_chat_history,
    '/p ': cmd_new_page,
    '/add ': cmd_add_content,
}
      
@app.route('/generate', methods=['POST'])
def generate():
    global messages
    data = request.json
    prompt = data.get('prompt', '')
    if prompt.startswith('/'):
        for cmd,fun in COMMANDS.items():
            if prompt.startswith(cmd):
                reply = fun(prompt)
                save_chat_history(messages,HISTORY_DIR,'history.json')
                return jsonify({"reply": reply})
                
        if prompt.startswith('/cls'):
            return jsonify({"reply": "__CLEAR__"})
        
    print('awsa2',flush=True)
    llm = Llama(
            model_path="models/qwen3-4b-instruct-2507-q4_k_m.gguf",
            n_ctx=4048,
            n_threads=4,
            verbose=False)
    messages.append({"role": "user", "content": prompt})

    response = llm.create_chat_completion(
        messages=messages,
        max_tokens=300,
        temperature=0.3,
    )
    #elapsed = time.time() - start
    reply = response["choices"][0]["message"]["content"]
    messages.append({"role": "assistant", "content": reply}) 
    usage = response.get("usage", {})
    #prompt_tokens = usage.get("prompt_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)
    while total_tokens > 2000 and len(messages) > 2:
           messages.pop(2)
     
    save_chat_history(messages,HISTORY_DIR,'history.json')
    return jsonify({"reply": reply})

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
