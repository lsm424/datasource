#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo: 使用 OpenAI 兼容接口测试「输入 prompt → 输出内容」是否正常。
不依赖 Ollama SDK，任何提供 OpenAI 兼容 API 的服务（如 Ollama / vLLM / 各类代理）均可使用。

用法:
  python demo_openai_chat.py
  OPENAI_BASE_URL=http://your-host/v1 OPENAI_MODEL=your-model python demo_openai_chat.py

Windows 控制台乱码时可在 PowerShell 中先执行: $env:PYTHONIOENCODING='utf-8'
"""
import os
import sys
import base64

# 建议安装: pip install openai
try:
    from openai import OpenAI
except ImportError:
    print("Please install: pip install openai", file=sys.stderr)
    sys.exit(1)


def main():
    # 从环境变量读取，兼容后续部署其他 OpenAI 兼容模型
    base_url = os.environ.get(
        "OPENAI_BASE_URL",
        os.environ.get("OLLAMA_BASE_URL", "http://47.108.93.204:11435").rstrip("/") + "/v1",
    )
    model = os.environ.get("OPENAI_MODEL", os.environ.get("OLLAMA_MODEL", "qwen3-vl:32b"))
    api_key = os.environ.get("OPENAI_API_KEY", "dummy")  # 很多兼容接口允许任意 key 或留空

    print("BASE_URL:", base_url)
    print("MODEL:", model)
    print("-" * 40)

    client = OpenAI(base_url=base_url, api_key=api_key)

    prompt = "请帮我分析/解读这些数据"
    print("Prompt:", prompt)
    print("Reply (streaming): ", end="", flush=True)

    #system_text = "你是一个大模型，请回答用户的问题。"
    # import json
    # resource_text = open('./backend/msg.txt', 'r', encoding='utf-8').read()
    # system_text = "你是一个大模型，请回答用户的问题。"

    messages_with_system = [
        {'role': 'system', 'content': "以下是与当前资源相关的内容，请基于这些内容回答用户问题。\n\n【资源内容】\nCSV列名: ['Year', '5%', 'Mean', '95%']\n前500行:\n      Year        5%      Mean       95%\n0   1950.0 -0.060030  0.252242  0.608546\n1   1951.0 -0.055686  0.274715  0.525308\n2   1952.0 -0.042891  0.274303  0.540725\n3   1953.0 -0.020530  0.253376  0.535419\n4   1954.0 -0.127657  0.246369  0.553914\n5   1955.0 -0.045436  0.273183  0.541897\n6   1956.0 -0.122056  0.270194  0.595489\n7   1957.0 -0.081519  0.268020  0.572240\n8   1958.0 -0.035150  0.258518  0.534191\n9   1959.0 -0.023537  0.258082  0.555881\n10  1960.0 -0.083648  0.275816  0.549635\n11  1961.0  0.023708  0.278716  0.596956\n12  1962.0 -0.114702  0.243163  0.485732\n13  1963.0 -0.154688  0.146068  0.446616\n14  1964.0 -0.199097  0.067564  0.358201\n15  1965.0 -0.189913  0.089235  0.330021\n16  1966.0 -0.080192  0.136807  0.419210\n17  1967.0 -0.252428  0.132230  0.431860\n18  1968.0 -0.225698  0.163259  0.469934\n19  1969.0 -0.141856  0.197771  0.431807\n20  1970.0 -0.097311  0.211585  0.493199\n21  1971.0 -0.187701  0.228505  0.531925\n22  1972.0 -0.179701  0.202590  0.472747\n23  1973.0 -0.023019  0.226456  0.451735\n24  1974.0 -0.015103  0.246628  0.497963\n25  1975.0 -0.029558  0.211784  0.529958\n26  1976.0 -0.015883  0.219708  0.468149\n27  1977.0  0.022513  0.278376  0.499191\n28  1978.0  0.028292  0.282009  0.611599\n29  1979.0 -0.025456  0.311394  0.570115\n30  1980.0  0.033029  0.347290  0.624456\n31  1981.0  0.113745  0.377955  0.592297\n32  1982.0  0.071366  0.337443  0.585534\n33  1983.0 -0.013935  0.231890  0.568651\n34  1984.0  0.134554  0.303182  0.607088\n35  1985.0  0.050454  0.354818  0.646899\n36  1986.0  0.145226  0.388410  0.688514\n37  1987.0  0.166573  0.437567  0.693618\n38  1988.0  0.152693  0.471578  0.695916\n39  1989.0  0.293242  0.516417  0.733800\n40  1990.0  0.409507  0.586496  0.817305\n41  1991.0  0.300284  0.565131  0.814267\n42  1992.0  0.065736  0.292329  0.523401\n43  1993.0  0.149989  0.348397  0.626579\n44  1994.0  0.167363  0.450393  0.681278\n45  1995.0  0.282344  0.490861  0.751686\n46  1996.0  0.356335  0.565519  0.755367\n47  1997.0  0.434545  0.638018  0.845823\n48  1998.0  0.445872  0.645688  0.831704\n49  1999.0  0.445269  0.681837  0.865118\n50  2000.0  0.537534  0.735275  0.871411\n51  2001.0  0.604782  0.798701  0.999765\n52  2002.0  0.597459  0.820328  0.991021\n53  2003.0  0.682348  0.856159  0.994181\n54  2004.0  0.689514  0.865993  1.068560\n55  2005.0  0.693329  0.884204  1.062460\n56  2006.0  0.692701  0.899079  1.088390\n57  2007.0  0.732211  0.928693  1.104070\n58  2008.0  0.792066  0.942816  1.130520\n59  2009.0  0.797398  0.961617  1.157980\n60  2010.0  0.836971  1.002620  1.280120\n61  2011.0  0.842644  1.036330  1.189250\n62  2012.0  0.882825  1.061300  1.240670\n63  2013.0  0.913046  1.084920  1.285700\n64  2014.0  0.930436  1.100040  1.331640"}, 
        {'role': 'user', 'content': '请帮我分析这个数据'}, 
        {'role': 'user', 'content': '请帮我分析这个数据'}
    ]
    # 构造图片消息，使用 OpenAI 兼容的多模态格式
    image_path = "backend/files/6038.jpg_wh860.jpg"
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    image_data_url = f"data:image/jpeg;base64,{img_b64}"

    messages_with_system = [
        {
            'role': 'user',
            'content': [
                {
                    "type": "text",
                    "text": "请帮我详细分析这张图片的内容。",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_url},
                },
            ],
        },
    ]
    print("messages_with_system: ", messages_with_system)

    def stream_chat(messages):
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            # max_tokens=512,
            temperature=0.3,
            stream=True,
        )
        full = []
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and getattr(delta, "content", None):
                part = delta.content
                full.append(part)
                print(part, end="", flush=True)
        return full

    try:
        full = stream_chat(messages_with_system)
        # 部分 OpenAI 兼容服务对 role=system 支持不完整：可能不报错但返回空
        if not full:
            print()
            print("[WARN] Empty reply with role=system, retrying without system role...", flush=True)
            print("Reply (fallback streaming): ", end="", flush=True)
        print()
        print("[OK] OpenAI-compatible API (streaming) works. full: ")
        return 0
    except Exception as e:
        print()
        print("[ERROR]", type(e).__name__, str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
