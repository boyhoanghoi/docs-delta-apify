# Dùng DocsDelta để cập nhật kho dữ liệu AI

## Mới: cập nhật index bằng từng thao tác

Tải `CHUNK_OPERATIONS` hoặc `chunk-operations.ndjson` trong output của Actor.
Mỗi bản ghi có `operation`, `id`, `sourceUrl`, `pageStatus`, `pageContentHash`
và `observedAt`. Chỉ trang NEW/UPDATED đã lưu thành công mới tạo thao tác:

- `REMOVE`: xóa đúng ID trong trang nguồn và kho dữ liệu của bạn; ID đã vắng thì bỏ qua.
- `UPSERT`: thêm hoặc thay đoạn theo ID, gồm text, heading, vị trí `index` và hash.

Mỗi trang trả REMOVE trước, rồi UPSERT tất cả đoạn hiện tại. Đoạn giữ nguyên ID
cũng được cập nhật vì vị trí và thông tin trang có thể đổi. `isNewChunk: false`
nghĩa là ID đã có trong baseline; chỉ tái sử dụng embedding khi index của bạn
thực sự có đoạn đó với `contentHash` tương ứng. Trang UNCHANGED không tạo thao tác,
nhưng vẫn tính phí kiểm tra trang nếu bạn để chế độ mặc định lưu trang không đổi.

Xử lý xong toàn bộ thao tác rồi mới lưu SNAPSHOT làm baseline cho lần sau.
Nếu index lỗi giữa chừng, giữ baseline cũ và xử lý lại; thao tác upsert theo ID
và xóa ID vắng theo cách bỏ qua sẽ cho phép chạy lại an toàn. Không xóa cả kho
chỉ vì danh sách thao tác rỗng. Không có suy luận xóa trang từ lỗi 404 hay sitemap.
Giá sự kiện vẫn là $0.003/trang được lưu; không thu thêm sự kiện cho từng đoạn.

## Chạy lặp lại trên máy mà không dán JSON

```bash
docsdelta --input examples/changed-only.json --output output --snapshot-file state/docs-snapshot.json
```

Lần đầu chưa có file thì bắt đầu baseline trống. Các lần sau nạp file đã lưu,
và chỉ thay checkpoint sau khi xuất xong toàn bộ file kết quả. Việc thay từng
file là nguyên tử; cả thư mục không phải một giao dịch chung. Nếu xuất file lỗi,
checkpoint cũ được giữ, nhưng một số file kết quả có thể đã được thay. Kiểm tra
rồi chạy lại từ baseline đã xác nhận. Chỉ chạy một tiến trình cho mỗi checkpoint.

Nếu dùng kết quả để cập nhật vector DB hoặc dịch vụ bên ngoài, nên dùng cờ chỉ đọc:

```bash
docsdelta --input examples/changed-only.json --output output/next --previous-snapshot state/docs-snapshot.json
```

Cờ này bắt buộc file tồn tại và không tự cập nhật file nguồn, trừ khi bạn đặt nó
trùng đường dẫn file output. Sau khi index cập nhật thành công, mới dùng
`output/next/snapshot.json` làm baseline tiếp theo. Hai cờ không dùng cùng nhau
và không kết hợp với `previousSnapshot` chứa dữ liệu trong input.

Đây là tiện ích CLI chạy local. Trên Apify, hệ thống gọi Actor vẫn phải truyền
snapshot rõ ràng; không có kho trạng thái chung hay tự nạp snapshot bằng lịch chạy.
Chi tiết định dạng và giới hạn: [hướng dẫn index](INCREMENTAL_INDEXING.md).

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
