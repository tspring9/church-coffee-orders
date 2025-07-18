import qrcode

url = "https://test1coffee.streamlit.app/"

qr = qrcode.QRCode(
    version=1,
    box_size=10,
    border=4,
)
qr.add_data(url)
qr.make(fit=True)

img = qr.make_image(fill="black", back_color="white")
img.save("coffee_qr.png")
img.show()
