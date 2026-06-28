import os
import io

# Disable MKLDNN/oneDNN prior to PaddlePaddle imports to prevent PIR crashes on CPU
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

import paddle
paddle.set_device('gpu')
print(paddle.is_compiled_with_cuda())
print(paddle.device.get_device())

# import fitz
# from PIL import Image
# from paddleocr import PaddleOCR  

# ocr = PaddleOCR(
#     use_doc_orientation_classify=False, # Disables document orientation classification model via this parameter
#     use_doc_unwarping=False, # Disables text image rectification model via this parameter
#     use_textline_orientation=False, # Disables text line orientation classification model via this parameter
#     enable_mkldnn=False,
# )

# def run_ocr_on_file(file_path):
#     ext = os.path.splitext(file_path)[1].lower()
    
#     if ext == ".pdf":
#         print(f"Processing PDF: {file_path}")
#         doc = fitz.open(file_path)
#         for i, page in enumerate(doc):
#             page_no = i + 1
#             print(f"\n--- Processing Page {page_no} ---")
            
#             # Render page to a pixmap (dpi=200)
#             pix = page.get_pixmap(dpi=200)
#             temp_img_path = f"temp_page_{page_no}.png"
#             pix.save(temp_img_path)
            
#             try:
#                 result = ocr.predict(temp_img_path)
#                 for res in result:  
#                     res.print()  
#                     res.save_to_img(f"output_page_{page_no}")  
#                     res.save_to_json(f"output_page_{page_no}")
#             finally:
#                 # Clean up temp image
#                 if os.path.exists(temp_img_path):
#                     os.remove(temp_img_path)
#     else:
#         print(f"Processing Image: {file_path}")
#         result = ocr.predict(file_path)
#         for res in result:  
#             res.print()  
#             res.save_to_img("output")  
#             res.save_to_json("output")

# if __name__ == "__main__":
#     # Set your test file path here (e.g. 'sample.pdf' or 'Save_0.png')
#     test_file = "Save_0.png"
    
#     if os.path.exists(test_file):
#         run_ocr_on_file(test_file)
#     else:
#         fallback_file = "Save_0.png"
#         if os.path.exists(fallback_file):
#             print(f"'{test_file}' not found. Falling back to '{fallback_file}'.")
#             run_ocr_on_file(fallback_file)
#         else:
#             print("No test file found!")