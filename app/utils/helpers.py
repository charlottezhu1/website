import os
import re
import json
import html


# --- Text Processing Utilities ---


def convert_to_paragraphs(text):
    """
    Convert raw text into HTML paragraphs.
    - Normalizes line endings to '\n'.
    - Splits text into paragraphs on two or more newlines.
    - Escapes HTML in each paragraph and replaces single newlines with spaces.
    Returns concatenated HTML string of <p>...</p> paragraphs.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n\s*\n", normalized.strip())
    html_paragraphs = "".join(
        f'<p>{html.escape(p.strip().replace("\n", " "))}</p>'
        for p in paragraphs
        if p.strip()
    )
    return html_paragraphs


# --- File Loading Utilities ---


def read_txt_file_from_directory(
    directory_path="system_prompts", filename="charlotte.txt"
):
    """
    Read and return the content of a text file located at directory_path/filename,
    relative to the current module's file location.
    Raises FileNotFoundError if the file does not exist.
    """
    print("running read_txt_file_from_directory...")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, directory_path, filename)

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    return content


def load_all_json_from_folder(folder_path):
    """
    Load and return a list of all JSON objects from .json files in the given folder_path.
    """
    json_list = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                json_list.append(data)
    return json_list


# --- Prompt Manipulation Utilities ---


def replace_marker_with_multiple_conversations(
    text, conversations, marker="!<INPUT 0>!"
):
    """
    Replace the marker in 'text' with all conversations combined as a JSON string.
    Conversations is a list of conversation lists/dicts.
    Combines all messages from all conversations into one list and inserts JSON at marker.
    Raises ValueError if marker not found in text.
    """
    combined = []
    for conv in conversations:
        combined.extend(conv)

    json_str = json.dumps(combined, indent=2, ensure_ascii=False)

    if marker not in text:
        raise ValueError(f"Marker '{marker}' not found in the input text.")

    return text.replace(marker, json_str)


def append_conversations_to_prompt(base_prompt: str, conversations: list) -> str:
    """
    Append JSON strings of each conversation in 'conversations' to the base_prompt string.
    Each conversation is converted to JSON and concatenated with newlines.
    Returns the combined string.
    """
    conversations_json_strings = [
        json.dumps(conv, ensure_ascii=False) for conv in conversations
    ]

    all_conversations_json = "\n".join(conversations_json_strings)
    combined_prompt = base_prompt + "\n" + all_conversations_json

    return combined_prompt
