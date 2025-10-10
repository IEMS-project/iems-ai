def remove_empty_lines(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as infile:
        lines = infile.readlines()

    # Lọc bỏ các dòng trống hoặc chỉ chứa khoảng trắng
    non_empty_lines = [line for line in lines if line.strip() != ""]

    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.writelines(non_empty_lines)

    print(f"✅ Đã xử lý xong! File mới được lưu tại: {output_file}")


# --- Ví dụ sử dụng ---
remove_empty_lines(r"C:\Users\thang\HK1_N4\TLCN\ai\documents\noi_quy.txt", "Noi_quy_IEMS_clean.txt")
