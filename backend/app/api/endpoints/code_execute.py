"""代码执行 API：在 Docker 沙箱中安全执行 Python 代码"""
import base64
import json
import docker
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.schemas.code_execute import CodeExecuteRequest, CodeExecuteResponse

router = APIRouter()

# 封装用户代码的模板代码 - 使用特殊占位符避免与代码中的大括号冲突
CODE_WRAPPER_TEMPLATE = '''
import sys
import base64
from io import BytesIO, StringIO
import json
import traceback

# 强制无界面
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 捕获控制台输出和错误
old_stdout = sys.stdout
old_stderr = sys.stderr
sys.stdout = StringIO()
sys.stderr = StringIO()

# 运行用户代码
try:
    user_code = """__USER_CODE_PLACEHOLDER__"""
    exec(user_code, globals())
    success = True
    error_msg = None
except Exception as e:
    success = False
    error_msg = traceback.format_exc()
finally:
    # 获取输出
    output = sys.stdout.getvalue()
    stderr_output = sys.stderr.getvalue()
    sys.stdout = old_stdout
    sys.stderr = old_stderr

# 捕获所有图片
images = []
for fig_num in plt.get_fignums():
    fig = plt.figure(fig_num)
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    images.append(img_b64)
    plt.close(fig)

# 返回结果
out = {
    "success": success,
    "stdout": output,
    "stderr": stderr_output,
    "error": error_msg,
    "images": images,
}
print(json.dumps(out, ensure_ascii=False))
'''


def wrap_user_code(code: str) -> str:
    """将用户代码嵌入模板"""
    # 只需要处理三引号，避免破坏模板结构
    code = code.replace('"""', '\\"""')
    return CODE_WRAPPER_TEMPLATE.replace('__USER_CODE_PLACEHOLDER__', code)


@router.post("/execute", response_model=CodeExecuteResponse)
def execute_code(
    body: CodeExecuteRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    在 Docker 沙箱中安全执行 Python 代码

    - **code**: 要执行的 Python 代码
    - **timeout**: 超时时间(秒)，默认30秒，最大300秒

    返回:
    - **success**: 是否执行成功
    - **stdout**: 标准输出内容
    - **images**: Base64编码的 PNG 图片列表
    - **error**: 错误信息(如果有)
    """
    try:
        # 创建 Docker 客户端
        client = docker.from_env()

        # 封装用户代码
        wrapped_code = wrap_user_code(body.code)

        # 在 Docker 容器中执行代码
        result = client.containers.run(
            image="python-sandbox-mpl",
            command=["python", "-c", wrapped_code],
            remove=True,
            network_disabled=True,
            mem_limit="512m",
            cpu_quota=50000,
            read_only=True,
            user="1000",
            working_dir="/tmp",
            stdout=True,
            stderr=True,
            tmpfs={
                '/tmp': 'rw,noexec,nosuid,size=100M'
            },
            environment={
                'MPLCONFIGDIR': '/tmp/matplotlib'
            }
        )

        # 解析输出（从最后一行提取 JSON）
        output_str = result.decode('utf-8')

        # 从输出中提取 JSON（最后一行）
        lines = output_str.strip().split('\n')
        json_line = None
        for line in reversed(lines):
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    json.loads(line)
                    json_line = line
                    break
                except json.JSONDecodeError:
                    continue

        if json_line is None:
            return CodeExecuteResponse(
                success=False,
                error=f"无法从输出中解析 JSON: {repr(output_str[:500])}"
            )

        data = json.loads(json_line)
        return CodeExecuteResponse(
            success=data.get("success", True),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            images=data.get("images", []),
            error=data.get("error")
        )

    except docker.errors.ContainerError as e:
        # 容器执行错误
        error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
        return CodeExecuteResponse(
            success=False,
            error=f"代码执行错误: {error_msg}"
        )
    except docker.errors.ImageNotFound:
        return CodeExecuteResponse(
            success=False,
            error="Docker 镜像 'python-sandbox-mpl' 未找到，请先构建镜像"
        )
    except docker.errors.APIError as e:
        return CodeExecuteResponse(
            success=False,
            error=f"Docker API 错误: {str(e)}"
        )
    except Exception as e:
        return CodeExecuteResponse(
            success=False,
            error=f"执行失败: {str(e)}"
        )
