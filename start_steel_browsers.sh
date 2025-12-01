#!/bin/sh

ulimit -n 40960

case "$1" in
  -h|--help)
    echo "用法: $0 [数量]"
    echo "示例: $0 3"
    echo "可选环境变量: MIRROR(默认空，示例 m.ixdev.cn/), APP_PORT_BASE(默认13001), CDP_PORT_BASE(默认19224)"
    exit 0
    ;;
esac

COUNT=${1:-3}
MIRROR=${MIRROR:-}
APP_PORT_BASE=${APP_PORT_BASE:-13001}
CDP_PORT_BASE=${CDP_PORT_BASE:-19224}

IMAGE=ghcr.io/steel-dev/steel-browser:latest
if [ -n "$MIRROR" ]; then
  IMAGE="${MIRROR%/}/$IMAGE"
fi

echo "启动${COUNT}个Steel Browser实例..."

docker stop $(seq -f "steel-browser-%g" 1 "$COUNT") 2>/dev/null
docker rm $(seq -f "steel-browser-%g" 1 "$COUNT") 2>/dev/null

for i in $(seq 1 "$COUNT"); do
  app_port=$((APP_PORT_BASE + i - 1))
  cdp_port=$((CDP_PORT_BASE + i - 1))
  echo "启动实例${i} (端口${app_port})..."
  docker run -d --name steel-browser-${i} \
    --restart=unless-stopped \
    -e CHROME_ARGS="--disable-web-security" \
    -e DOMAIN=127.0.0.1:${app_port} \
    -e CDP_DOMAIN=127.0.0.1:${app_port} \
    -p 127.0.0.1:${app_port}:3000 \
    -p 127.0.0.1:${cdp_port}:9223 \
    "$IMAGE"
done

echo "等待容器启动..."
sleep 1

echo "容器状态:"
docker ps --filter "name=steel-browser" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
CDP_URLS=$(seq -s, -f "ws://127.0.0.1:%g" "$APP_PORT_BASE" "$((APP_PORT_BASE + COUNT - 1))")
echo "请设置环境变量:"
echo "export CDP_URLS=\"${CDP_URLS}\""
echo ""
echo "或者添加到 ~/.bashrc 或 ~/.zshrc:"
echo "echo 'export CDP_URLS=\"${CDP_URLS}\"' >> ~/.bashrc"