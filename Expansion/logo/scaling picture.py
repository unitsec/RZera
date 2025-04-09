from PIL import Image

# 打开原始图像
original_image = Image.open('csns.png')

# 设置新的尺寸
new_height = 150  # 或者你想要的任何高度
# 按比例缩放图像
scale_factor = new_height / original_image.height
new_width = int(original_image.width * scale_factor)


# 缩小图像
resized_image = original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

# 保存缩小后的图像
resized_image.save('resized_csns.png')
