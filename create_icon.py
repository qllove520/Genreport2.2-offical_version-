#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os


def create_app_icon():
    """创建一个简单的应用图标"""

    # 创建一个简单的ICO文件内容
    ico_data = bytes([
        # ICO文件头
        0x00, 0x00,  # 保留字段
        0x01, 0x00,  # 图标类型 (1=ICO)
        0x01, 0x00,  # 图标数量

        # 图标目录项
        0x10,  # 宽度 (16)
        0x10,  # 高度 (16)
        0x00,  # 颜色数 (0=256色以上)
        0x00,  # 保留字段
        0x01, 0x00,  # 颜色平面数
        0x20, 0x00,  # 每像素位数 (32位)
        0x00, 0x01, 0x00, 0x00,  # 图像数据大小
        0x16, 0x00, 0x00, 0x00,  # 图像数据偏移

        # BMP头
        0x28, 0x00, 0x00, 0x00,  # BMP头大小
        0x10, 0x00, 0x00, 0x00,  # 图像宽度
        0x20, 0x00, 0x00, 0x00,  # 图像高度 (包含AND掩码)
        0x01, 0x00,  # 颜色平面数
        0x20, 0x00,  # 每像素位数
        0x00, 0x00, 0x00, 0x00,  # 压缩方式
        0x00, 0x00, 0x00, 0x00,  # 图像数据大小
        0x00, 0x00, 0x00, 0x00,  # 水平分辨率
        0x00, 0x00, 0x00, 0x00,  # 垂直分辨率
        0x00, 0x00, 0x00, 0x00,  # 使用的颜色数
        0x00, 0x00, 0x00, 0x00,  # 重要颜色数
    ])

    # 添加简单的蓝色背景像素数据
    pixel_data = []
    for y in range(16):
        for x in range(16):
            # 创建简单的图标：蓝色背景，白色文档图案
            if 3 <= x <= 12 and 2 <= y <= 13:
                # 文档区域 - 白色
                pixel_data.extend([0xFF, 0xFF, 0xFF, 0xFF])  # BGRA
            else:
                # 背景 - 蓝色
                pixel_data.extend([0xFF, 0x7F, 0x00, 0xFF])  # BGRA

    # AND掩码 (全透明)
    and_mask = [0x00] * 32  # 16x16位 = 32字节

    # 写入ICO文件
    with open('app_icon.ico', 'wb') as f:
        f.write(ico_data)
        f.write(bytes(pixel_data))
        f.write(bytes(and_mask))

    print("✅ 程序图标已创建: app_icon.ico")


if __name__ == "__main__":
    create_app_icon()