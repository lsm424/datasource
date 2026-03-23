import ollama
import os
import cv2
import pandas as pd
from PIL import Image
import base64
from io import BytesIO

client = ollama.Client(host='http://47.108.93.204:11435')
models = client.list()
print(models)
# -------------------------- 工具函数：资源预处理 --------------------------
def preprocess_image(image_path):
    """预处理图片：转换为base64编码（ollama支持的图片格式）"""
    try:
        with Image.open(image_path) as img:
            # 压缩图片（避免32B模型处理过大图片超时）
            img.thumbnail((1024, 1024))
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return img_base64
    except Exception as e:
        raise ValueError(f"图片预处理失败：{e}")

def preprocess_txt(txt_path):
    """预处理TXT文件：读取文本内容"""
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        raise ValueError(f"TXT文件读取失败：{e}")

def preprocess_csv(csv_path):
    """预处理CSV文件：读取并转换为易读文本"""
    try:
        df = pd.read_csv(csv_path)
        # 转换为带格式的文本（包含列名+前10行数据，避免内容过长）
        content = f"CSV文件列名：{list(df.columns)}\n前10行数据：\n{df.head(10).to_string()}"
        return content
    except Exception as e:
        raise ValueError(f"CSV文件读取失败：{e}")

def preprocess_video(video_path, frame_interval=200):
    """预处理视频：抽帧（每frame_interval帧取1张）并转换为base64列表"""
    try:
        cap = cv2.VideoCapture(video_path)
        frames_base64 = []
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            # 按间隔抽帧
            if frame_count % frame_interval == 0:
                # 转换为PIL Image并编码
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                buffer = BytesIO()
                img.save(buffer, format="JPEG")
                img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                frames_base64.append(img_base64)
            frame_count += 1
        cap.release()
        if not frames_base64:
            raise ValueError("视频抽帧为空")
        return frames_base64
    except Exception as e:
        raise ValueError(f"视频预处理失败：{e}")

# -------------------------- 核心函数：与模型对话 --------------------------
def chat_with_qwen3_vl(resource_path, prompt, resource_type):
    """
    与Qwen3-VL:32B模型对话
    :param resource_path: 资源文件路径（图片/txt/csv/视频）
    :param prompt: 对话指令（如"分析这张图片的内容"）
    :param resource_type: 资源类型，可选值：image/txt/csv/video
    :return: 模型回复内容
    """
    # 1. 预处理资源
    if resource_type == "image":
        # 对于 Ollama，多模态消息使用字符串 content + images 列表
        img_base64 = preprocess_image(resource_path)
        messages = [
            {
                "role": "user",
                "content": prompt,
                "images": [img_base64],
            }
        ]
    elif resource_type == "txt":
        txt_content = preprocess_txt(resource_path)
        messages = [
            {
                "role": "user",
                "content": f"{prompt}\n文本内容：{txt_content}",
            }
        ]
    elif resource_type == "csv":
        csv_content = preprocess_csv(resource_path)
        messages = [
            {
                "role": "user",
                "content": f"{prompt}\nCSV内容：{csv_content}",
            }
        ]
    elif resource_type == "video":
        frames_base64 = preprocess_video(resource_path)
        # 取前3帧作为图片输入，content 仍然是字符串
        images = frames_base64[:]
        messages = [
            {
                "role": "user",
                "content": f"{prompt}\n下面是从视频中抽取的 {len(images)} 帧图片，请综合分析。",
                "images": images,
            }
        ]
    else:
        raise ValueError(f"不支持的资源类型：{resource_type}")

    # 2. 调用ollama API与模型对话
    try:
        response = client.chat(
            model="qwen3-vl:32b",
            messages=messages,
            options={"temperature": 0.1, "max_tokens": 2048}  # 控制回复稳定性和长度
        )
        return response["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"调用模型失败：{e}")

# -------------------------- 测试示例 --------------------------
if __name__ == "__main__":
    # 示例1：图片对话
    # image_path = "6038.jpg_wh860.jpg"
    # prompt = "分析这张图片的内容，详细描述画面中的元素"
    # print("图片对话结果：\n", chat_with_qwen3_vl(image_path, prompt, "image"))

    # 示例2：TXT文本对话
    # txt_path = "resources/test.txt"
    # prompt = "总结这个txt文件的核心内容"
    # print("TXT对话结果：\n", chat_with_qwen3_vl(txt_path, prompt, "txt"))

    # 示例3：CSV文件对话
    # csv_path = "resources/temp_export.csv"
    # prompt = "分析这个CSV文件的数据分布，指出关键信息"
    # print("CSV对话结果：\n", chat_with_qwen3_vl(csv_path, prompt, "csv"))

    # 示例4：视频对话
    video_path = "resources/20260109_080822.mp4"
    prompt = "分析这个视频的内容，描述主要画面"
    print("视频对话结果：\n", chat_with_qwen3_vl(video_path, prompt, "video"))