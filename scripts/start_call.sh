#!/bin/bash

# ====================================================================
# 测试版本：即使 gstreamer 失败也会持续运行，直到被外部终止
# ====================================================================

echo "正在启动TCP流媒体服务器，使用物理摄像头 /dev/video0 ..."

# 尝试运行 gstreamer 命令
gst-launch-1.0 \
    v4l2src device=/dev/video0 ! \
    video/x-raw,width=640,height=480,framerate=30/1 ! \
    videoconvert ! queue ! x264enc tune=zerolatency bitrate=1500 ! h264parse ! \
    mux. \
    autoaudiosrc ! audioconvert ! queue ! opusenc ! \
    mux. \
    matroskamux name=mux ! tcpserversink host=0.0.0.0 port=8080

# 检查 gstreamer 命令的退出状态
if [ $? -ne 0 ]; then
    echo "警告：gst-launch-1.0 命令执行失败（可能是因为找不到摄像头）。"
    echo "为了测试目的，脚本将继续运行..."
fi

echo "模拟服务器正在运行... 按下 's' 键 (在 py-xiaozhi 命令行中) 来停止此脚本。"

# 使用无限循环保持脚本运行，直到被外部信号终止
# trap 命令用于捕获 SIGTERM 信号（由 Python 代码发送）并优雅退出
trap 'echo "收到终止信号，正在退出..."; exit 0' SIGTERM
while true; do
    sleep 1 # 每秒检查一次信号
done

# 理论上不会执行到这里，除非循环被某种方式打断
echo "脚本意外退出。"
exit 1