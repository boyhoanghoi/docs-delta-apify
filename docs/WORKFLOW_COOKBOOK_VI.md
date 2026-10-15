# Dùng DocsDelta để cập nhật kho dữ liệu AI

## Tạo nguồn cho chatbot tài liệu

1. Chọn vài URL tài liệu công khai, nhập vào `urls` và đặt `maxPages` nhỏ.
2. Chạy Actor và kiểm tra Markdown, các đoạn `chunks` cùng `sourceUrl`.
3. Dùng `RAG_CHUNKS` làm đầu vào cho bước embedding/indexing của hệ thống bạn.
   Actor tạo tài liệu có cấu trúc; không tự tạo chatbot, embedding hoặc vector DB.
4. Lưu JSON `SNAPSHOT` để so sánh ở lần chạy sau.

Ví dụ có thể chạy ngay là tài liệu cấu trúc dữ liệu Python và trang giới thiệu
Django trong `examples`. Có thể dùng `contentCssSelector` để chỉ lấy vùng nội
dung chính hoặc `excludeCssSelectors` để bỏ vùng thay đổi không cần theo dõi.

## Cập nhật theo thay đổi

Truyền nguyên JSON `SNAPSHOT` lần trước vào `previousSnapshot` lần sau.
Kết quả có trạng thái `NEW`, `UPDATED` hoặc `UNCHANGED` và các ID đoạn.
Với từng trang trả về, xóa những ID trong `removedChunkIds`, rồi upsert các
đoạn hiện tại theo `id`. Lưu snapshot mới sau khi đã xử lý kết quả thành công.

Trang lỗi, bị robots chặn hoặc vượt giới hạn không làm mất baseline tốt.
Actor không kết luận một trang đã bị xóa chỉ vì lần chạy không đọc được nó.
Không xóa toàn bộ index vì một lần chạy trả ít trang hơn trước.

`changedOnly: true` chỉ lưu trang mới/thay đổi. Mặc định các lần kiểm tra thành
công không đổi cũng được lưu và tính phí. Trang không đổi bị chế độ changedOnly
loại sẽ không phát sinh sự kiện tính phí; các đoạn con không bị tính phí riêng.

## Nối vào n8n/Make hoặc chương trình riêng

Luồng dữ liệu: lấy snapshot từ nơi bạn lưu → chạy Actor với previousSnapshot →
lấy RESULTS/RAG_CHUNKS và SNAPSHOT → cập nhật index theo từng trang → lưu snapshot
mới. Apify tạo API cho Actor; dùng mẫu request từ tab API với token của chính
tài khoản bạn, giữ token ngoài mã nguồn.

Chỉ gắn lịch chạy với input cố định sẽ không tự nạp snapshot của lần chạy trước.
Hệ thống gọi Actor cần thực hiện bước truyền trạng thái này. Snapshot có giới
hạn 5 MiB; chia nguồn thành các nhóm nếu vượt giới hạn. Trang cần trình duyệt
chạy JavaScript có thể không đọc được trong bản HTTP hiện tại.
