import base64

with open(r"C:\Users\Administrator\Desktop\jetson.png", "rb") as upload_file:
    img_bytes = upload_file.read()


img_base64 = base64.b64encode(img_bytes).decode("utf-8")