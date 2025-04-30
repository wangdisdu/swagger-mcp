## Python环境

Python 3.12

## 1.Conda

推荐使用使用conda构建Python环境。
构建Python 3.12环境

```
conda create --name swagger-mcp python=3.12
conda activate swagger-mcp
```

## 2.Requirements

使用国内镜像源安装依赖

```
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 3.启动

修改配置文件.env，设置SWAGGER_URLS为Swagger API地址
```
SWAGGER_URLS=http://localhost:8080/v3/api-docs
```

启动服务
```
./start.sh
```

## 4.MCP Inspector

使用npx启动 [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector)

```
npx @modelcontextprotocol/inspector
```

输出日志
```
MCP Inspector is up and running at http://127.0.0.1:6274
```

浏览器打开 http://127.0.0.1:6274，用这个工具调试MCP Server。 Transport选择SSE，URL地址填http://127.0.0.1:8000/sse。
