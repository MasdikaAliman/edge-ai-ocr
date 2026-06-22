
import os
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional, TypedDict
from langchain.chat_models import init_chat_model

from app.core.sys_prompt import GENERAL_PROMPT, get_prompt_for_fields
import json
import random
import io
import ast
from PIL import Image, ImageDraw, ImageFont
from PIL import ImageColor
from IPython.display import Markdown, display
import os
import base64
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.doc_prompt import KTP_PROMPT

from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

BASE_URL_LLM = os.getenv("BASE_URL_LLM", "http://localhost:1234")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen/qwen3-vl-4b")

model = init_chat_model(
    model=MODEL_NAME,
    model_provider="openai",
    base_url=f"{BASE_URL_LLM}/v1",
    api_key="EMPTY",
    # temperature=0.0,
    # top_p=0.95,
    model_kwargs={
        "extra_body": {
            # "top_k": 1,
            "mm_processor_kwargs": {
                "min_pixels": 360 * 32 * 32,
                "max_pixels": 4096 * 32 * 32
            }
        }
    }
)

def parse_json(json_output):
    # Parsing out the markdown fencing
    lines = json_output.splitlines()
    for i, line in enumerate(lines):
        if line == "```json":
            json_output = "\n".join(lines[i+1:])  # Remove everything before "```json"
            json_output = json_output.split("```")[0]  # Remove everything after the closing "```"
            break  # Exit the loop once "```json" is found
    return json_output


def encode_image(image_path):
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        with io.BytesIO() as buf:
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")

def extract_bboxes(data):
        boxes = []
        if isinstance(data, dict):
            if "bbox_2d" in data and isinstance(data["bbox_2d"], list) and len(data["bbox_2d"]) == 4:
                boxes.append(data)
            else:
                for v in data.values():
                    boxes.extend(extract_bboxes(v))
        elif isinstance(data, list):
            for item in data:
                boxes.extend(extract_bboxes(item))
        return boxes

def plot_text_bounding_boxes(image_path, json_output):
    """
    Plots bounding boxes on an image with markers for each a name, using PIL, normalized coordinates, and different colors.

    Args:
        image_path: The path to the image file.
        json_output: A list of bounding boxes containing the name of the object
         and their positions in normalized [y1 x1 y2 x2] format.
    """

    # Load the image
    img = Image.open(image_path)
    width, height = img.size
    print(img.size)
    # Create a drawing object
    draw = ImageDraw.Draw(img)

    # Parsing out the markdown fencing
    bounding_boxes = parse_json(json_output)

    # Iterate over the bounding boxes
    parsed_data = ast.literal_eval(bounding_boxes)



    bounding_boxes_list = extract_bboxes(parsed_data)

    for i, bounding_box in enumerate(bounding_boxes_list):
      color = 'green'

      # Convert normalized coordinates to absolute coordinates
      abs_y1 = int(int(bounding_box["bbox_2d"][1])/999 * height)
      abs_x1 = int(int(bounding_box["bbox_2d"][0])/999 * width)
      abs_y2 = int(int(bounding_box["bbox_2d"][3])/999 * height)
      abs_x2 = int(int(bounding_box["bbox_2d"][2])/999 * width)

      if abs_x1 > abs_x2:
        abs_x1, abs_x2 = abs_x2, abs_x1

      if abs_y1 > abs_y2:
        abs_y1, abs_y2 = abs_y2, abs_y1

      # Draw the bounding box
      draw.rectangle(
          ((abs_x1, abs_y1), (abs_x2, abs_y2)), outline=color, width=1
      )

      # Draw the text
      if "value" in bounding_box and bounding_box["value"] is not None:
        draw.text((abs_x1, abs_y2), str(bounding_box["value"]), fill=color)

    # Display the image
    img.show()



def main():
    # PROMPT_USER = "This is page 1 of a KTP document."
    PROMPT_USER = "Spotting all the text in the image with line-level, and output in JSON format as [{'bbox_2d': [x1, y1, x2, y2], 'value': 'text'}, ...].\n Bounding boxes must tightly enclose the text region."

    Fields_required = ["nik", "nama", "tanggal_lahir", "alamat"]

    path = r"sample2.jpg"
    base64 = encode_image(path)
    content_item = {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/png;base64,{base64}"
        }
    }
    content: List[Dict[str, Any]] = [
        {"type": "text", "text": PROMPT_USER}
    ]
    content.append(content_item)
    
    # messages = [SystemMessage(content=KTP_PROMPT), HumanMessage(content=content)]
    messages = [HumanMessage(content=content)]

    # print(messages)
    response = model.invoke(messages)
    print(response.content)
    plot_text_bounding_boxes(path, response.content)

if __name__ == "__main__":
    main()
